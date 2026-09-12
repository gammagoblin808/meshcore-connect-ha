"""Correlate authorized word requests with locally configured HA actions."""
import asyncio
from collections import OrderedDict
import logging
import time
from uuid import uuid4

from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script, async_validate_actions_config
from homeassistant.helpers.script_variables import ScriptRunVariables

from .const import CONF_ACTION_RESPONSES, DOMAIN, EVENT_RESPONSE
from .automation_response import AutomationResponses
from .reply_delivery import send_reply

LOGGER = logging.getLogger(__name__)
REQUEST_TTL = 300
MAX_REQUESTS = 256
ACTION_SEQUENCE_ALIAS = "meshcore_connect_action_sequence"


def automation_actions(hass, entity_id):
    from homeassistant.components.automation import DATA_COMPONENT

    component = hass.data.get(DATA_COMPONENT)
    entity = component.get_entity(entity_id) if component else None
    config = getattr(entity, "raw_config", None) or {}
    # Read the unrendered, disabled sequence. Passing it as service data would
    # evaluate nested wait/repeat templates before the actions actually run.
    for action in config.get("actions", config.get("action", [])):
        if (action.get("alias") == ACTION_SEQUENCE_ALIAS
                and action.get("enabled") is False and action.get("sequence")):
            return action["sequence"]
    raise HomeAssistantError("Response automation has no configured MeshCore action sequence")


def response_text(status, timestamp, word):
    prefix = f"HA {status} {timestamp}: "
    # Preserve UTF-8 boundaries within the companion's private-message budget.
    suffix = word.encode("utf-8")[:130 - len(prefix)].decode("utf-8", errors="ignore")
    return prefix + suffix


class ActionResponses:
    def __init__(self, hub):
        self.hub = hub
        self.requests = OrderedDict()
        self.running = set()
        self.observer = AutomationResponses(self)

    @property
    def enabled(self):
        return self.hub.entry.options.get(CONF_ACTION_RESPONSES, False) is True

    async def close(self):
        await self.observer.close()
        tasks = list(self.running - {asyncio.current_task()})
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.requests.clear()

    def register(self, message, *, context_id=None):
        timestamp = message.get("sender_timestamp")
        if type(timestamp) is not int or not 0 <= timestamp <= 0xFFFFFFFF:
            return None
        now = time.monotonic()
        for key, request in list(self.requests.items()):
            if request["state"] != "running" and now - request["created"] > REQUEST_TTL:
                del self.requests[key]
        if len(self.requests) >= MAX_REQUESTS:
            return None
        key = uuid4().hex
        self.requests[key] = {**message, "created": now, "state": "pending",
                              "context_id": context_id, "auto_reply": self.enabled}
        if self.enabled:
            self.activity(self.requests[key], "requested")
        return key

    def activity(self, request, phase, status=None):
        hub = self.hub
        contact = hub.contact_snapshot().get(request["public_key"], {})
        hub.hass.bus.async_fire(EVENT_RESPONSE, {
            "entry_id": hub.entry.entry_id, "device_id": hub.device_id,
            "name": hub.entry.title, "phase": phase, "status": status,
            "recipient": contact.get("adv_name", request["public_key"][:12]),
            "text": request["text"], "sender_timestamp": request["sender_timestamp"],
        }, context=Context(parent_id=request.get("context_id")))

    async def _reply(self, request, status):
        def permitted():
            return (self.enabled and request.get("auto_reply") and not self.hub.stopping
                    and request["public_key"] in self.hub.allowed)

        if not permitted():
            return False
        try:
            return await send_reply(self.hub, request["public_key"], response_text(
                status, request["sender_timestamp"], request["text"]), permitted,
                lambda phase: self.activity(request, phase, status), confirm=status != "RUN")
        except Exception:
            self.activity(request, "failed", status)
            LOGGER.warning("Could not send Home Assistant action result", exc_info=True)
            return False

    async def execute(self, request_id, actions, context):
        request = self.requests.get(request_id)
        hub = self.hub
        if (request is None or hub.stopping
                or request["public_key"] not in hub.allowed
                or request["public_key"] not in hub.contact_snapshot()
                or request["text"] not in hub.words.values()):
            raise HomeAssistantError("Unknown or no longer authorized MeshCore request")
        if request["state"] != "pending":
            raise HomeAssistantError("This MeshCore request has already been handled")
        if time.monotonic() - request["created"] > REQUEST_TTL:
            raise HomeAssistantError("MeshCore request expired")
        if not actions:
            raise HomeAssistantError("Configure at least one Home Assistant action")
        # Claim before awaiting: duplicate automation runs must not repeat the action.
        request["state"] = "running"
        task = asyncio.current_task()
        self.running.add(task)
        try:
            return await self._execute(request_id, request, actions, context)
        finally:
            self.running.discard(task)

    async def _execute(self, request_id, request, actions, context):
        hub = self.hub
        await self._reply(request, "RUN")
        try:
            async with asyncio.timeout(REQUEST_TTL):
                marker = f"meshcore_completed_{request_id}"
                sequence = await async_validate_actions_config(hub.hass, cv.SCRIPT_SCHEMA([
                    *actions, {"variables": {marker: True}},
                ]))
                # A sub-sequence is owned by this service invocation, not registered
                # as a permanent top-level HA script for every incoming message.
                runner = Script(hub.hass, sequence, "MeshCore action", DOMAIN, top_level=False)
                variables = ScriptRunVariables.create_top_level({
                    "meshcore_sender": request["public_key"],
                    "meshcore_word": request["text"],
                    "meshcore_request_id": request_id,
                    "context": context,
                })
                result = await runner.async_run(variables, context=context)
        except asyncio.CancelledError:
            request["state"] = "UNKNOWN"
            raise
        except TimeoutError:
            request["state"] = "UNKNOWN"
        except Exception:
            LOGGER.exception("Home Assistant action failed")
            request["state"] = "ERR"
        else:
            request["state"] = "OK" if result and result.variables.get(marker) else "UNKNOWN"
        # A failed radio reply never repeats the actions.
        sent = await self._reply(request, request["state"])
        return {"status": request["state"], "reply_queued": sent}
