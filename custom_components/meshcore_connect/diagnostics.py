"""Allowlisted diagnostics: no service keys, identity seeds or channel secrets."""
from .const import CONF_MODE, DOMAIN, MODE_STANDARD


async def async_get_config_entry_diagnostics(hass, entry):
    hub = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    client = hub.client if hub else None
    return {"mode": entry.data.get(CONF_MODE, MODE_STANDARD),
            "port": entry.data.get("port"), "connected": bool(client and client.is_connected),
            "contacts": len(hub.contact_snapshot()) if hub else None,
            "raw_gateway": entry.data.get(CONF_MODE) == "gateway_companion"}
