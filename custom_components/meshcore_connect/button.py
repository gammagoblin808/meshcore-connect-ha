from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODE, MODE_GATEWAY_COMPANION
from .entity import CompanionEntity
from .management import ContactInputError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SaveContact(entry.runtime_data, entry), RefreshContacts(entry.runtime_data, entry)])
    if entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION:
        async_add_entities([AnnounceCompanion(entry.runtime_data, entry)])


class SaveContact(CompanionEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "save_contact"
    _attr_icon = "mdi:account-plus"

    def __init__(self, hub, entry):
        super().__init__(hub, entry, "save_contact")

    @property
    def available(self):
        return super().available and not self.coordinator.contact_draft_saving

    async def async_press(self):
        try:
            await self.coordinator.save_contact_draft()
        except ContactInputError as error:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key=error.code) from error
        except (OSError, ConnectionError, ValueError) as error:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="contact_save_failed") from error


class AnnounceCompanion(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "announce_companion"
    _attr_icon = "mdi:access-point"

    def __init__(self, hub, entry):
        super().__init__(hub)
        self._attr_unique_id = f"{entry.unique_id}_announce_companion"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    async def async_press(self):
        try:
            async with self.coordinator.lock:
                self.coordinator.require_client()
                await self.coordinator.client.commands.send_advert()
        except (OSError, ValueError, ConnectionError, TimeoutError) as error:
            raise HomeAssistantError("Gateway could not send the announcement; check its radio TX permission") from error


class RefreshContacts(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "refresh_contacts"
    _attr_icon = "mdi:account-sync"

    def __init__(self, hub, entry):
        super().__init__(hub)
        self._attr_unique_id = f"{entry.unique_id}_refresh_contacts"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)

    async def async_press(self):
        try:
            await self.coordinator.refresh_contacts()
        except (ValueError, ConnectionError, OSError) as error:
            raise HomeAssistantError(str(error)) from error
