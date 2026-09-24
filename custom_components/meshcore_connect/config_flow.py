import voluptuous as vol
from contextlib import nullcontext
from uuid import uuid4
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .client import connect
from .const import CONF_ALLOWED, CONF_WORDS, DOMAIN, CONF_MODE, MODE_GATEWAY_COMPANION
from .gateway_state import GatewayState
from .gateway_transport import GatewayAuthError, GatewayProtocolError, GatewayTlsError
from .message import allowed_keys, public_key
from .management import ContactInputError
from .contact_learning import LEARNING_KEYS, learning_options
from .words import configured_words, validate_word, word_options


class MeshCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    async def _probe_gateway(self, data, state, entry):
        hub = self.hass.data.get(DOMAIN, {}).get(entry.entry_id) if entry else None
        async with (hub.lock if hub else nullcontext()):
            if hub:
                await hub._disconnect()
            client = None
            try:
                client = await connect(data, gateway_state=state)
            finally:
                if client:
                    await client.disconnect()

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["gateway", "serial", "tcp"])

    async def async_step_gateway(self, user_input=None):
        errors = {}
        entry = getattr(self, "_gateway_entry", None)
        defaults = entry.data if entry else {}
        if user_input is not None:
            try:
                data = {**defaults, **user_input, "transport": "tcp", CONF_MODE: MODE_GATEWAY_COMPANION}
                if entry and data.get("gateway_identity"):
                    state = await GatewayState.load(self.hass, data["gateway_identity"])
                else:
                    state = GatewayState.create()
                for other in self._async_current_entries():
                    if (other is not entry and other.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION
                            and other.data.get("host", "").lower() == data["host"].lower()
                            and other.data.get("port") == data["port"]):
                        return self.async_abort(reason="already_configured")
                await self._probe_gateway(data, state, entry)
                data["gateway_identity"] = state.public_key
                if not entry:
                    await self.async_set_unique_id(state.public_key)
                    self._abort_if_unique_id_configured()
                state.bind(self.hass)
                await state.save()
                if entry:
                    return self.async_update_reload_and_abort(entry, data_updates=data,
                        reason="reauth_successful" if self.source == "reauth" else "reconfigure_successful")
                return self.async_create_entry(title=data["companion_name"], data={**data, CONF_ALLOWED: []})
            except GatewayTlsError:
                errors["base"] = "gateway_tls_failed"
            except GatewayAuthError:
                errors["base"] = "invalid_auth"
            except GatewayProtocolError:
                errors["base"] = "not_gateway"
            except (OSError, ConnectionError, TimeoutError):
                errors["base"] = "gateway_unavailable"
            except (KeyError, ValueError):
                errors["base"] = "invalid_gateway"
            finally:
                if entry and errors:
                    hub = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
                    if hub:
                        self.hass.async_create_task(hub.async_request_refresh())
        schema = vol.Schema({
            vol.Required("host", default=defaults.get("host", "")): str,
            vol.Required("port", default=defaults.get("port", 5001)): vol.All(vol.Coerce(int), vol.In((5001, 5002, 5003))),
            vol.Required("service_key"): selector.TextSelector({"type": "password"}),
            vol.Required("companion_name", default=defaults.get("companion_name", "Home Assistant")): str,
            vol.Optional("gateway_tls", default=defaults.get("gateway_tls", False)): bool,
            vol.Optional("gateway_certificate", default=defaults.get("gateway_certificate", "")): selector.TextSelector({"multiline": True}),
        })
        return self.async_show_form(step_id="gateway", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data):
        self._gateway_entry = self._get_reauth_entry()
        if self._gateway_entry.data.get(CONF_MODE) != MODE_GATEWAY_COMPANION:
            return self.async_abort(reason="not_gateway")
        return await self.async_step_gateway()

    async def async_step_reconfigure(self, user_input=None):
        self._gateway_entry = self._get_reconfigure_entry()
        if self._gateway_entry.data.get(CONF_MODE) != MODE_GATEWAY_COMPANION:
            return self.async_abort(reason="not_gateway")
        return await self.async_step_gateway(user_input)

    async def async_step_serial(self, user_input=None):
        return await self._connection("serial", user_input, {
            vol.Required("path", default="/dev/serial/by-id/"): str,
        })

    async def async_step_tcp(self, user_input=None):
        return await self._connection("tcp", user_input, {
            vol.Required("host"): str,
            vol.Required("port", default=5000): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })

    async def _connection(self, kind, user_input, schema):
        errors = {}
        if user_input is not None:
            client = None
            try:
                data = {**user_input, "transport": kind, CONF_ALLOWED: []}
                client = await connect(data)
                key = client.self_info["public_key"]
                await self.async_set_unique_id(key)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="MeshCore Connect", data=data)
            except (OSError, ConnectionError, TimeoutError, KeyError, ValueError):
                errors["base"] = "cannot_connect"
            finally:
                if client:
                    await client.disconnect()
        return self.async_show_form(step_id=kind, data_schema=vol.Schema(schema), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MeshCoreOptionsFlow()


class MeshCoreOptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self._editing_word = None
        self._channels = []
        self._favorite_keys = None

    @property
    def hub(self):
        hub = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if hub is None:
            raise ConnectionError("Integration is not loaded")
        return hub

    def save(self, **changes):
        options = word_options(self.config_entry, self.words())
        options.update(changes)
        return self.async_create_entry(title="", data=options)

    def keys(self):
        return self.config_entry.options.get(CONF_ALLOWED, self.config_entry.data.get(CONF_ALLOWED, []))

    def words(self):
        return configured_words(self.config_entry)

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=[
            "contact_add", "contacts", "allowed", "words", "channels"])

    async def async_step_contacts(self, user_input=None):
        return self.async_show_menu(step_id="contacts", menu_options=[
            "contact_add", "contact_remove", "favorites", "contact_learning"])

    async def async_step_contact_learning(self, user_input=None):
        if user_input is not None:
            return self.save(**{key: bool(user_input.get(key, False)) for key in LEARNING_KEYS})
        defaults = learning_options(self.config_entry.options,
                                    self.config_entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION)
        return self.async_show_form(step_id="contact_learning", data_schema=vol.Schema({
            vol.Optional(key, default=defaults[key]): bool for key in LEARNING_KEYS
        }))

    async def async_step_channels(self, user_input=None):
        return self.async_show_menu(step_id="channels", menu_options=["channel_add", "channel_remove"])

    async def async_step_words(self, user_input=None):
        self._editing_word = None
        return self.async_show_menu(step_id="words", menu_options=[
            "word_add", "word_edit", "word_remove"])

    async def async_step_allowed(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                keys = allowed_keys(",".join(user_input.get(CONF_ALLOWED, [])))
                return self.save(**{CONF_ALLOWED: keys})
            except ValueError:
                errors[CONF_ALLOWED] = "invalid_key"
        try:
            contacts = await self.hub.refresh_contacts()
        except (OSError, ConnectionError, ValueError):
            contacts = []
            errors["base"] = "cannot_connect"
        labels = {c["public_key"]: f'{c["name"]} ({c["public_key"][:12]})' for c in contacts}
        for key in self.keys():
            labels.setdefault(key, key)
        return self.async_show_form(step_id="allowed", data_schema=vol.Schema({
            vol.Optional(CONF_ALLOWED, default=self.keys()): selection(labels, multiple=True),
        }), errors=errors)

    async def async_step_favorites(self, user_input=None):
        errors = {}
        try:
            if user_input is not None:
                await self.hub.set_favorites(user_input.get("contacts", []), known_keys=self._favorite_keys)
                return self.save()
            contacts = await self.hub.refresh_contacts()
        except (OSError, ConnectionError, ValueError):
            return self.async_abort(reason="device_error")
        self._favorite_keys = {c["public_key"] for c in contacts}
        return self.async_show_form(step_id="favorites", data_schema=vol.Schema({
            vol.Optional("contacts", default=[c["public_key"] for c in contacts if c["favorite"]]):
                selection({c["public_key"]: f'{c["name"]} ({c["public_key"][:12]})' for c in contacts}, True),
        }), errors=errors)

    async def async_step_contact_add(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await self.hub.add_contact(user_input["public_key"], user_input["name"],
                                           int(user_input["type"]), user_input.get("favorite", False))
                if user_input.get("allowed", False):
                    return self.save(**{CONF_ALLOWED: sorted(set(self.keys()) | {public_key(user_input["public_key"])})})
                return self.save()
            except ContactInputError as error:
                errors["base"] = error.code
            except (OSError, ConnectionError, ValueError):
                errors["base"] = "device_error"
        schema = vol.Schema({
            vol.Required("public_key"): str, vol.Required("name"): str,
            vol.Required("type", default="1"): selector.SelectSelector({
                "options": ["1", "2", "3"], "translation_key": "contact_type"}),
            vol.Optional("favorite", default=False): bool,
            vol.Optional("allowed", default=False): bool,
        })
        return self.async_show_form(step_id="contact_add", data_schema=
            self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_contact_remove(self, user_input=None):
        errors = {}
        try:
            if user_input is not None:
                if not user_input.get("confirm"):
                    errors["confirm"] = "confirm_required"
                else:
                    key = user_input["contact"]
                    await self.hub.remove_contact(key)
                    return self.save(**{CONF_ALLOWED: [k for k in self.keys() if k != key]})
            contacts = await self.hub.refresh_contacts()
        except (OSError, ConnectionError, ValueError):
            errors["base"] = "device_error"
            contacts = []
        return self.async_show_form(step_id="contact_remove", data_schema=vol.Schema({
            vol.Required("contact"): selection({c["public_key"]: f'{c["name"]} ({c["public_key"][:12]})' for c in contacts}),
            vol.Required("confirm", default=False): bool,
        }), errors=errors)

    async def async_step_channel_add(self, user_input=None):
        errors = {}
        try:
            if user_input is not None:
                await self.hub.add_channel(int(user_input["slot"]), user_input["name"], user_input.get("secret", ""))
                return self.save()
            self._channels = await self.hub.refresh_channels()
        except (OSError, ConnectionError, ValueError):
            errors["base"] = "device_error"
        schema = vol.Schema({
            vol.Required("slot"): selection({str(c["index"]): str(c["index"]) for c in self._channels if not c["name"]}),
            vol.Required("name"): str,
            vol.Optional("secret"): selector.TextSelector({"type": "password"}),
        })
        return self.async_show_form(step_id="channel_add", data_schema=
            self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_channel_remove(self, user_input=None):
        errors = {}
        try:
            if user_input is not None:
                if not user_input.get("confirm"):
                    errors["confirm"] = "confirm_required"
                else:
                    index = int(user_input["slot"])
                    name = next(c["name"] for c in self._channels if c["index"] == index)
                    await self.hub.remove_channel(index, name)
                    return self.save()
            self._channels = await self.hub.refresh_channels()
        except (OSError, ConnectionError, ValueError, StopIteration):
            errors["base"] = "device_error"
        return self.async_show_form(step_id="channel_remove", data_schema=vol.Schema({
            vol.Required("slot"): selection({str(c["index"]): f'{c["index"]}: {c["name"]}' for c in self._channels if c["name"]}),
            vol.Required("confirm", default=False): bool,
        }), errors=errors)

    async def async_step_word_add(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                word = validate_word(user_input["word"])
                words = self.words()
                if any(value == word and key != self._editing_word for key, value in words.items()):
                    errors["word"] = "word_exists"
                else:
                    if self._editing_word and self._editing_word not in words:
                        raise ValueError("Word no longer exists")
                    words[self._editing_word or uuid4().hex] = word
                    return self.save(**{CONF_WORDS: words})
            except (ValueError, vol.Invalid):
                errors["base"] = "invalid_word"
        defaults = user_input or {"word": self.words().get(self._editing_word, "")}
        return self.async_show_form(step_id="word_add", data_schema=
            self.add_suggested_values_to_schema(vol.Schema({
                vol.Required("word"): str,
            }), defaults), errors=errors)

    async def async_step_word_edit(self, user_input=None):
        if user_input is not None and user_input["word"] in self.words():
            self._editing_word = user_input["word"]
            return await self.async_step_word_add()
        return self.async_show_form(step_id="word_edit", data_schema=vol.Schema({
            vol.Required("word"): selection(self.words()),
        }))

    async def async_step_word_remove(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get("confirm"):
                words = self.words()
                words.pop(user_input["word"], None)
                return self.save(**{CONF_WORDS: words})
            errors["confirm"] = "confirm_required"
        return self.async_show_form(step_id="word_remove", data_schema=vol.Schema({
            vol.Required("word"): selection(self.words()),
            vol.Required("confirm", default=False): bool,
        }), errors=errors)


def selection(labels, multiple=False):
    return selector.SelectSelector({"options": [{"value": key, "label": label} for key, label in labels.items()],
                                    "multiple": multiple, "mode": "dropdown"})
