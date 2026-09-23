"""Observe HA automation traces without changing or re-running automations."""
import asyncio
from dataclasses import dataclass, field
import logging
import time

from homeassistant.core import callback

from .action_request import RequestState

LOGGER = logging.getLogger(__name__)
POLL_INTERVAL = 1
RESULT_TIMEOUT = 300
MAX_RUNS = 64


def find_trace(hass, entity_id, context_id):
    # Keep HA's trace-store dependency isolated and fail closed when unavailable.
    from homeassistant.components.automation import DATA_COMPONENT
    from homeassistant.components.trace.const import DATA_TRACE

    component = hass.data.get(DATA_COMPONENT)
    entity = component.get_entity(entity_id) if component else None
    key = getattr(entity, "unique_id", None)
    bucket = hass.data.get(DATA_TRACE, {}).get(f"automation.{key}", {})
    runs = getattr(bucket, "runs", bucket)
    for trace in runs.values():
        if trace.context.id == context_id:
            return trace
    return None


def trace_result(trace):
    if trace is None:
        return "UNKNOWN"
    short = trace.as_short_dict()
    if short.get("state") == "running":
        return None
    if short.get("state") != "stopped":
        return "UNKNOWN"
    details = trace.as_extended_dict().get("trace", {})
    steps = [step for path, entries in details.items() if path.startswith("action/")
             for step in entries]
    if short.get("error") or any("error" in step for step in steps):
        return "ERR"
    if (short.get("script_execution") != "finished" or not steps
            or any("stop" in step.get("result", {}) for step in steps)):
        return "UNKNOWN"
    return "OK"


@dataclass
class ObservedRuns:
    runs: dict = field(default_factory=dict)
    too_many: bool = False


class AutomationResponses:
    def __init__(self, responses):
        self.responses = responses
        self.hass = responses.hub.hass
        self.watching = {}
        self._tasks = set()
        self.observations: dict[str, ObservedRuns] = {}
        self.unsubscribe = self.hass.bus.async_listen("automation_triggered", self.started)

    @callback
    def started(self, event):
        responses = self.responses
        if not responses.enabled or responses.hub.stopping:
            return
        for request_id, request in responses.requests.items():
            if (not request.auto_reply or request.state is not RequestState.PENDING
                    or not request.context_id
                    or event.context.parent_id != request.context_id
                    or time.monotonic() - request.created >= RESULT_TIMEOUT):
                continue
            run_id = event.context.id
            observation = self.observations.setdefault(request_id, ObservedRuns())
            runs = observation.runs
            if run_id in runs:
                return
            if len(runs) >= MAX_RUNS:
                observation.too_many = True
                return
            try:
                runs[run_id] = find_trace(self.hass, event.data.get("entity_id"), run_id)
            except (AttributeError, TypeError, ImportError):
                LOGGER.warning("Home Assistant automation trace is unavailable", exc_info=True)
                runs[run_id] = None
            if request_id not in self.watching:
                responses.activity(request, "executing")
                task = self.hass.async_create_background_task(
                    self._watch(request_id, request, observation), "MeshCore action response")
                self.watching[request_id] = task
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
            return

    async def _watch(self, request_id, request, observation):
        responses = self.responses
        try:
            while True:
                # Let all automations for this message start before aggregating.
                await asyncio.sleep(POLL_INTERVAL)
                if (not responses.enabled or responses.hub.stopping
                        or not request.auto_reply or request.state is not RequestState.PENDING):
                    return
                results = [trace_result(trace) for trace in observation.runs.values()]
                expired = time.monotonic() - request.created >= RESULT_TIMEOUT
                if None in results and not expired:
                    continue
                status = (RequestState.ERR if "ERR" in results else
                          RequestState.UNKNOWN if expired or observation.too_many
                          or "UNKNOWN" in results else RequestState.OK)
                await responses.complete(request_id, status, expected=RequestState.PENDING)
                return
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Cannot determine MeshCore automation execution result")
            # Unknown HA trace shapes must never produce a success response.
            await responses.complete(request_id, RequestState.UNKNOWN, expected=RequestState.PENDING)
        finally:
            self.watching.pop(request_id, None)
            self.observations.pop(request_id, None)

    def disable(self):
        for task in self.watching.values():
            task.cancel()
        self.watching.clear()
        self.observations.clear()

    async def close(self):
        if self.unsubscribe is not None:
            self.unsubscribe()
            self.unsubscribe = None
        # Disabled observers still belong to us until cancellation has drained.
        tasks = list(self._tasks)
        self.disable()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.watching.clear()
