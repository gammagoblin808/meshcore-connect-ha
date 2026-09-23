import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import CONF_MODE, DOMAIN, MODE_STANDARD
from .action_response import automation_actions
from .coordinator import MeshCoreCoordinator
from .words import configured_words, word_options

PLATFORMS = [Platform.SENSOR, Platform.NOTIFY, Platform.BUTTON, Platform.EVENT, Platform.SWITCH, Platform.TEXT, Platform.SELECT]


async def async_migrate_entry(hass, entry):
    if entry.version > 3:
        return False
    if entry.version < 3:
        data = {**entry.data, CONF_MODE: entry.data.get(CONF_MODE, MODE_STANDARD)}
        changes = {"data": data, "version": 3}
        if entry.version == 1:
            changes["options"] = word_options(entry, configured_words(entry))
        hass.config_entries.async_update_entry(entry, **changes)
    return True


async def async_setup_entry(hass, entry):
    hub = MeshCoreCoordinator(hass, entry)
    try:
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)
        hub.device_id = device.id
        await hub.async_config_entry_first_refresh()
        entry.runtime_data = hub
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_options_updated))
        hub.messages_ready = True
        await hub.async_refresh()
    except BaseException:
        await hub.close()
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise

    if not hass.services.has_service(DOMAIN, "send_message"):
        async def send_message(call):
            selected = hass.data.get(DOMAIN, {}).get(call.data["entry_id"])
            if selected is None:
                raise HomeAssistantError("MeshCore Connect entry is not loaded")
            try:
                await selected.send_message(call.data["public_key"], call.data["text"])
            except (ValueError, ConnectionError, OSError) as error:
                raise HomeAssistantError(str(error)) from error
        hass.services.async_register(DOMAIN, "send_message", send_message, schema=vol.Schema({
            vol.Required("entry_id"): cv.string,
            vol.Required("public_key"): cv.string,
            vol.Required("text"): cv.string,
        }))
        async def get_contacts(call):
            selected = hass.data.get(DOMAIN, {}).get(call.data["entry_id"])
            if selected is None:
                raise HomeAssistantError("MeshCore Connect entry is not loaded")
            try:
                return {"contacts": await selected.refresh_contacts(call.data["favorites_only"])}
            except (ValueError, ConnectionError, OSError) as error:
                raise HomeAssistantError(str(error)) from error
        hass.services.async_register(DOMAIN, "get_contacts", get_contacts,
            supports_response=SupportsResponse.ONLY, schema=vol.Schema({
                vol.Required("entry_id"): cv.string,
                vol.Optional("favorites_only", default=False): cv.boolean,
            }))
        async def execute_action(call):
            selected = hass.data.get(DOMAIN, {}).get(call.data["entry_id"])
            if selected is None:
                raise HomeAssistantError("MeshCore Connect entry is not loaded")
            return await selected.action_responses.execute(
                call.data["request_id"],
                automation_actions(hass, call.data["automation_entity"]), call.context)
        hass.services.async_register(DOMAIN, "execute_action", execute_action,
            supports_response=SupportsResponse.OPTIONAL, schema=vol.Schema({
                vol.Required("entry_id"): cv.string,
                vol.Required("request_id"): cv.string,
                vol.Required("automation_entity"): cv.entity_id,
            }))
    return True


async def async_options_updated(hass, entry):
    entry.runtime_data.options_updated()


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.close()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, "send_message")
        hass.services.async_remove(DOMAIN, "get_contacts")
        hass.services.async_remove(DOMAIN, "execute_action")
    return True
