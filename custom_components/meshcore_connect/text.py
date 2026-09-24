"""Editable words on the HA device page, with a separate add-word field."""
from homeassistant.components.text import TextEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .entity import CompanionEntity, ContactDraftEntity


async def async_setup_entry(hass, entry, async_add_entities):
    known = set()
    async_add_entities([WordText(entry.runtime_data, entry, None)] +
                       [ContactDraftText(entry.runtime_data, entry, field) for field in ("name", "public_key")])

    @callback
    def add_words():
        new = set(entry.runtime_data.words) - known
        known.update(new)
        async_add_entities([WordText(entry.runtime_data, entry, key) for key in sorted(new)])

    add_words()
    entry.async_on_unload(entry.runtime_data.async_add_listener(add_words))


class ContactDraftText(ContactDraftEntity, TextEntity):
    _attr_native_min = 0
    _attr_icon = "mdi:account-edit"

    def __init__(self, hub, entry, field):
        super().__init__(hub, entry, field)
        self._attr_native_max = 64 if field == "public_key" else 31

    @property
    def native_value(self):
        return self.coordinator.contact_draft[self.field]

    async def async_set_value(self, value):
        self.set_value(value)


class WordText(CompanionEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = 130
    _attr_native_min = 0
    _attr_icon = "mdi:form-textbox"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, f"word_text_{key}" if key else "new_word")
        self.key = key
        self._attr_translation_key = "edit_word" if key else "new_word"
        self._last_name = hub.words.get(key, "")

    @property
    def translation_placeholders(self):
        self._last_name = self.coordinator.words.get(self.key, self._last_name)
        return {"word": self._last_name}

    @property
    def native_value(self):
        return self.coordinator.words.get(self.key, "")

    @property
    def available(self):
        return self.key is None or self.key in self.coordinator.words

    async def async_set_value(self, value):
        try:
            self.coordinator.set_word(self.key, value)
        except ValueError as error:
            raise HomeAssistantError(str(error)) from error
        self.async_write_ha_state()
