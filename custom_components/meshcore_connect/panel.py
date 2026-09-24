"""Admin-only companion management and live messages over HA WebSocket."""
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback

from .const import DOMAIN, CONF_ACTION_RESPONSES, EVENT_RECEIVED, CONF_MODE, MODE_GATEWAY_COMPANION
from .contact_learning import LEARNING_KEYS
from .management import ContactInputError
from .message import public_key
from .gateway_transport import tls_context, certificate_fingerprint

PANEL = "meshcore-connect"
DATA = DOMAIN + "_panel"
BASE = "/meshcore_connect_panel"
SETTINGS = (*LEARNING_KEYS, CONF_ACTION_RESPONSES)
SCHEMAS = {
    "gateway_tls": vol.Schema({vol.Required("enabled"): bool,
                               vol.Required("certificate"): vol.All(str, vol.Length(max=4096))}),
    "refresh": vol.Schema({}),
    "add": vol.Schema({vol.Required("public_key"): str, vol.Required("name"): str,
                       vol.Required("kind"): vol.In((1, 2, 3)),
                       vol.Optional("favorite", default=False): bool,
                       vol.Optional("allowed", default=False): bool}),
    "remove": vol.Schema({vol.Required("public_key"): str, vol.Required("confirm"): vol.All(bool, vol.In((True,)))}),
    "favorite": vol.Schema({vol.Required("public_key"): str, vol.Required("enabled"): bool}),
    "allowed": vol.Schema({vol.Required("public_key"): str, vol.Required("enabled"): bool}),
    "settings": vol.Schema({vol.Required("key"): vol.In(SETTINGS), vol.Required("enabled"): bool}),
    "word_save": vol.Schema({vol.Required("text"): str,
                             vol.Optional("slot", default=None): vol.Any(None, str),
                             vol.Optional("original", default=None): vol.Any(None, str)}),
    "word_remove": vol.Schema({vol.Required("slot"): str, vol.Required("original"): str,
                               vol.Required("confirm"): vol.All(bool, vol.In((True,)))}),
}


def snapshot(hass):
    entries = []
    for entry_id, hub in hass.data.get(DOMAIN, {}).items():
        entries.append({"entry_id": entry_id, "name": hub.entry.title,
                        "connected": bool(hub.client and hub.client.is_connected and not hub.stopping),
                        "contacts": [{**contact, "allowed": contact["public_key"] in hub.allowed}
                                     for contact in hub.contact_list()],
                        "words": hub.words, "messages": list(hub.message_history),
                        "settings": {**hub.learning, CONF_ACTION_RESPONSES: hub.action_responses.enabled},
                        "gateway_tls": {"enabled": hub.entry.data.get("gateway_tls", False),
                                        "certificate": hub.entry.data.get("gateway_certificate", ""),
                                        "fingerprint": certificate_fingerprint(hub.entry.data.get("gateway_certificate", ""))}
                            if hub.entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION else None})
    return {"entries": entries}


async def mutate(hub, action, values):
    values = SCHEMAS[action](values)
    if action == "gateway_tls":
        if hub.entry.data.get(CONF_MODE) != MODE_GATEWAY_COMPANION:
            raise ContactInputError("invalid_gateway_tls")
        try:
            await hub.hass.async_add_executor_job(tls_context, values["enabled"], values["certificate"])
        except ValueError as error:
            raise ContactInputError("invalid_gateway_tls") from error
        async with hub.lock:
            await hub._disconnect()
            hub.hass.config_entries.async_update_entry(hub.entry, data={**hub.entry.data,
                "gateway_tls": values["enabled"], "gateway_certificate": values["certificate"]})
        hub.hass.async_create_task(hub.async_request_refresh())
    elif action == "refresh":
        await hub.refresh_contacts()
    elif action == "add":
        key = public_key(values["public_key"])
        await hub.add_contact(key, values["name"], values["kind"], values["favorite"])
        if values["allowed"]:
            hub.set_allowed(key, True)
    elif action == "remove":
        key = public_key(values["public_key"])
        await hub.remove_contact(key)
        hub.set_allowed(key, False)
    elif action == "favorite":
        await hub.set_favorite(values["public_key"], values["enabled"])
    elif action == "allowed":
        hub.set_allowed(values["public_key"], values["enabled"])
    elif action in ("word_save", "word_remove"):
        slot = values["slot"]
        if slot is not None and (slot not in hub.words or hub.words[slot] != values["original"]):
            raise ContactInputError("stale_word")
        text = values["text"] if action == "word_save" else ""
        if action == "word_save" and not text.strip():
            raise ContactInputError("invalid_word")
        try:
            hub.set_word(slot, text)
        except ValueError as error:
            raise ContactInputError("invalid_word") from error
    else:
        key, enabled = values["key"], values["enabled"]
        hub.hass.config_entries.async_update_entry(hub.entry, options={**hub.entry.options, key: enabled})
        if key == CONF_ACTION_RESPONSES and not enabled:
            hub.action_responses.disable_reply()
        hub.options_updated()
        if key in LEARNING_KEYS:
            await hub.async_request_refresh()


@websocket_api.websocket_command({
    vol.Required("type"): DOMAIN + "/panel",
    vol.Optional("action", default="state"): vol.In(("state", *SCHEMAS)),
    vol.Optional("entry_id"): str,
    vol.Optional("values", default=dict): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_panel(hass, connection, msg):
    try:
        if msg["action"] != "state":
            hub = hass.data.get(DOMAIN, {}).get(msg.get("entry_id"))
            if hub is None:
                connection.send_error(msg["id"], "not_loaded", "Integration is not loaded")
                return
            await mutate(hub, msg["action"], msg["values"])
        connection.send_result(msg["id"], snapshot(hass))
    except ContactInputError as error:
        connection.send_error(msg["id"], error.code, error.code)
    except (ValueError, vol.Invalid, KeyError):
        connection.send_error(msg["id"], "invalid_contact", "Invalid or stale contact input")
    except (ConnectionError, OSError, TimeoutError):
        connection.send_error(msg["id"], "device_error", "Device did not confirm the operation")


@websocket_api.websocket_command({vol.Required("type"): DOMAIN + "/panel_messages"})
@websocket_api.require_admin
@callback
def ws_messages(hass, connection, msg):
    @callback
    def received(event):
        data = event.data
        hub = hass.data.get(DOMAIN, {}).get(data.get("entry_id"))
        if hub is not None and not hub.stopping:
            # Only forward records actually accepted by this coordinator.
            record = next((item for item in hub.message_history if item["id"] == data.get("id")), None)
            if record is not None:
                connection.send_event(msg["id"], record)

    connection.subscriptions[msg["id"]] = hass.bus.async_listen(EVENT_RECEIVED, received)
    connection.send_result(msg["id"])


async def async_setup_panel(hass):
    state = hass.data.setdefault(DATA, {})
    if not state.get("registered"):
        root = Path(__file__).parent
        await hass.http.async_register_static_paths([
            StaticPathConfig(BASE + "/panel.js", str(root / "web/panel.js"), False),
            StaticPathConfig(BASE + "/logo.png", str(root / "brand/icon.png"), True),
        ])
        websocket_api.async_register_command(hass, ws_panel)
        websocket_api.async_register_command(hass, ws_messages)
        state["registered"] = True
    if not state.get("visible"):
        await panel_custom.async_register_panel(
            hass, frontend_url_path=PANEL, webcomponent_name="meshcore-connect-panel",
            sidebar_title="MeshCore Connect", sidebar_icon="mdi:radio-handheld",
            module_url=BASE + "/panel.js?v=26.09.64", require_admin=True)
        state["visible"] = True


def async_remove_panel(hass):
    state = hass.data.get(DATA, {})
    if state.get("visible"):
        frontend.async_remove_panel(hass, PANEL)
        state["visible"] = False
