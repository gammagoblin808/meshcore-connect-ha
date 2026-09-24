"""A read-only status target per word, configured on the companion device page."""
from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .entity import CompanionEntity, ContactDraftEntity
from .status_query import CONF_STATUS_QUERIES, DISABLED, DOMAINS


async def async_setup_entry(hass, entry, async_add_entities):
    known = set()
    async_add_entities([ContactDraftType(entry.runtime_data, entry)])

    @callback
    def add_words():
        new = set(entry.runtime_data.words) - known
        known.update(new)
        async_add_entities([StatusTarget(entry.runtime_data, entry, key) for key in sorted(new)])

    add_words()
    entry.async_on_unload(entry.runtime_data.async_add_listener(add_words))


class ContactDraftType(ContactDraftEntity, SelectEntity):
    _attr_icon = "mdi:devices"
    _attr_options = ["1", "2", "3"]

    def __init__(self, hub, entry):
        super().__init__(hub, entry, "type")

    @property
    def current_option(self):
        return self.coordinator.contact_draft["type"]

    async def async_select_option(self, option):
        self.set_value(option)


class StatusTarget(CompanionEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:text-box-search-outline"
    _attr_translation_key = "status_target"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, f"status_target_{key}")
        self.key = key
        self._last_name = hub.words.get(key, "")

    @property
    def translation_placeholders(self):
        self._last_name = self.coordinator.words.get(self.key, self._last_name)
        return {"word": self._last_name}

    @property
    def available(self):
        return self.key in self.coordinator.words

    @property
    def current_option(self):
        return self.coordinator.entry.options.get(CONF_STATUS_QUERIES, {}).get(self.key, DISABLED)

    @property
    def options(self):
        ids = {s.entity_id for s in self.coordinator.hass.states.async_all() if s.domain in DOMAINS}
        if self.current_option != DISABLED:
            ids.add(self.current_option)
        return [DISABLED, *sorted(ids)]

    async def async_select_option(self, option):
        hub = self.coordinator
        if not self.available or option not in self.options:
            raise HomeAssistantError("Unknown status target")
        word = hub.words[self.key]
        if option != DISABLED and (word == "SOS!" or word.startswith("SOS! GPS: ")):
            raise HomeAssistantError("SOS words cannot be used as status queries")
        mapping = dict(hub.entry.options.get(CONF_STATUS_QUERIES, {}))
        if option == DISABLED:
            mapping.pop(self.key, None)
        else:
            mapping[self.key] = option
        hub.hass.config_entries.async_update_entry(
            hub.entry, options={**hub.entry.options, CONF_STATUS_QUERIES: mapping})
        hub.options_updated()
        self.async_write_ha_state()
