"""Explicitly configured, read-only state queries from authorized radio contacts."""
import asyncio
import logging
import time
from collections import OrderedDict

from .const import EVENT_RESPONSE
from .reply_delivery import send_reply

CONF_STATUS_QUERIES = "status_queries"
DISABLED = "disabled"
DOMAINS = frozenset(("sensor", "binary_sensor", "lock", "cover", "light", "switch",
                     "climate", "fan", "input_boolean", "input_number", "input_select"))
LOGGER = logging.getLogger(__name__)


def format_status(state, language="en"):
    de = language.startswith("de")
    if state is None:
        return "Status: nicht verfuegbar" if de else "Status: unavailable"
    value = state.state
    if de:
        value = {"unavailable": "nicht verfuegbar", "unknown": "unbekannt",
                 "locked": "verriegelt", "unlocked": "entriegelt", "jammed": "blockiert",
                 "open": "offen", "closed": "geschlossen", "opening": "oeffnet",
                 "closing": "schliesst", "on": "ein", "off": "aus"}.get(value, value)
        if state.domain == "binary_sensor":
            cls = state.attributes.get("device_class")
            if cls in ("door", "window", "opening", "garage_door"):
                value = {"on": "offen", "off": "geschlossen"}.get(state.state, value)
            elif cls == "lock":
                value = {"on": "entriegelt", "off": "verriegelt"}.get(state.state, value)
    unit = state.attributes.get("unit_of_measurement", "") if state.state not in ("unknown", "unavailable") else ""
    name = str(state.attributes.get("friendly_name", state.entity_id))
    # Reserve space for the value even when the entity has a very long name.
    detail = f"{value}{' ' + str(unit) if unit else ''}".replace("\0", "").replace("\n", " ").replace("\r", " ")
    detail = detail.encode("utf-8")[:96].decode("utf-8", errors="ignore")
    name = name.replace("\0", "").replace("\n", " ").replace("\r", " ")
    name = name.encode("utf-8")[:128 - len(detail.encode("utf-8"))].decode("utf-8", errors="ignore")
    return f"{name}: {detail}"


class StatusQueries:
    def __init__(self, hub):
        self.hub = hub
        self.tasks = set()
        self.last_query = OrderedDict()

    def receive(self, message, context):
        if message.get("sos"):
            return False
        hub = self.hub
        mapping = hub.entry.options.get(CONF_STATUS_QUERIES, {})
        slot = next((slot for slot, word in hub.words.items()
                     if word == message["text"] and slot in mapping), None)
        if slot is None:
            return False
        key = message["public_key"]
        now = time.monotonic()
        if len(self.tasks) >= 8 or now - self.last_query.get(key, -100) < 10:
            return True
        self.last_query[key] = now
        self.last_query.move_to_end(key)
        if len(self.last_query) > 256:
            self.last_query.popitem(last=False)
        task = hub.hass.async_create_task(self._reply(slot, mapping[slot], message, context))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return True

    async def _reply(self, slot, entity_id, message, context):
        hub = self.hub
        key = message["public_key"]

        def permitted():
            return (not hub.stopping and key in hub.allowed
                    and hub.words.get(slot) == message["text"]
                    and hub.entry.options.get(CONF_STATUS_QUERIES, {}).get(slot) == entity_id
                    and entity_id.split(".", 1)[0] in DOMAINS)

        def activity(phase):
            hub.hass.bus.async_fire(EVENT_RESPONSE, {
                "entry_id": hub.entry.entry_id, "device_id": hub.device_id,
                "name": hub.entry.title, "recipient": key[:12], "text": message["text"],
                "phase": phase, "status": "STATUS",
            }, context=context)

        if not permitted():
            return
        text = format_status(hub.hass.states.get(entity_id), hub.hass.config.language)
        try:
            await send_reply(hub, key, text, permitted, activity)
        except (ConnectionError, OSError, TimeoutError, ValueError):
            activity("failed")
            LOGGER.warning("Could not send radio status response")

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.clear()
