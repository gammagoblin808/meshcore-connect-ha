"""Per-contact word permission switches on the HA device page."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .entity import CompanionEntity


async def async_setup_entry(hass, entry, async_add_entities):
    known = set()

    @callback
    def add_contacts():
        hub = entry.runtime_data
        new = (set(hub.contact_snapshot()) | set(hub.allowed)) - known
        known.update(new)
        async_add_entities([AllowedContact(hub, entry, key) for key in sorted(new)])

    add_contacts()
    entry.async_on_unload(entry.runtime_data.async_add_listener(add_contacts))


class AllowedContact(CompanionEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "allowed_contact"
    _attr_icon = "mdi:account-check"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, f"allowed_{key}")
        self.key = key
        self._last_name = key[:12]

    @property
    def translation_placeholders(self):
        contact = self.coordinator.contact_snapshot().get(self.key, {})
        self._last_name = contact.get("adv_name", self._last_name)
        return {"contact": self._last_name}

    @property
    def is_on(self):
        return self.key in self.coordinator.allowed

    @property
    def available(self):
        return self.is_on or self.key in self.coordinator.contact_snapshot()

    @property
    def extra_state_attributes(self):
        return {"public_key": self.key}

    async def async_turn_on(self, **kwargs):
        try:
            self.coordinator.set_allowed(self.key, True)
        except ValueError as error:
            raise HomeAssistantError(str(error)) from error

    async def async_turn_off(self, **kwargs):
        self.coordinator.set_allowed(self.key, False)
