"""Per-contact word permission switches on the HA device page."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .entity import CompanionEntity
from .const import CONF_ACTION_RESPONSES
from .contact_learning import LEARNING_KEYS


async def async_setup_entry(hass, entry, async_add_entities):
    known = set()
    async_add_entities([ActionResponseSwitch(entry.runtime_data, entry)] +
                       [ContactLearningSwitch(entry.runtime_data, entry, key) for key in LEARNING_KEYS])

    @callback
    def add_contacts():
        hub = entry.runtime_data
        new = (set(hub.contact_snapshot()) | set(hub.allowed)) - known
        known.update(new)
        async_add_entities([entity(hub, entry, key) for key in sorted(new)
                            for entity in (AllowedContact, FavoriteContact)])

    add_contacts()
    entry.async_on_unload(entry.runtime_data.async_add_listener(add_contacts))


class ActionResponseSwitch(CompanionEntity, SwitchEntity):
    _attr_translation_key = "action_responses"
    _attr_icon = "mdi:message-check-outline"

    def __init__(self, hub, entry):
        super().__init__(hub, entry, "action_responses")

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.action_responses.enabled

    async def _set_enabled(self, enabled):
        hub = self.coordinator
        hub.hass.config_entries.async_update_entry(
            hub.entry, options={**hub.entry.options, CONF_ACTION_RESPONSES: enabled})
        if not enabled:
            hub.action_responses.disable_reply()
        hub.options_updated()

    async def async_turn_on(self, **kwargs):
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs):
        await self._set_enabled(False)


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


class FavoriteContact(AllowedContact):
    _attr_translation_key = "favorite_contact"
    _attr_icon = "mdi:star"

    def __init__(self, hub, entry, key):
        CompanionEntity.__init__(self, hub, entry, f"favorite_{key}")
        self.key = key
        self._last_name = key[:12]

    @property
    def is_on(self):
        return bool(self.coordinator.contact_snapshot().get(self.key, {}).get("flags", 0) & 1)

    @property
    def available(self):
        return self.key in self.coordinator.contact_snapshot() and self.coordinator.last_update_success

    async def _set(self, enabled):
        try:
            await self.coordinator.set_favorite(self.key, enabled)
        except (ValueError, OSError, ConnectionError) as error:
            raise HomeAssistantError(str(error)) from error

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)


class ContactLearningSwitch(CompanionEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:account-plus"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, key)
        self.key = key
        self._attr_translation_key = key

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.learning[self.key]

    async def _set(self, enabled):
        hub = self.coordinator
        hub.hass.config_entries.async_update_entry(hub.entry, options={**hub.entry.options, self.key: enabled})
        hub.options_updated()
        await hub.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)
