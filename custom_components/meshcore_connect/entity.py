"""Entities belonging to a MeshCore companion in Home Assistant."""
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .management import ContactInputError


class CompanionEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, entry, suffix):
        super().__init__(hub)
        self._attr_unique_id = f"{entry.unique_id}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)


class ContactDraftEntity(CompanionEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hub, entry, field):
        super().__init__(hub, entry, f"new_contact_{field}")
        self.field = field
        self._attr_translation_key = f"new_contact_{field}"

    @property
    def available(self):
        return not self.coordinator.contact_draft_saving

    def set_value(self, value):
        try:
            self.coordinator.set_contact_draft_value(self.field, value)
        except ContactInputError as error:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key=error.code) from error
