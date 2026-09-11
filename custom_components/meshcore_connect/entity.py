"""Entities belonging to a MeshCore companion in Home Assistant."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class CompanionEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, entry, suffix):
        super().__init__(hub)
        self._attr_unique_id = f"{entry.unique_id}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)
