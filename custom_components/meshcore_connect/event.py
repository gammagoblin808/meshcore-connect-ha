"""One repeatable event entity per configured word; never executes actions."""
from homeassistant.components.event import EventEntity
from homeassistant.core import callback

from .const import EVENT_WORD
from .entity import CompanionEntity


async def async_setup_entry(hass, entry, async_add_entities):
    known = set()

    @callback
    def add_words():
        new = set(entry.runtime_data.words) - known
        known.update(new)
        async_add_entities([WordEvent(entry.runtime_data, entry, key) for key in sorted(new)])

    add_words()
    entry.async_on_unload(entry.runtime_data.async_add_listener(add_words))


class WordEvent(CompanionEntity, EventEntity):
    _attr_event_types = ["received"]
    _attr_icon = "mdi:message-flash"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, f"word_{key}")
        self.key, self.entry_id = key, entry.entry_id
        self._last_name = hub.words[key]

    @property
    def name(self):
        self._last_name = self.coordinator.words.get(self.key, self._last_name)
        return self._last_name

    @property
    def available(self):
        return super().available and self.key in self.coordinator.words

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen(EVENT_WORD, self._received))

    @callback
    def _received(self, event):
        data, hub = event.data, self.coordinator
        # Authorization can change while the bus event waits to be delivered.
        if (not self.available or hub.stopping or data.get("entry_id") != self.entry_id
                or data.get("word_id") != self.key or data.get("text") != hub.words.get(self.key)
                or data.get("public_key") not in hub.allowed
                or data.get("public_key") not in hub.contact_snapshot()):
            return
        self.async_set_context(event.context)
        self._trigger_event("received", {
            **{k: data[k] for k in ("public_key", "text", "sender_timestamp")},
            "entry_id": self.entry_id, "request_id": data.get("request_id"),
        })
        self.async_write_ha_state()
