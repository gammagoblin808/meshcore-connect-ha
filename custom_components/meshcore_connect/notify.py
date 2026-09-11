"""Individually addressable notification targets for companion favorites."""
from homeassistant.components.notify import NotifyEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    hub = entry.runtime_data
    known = set()

    @callback
    def add_favorites():
        entities = []
        for contact in (hub.data or {}).get("contacts", []):
            key = contact["public_key"]
            if contact["favorite"] and key not in known:
                known.add(key)
                entities.append(FavoriteNotifier(hub, entry, key, contact["name"]))
        if entities:
            async_add_entities(entities)

    add_favorites()
    entry.async_on_unload(hub.async_add_listener(add_favorites))


class FavoriteNotifier(CoordinatorEntity, NotifyEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:account-star"

    def __init__(self, hub, entry, key, name):
        super().__init__(hub)
        self.key = key
        self._last_name = name
        self._attr_unique_id = f"{entry.unique_id}_favorite_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)

    @property
    def contact(self):
        return next((c for c in (self.coordinator.data or {}).get("contacts", [])
                     if c["public_key"] == self.key and c["favorite"]), None)

    @property
    def name(self):
        if contact := self.contact:
            self._last_name = contact["name"]
        return self._last_name

    @property
    def available(self):
        return super().available and self.contact is not None

    @property
    def extra_state_attributes(self):
        return {"public_key": self.key}

    async def async_send_message(self, message, title=None):
        if not self.available:
            raise HomeAssistantError("This contact is no longer an available companion favorite")
        if title:
            raise HomeAssistantError("MeshCore messages do not support a separate title")
        try:
            await self.coordinator.send_message(self.key, message, favorite_only=True)
        except (ValueError, ConnectionError, OSError) as error:
            raise HomeAssistantError(str(error)) from error
