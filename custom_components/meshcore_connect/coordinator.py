import asyncio
from collections import OrderedDict
from copy import deepcopy
from datetime import timedelta
import logging
import time
from uuid import uuid4

from meshcore import EventType
from homeassistant.core import Context
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import checked, connect
from .const import (CONF_ALLOWED, DOMAIN, EVENT_MESSAGE, EVENT_SOS, EVENT_WORD, EVENT_RECEIVED,
                    CONF_MODE, MODE_GATEWAY_COMPANION)
from .management import CompanionManagement, empty_contact_draft
from .message import public_key, trusted_message
from .words import configured_words, validate_word, word_options
from .action_response import ActionResponses
from .status_query import StatusQueries
from .contact_learning import (LEARN_ALLOWED, LEARN_FAVORITES,
                               accepts_contact, learning_options)

LOGGER = logging.getLogger(__name__)


class MeshCoreCoordinator(CompanionManagement, DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30))
        self.entry = entry
        self.client = None
        self.lock = asyncio.Lock()
        self.subscriptions = []
        self.seen = OrderedDict()
        self.battery_at = 0
        self.state = {}
        self.stopping = False
        self.contacts = None
        self.contacts_at = time.monotonic()
        self.channels = []
        self.device_id = None
        self.stats_at = 0
        self.received_seen = OrderedDict()
        self.messages_ready = False
        self.action_responses = ActionResponses(self)
        self.status_queries = StatusQueries(self)
        self.discovered = OrderedDict()
        self._learning_applied = None
        self.contact_draft = empty_contact_draft()
        self.contact_draft_saving = False

    @property
    def learning(self):
        return learning_options(self.entry.options, self.entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION)

    @property
    def words(self):
        return configured_words(self.entry)

    @property
    def allowed(self):
        return self.entry.options.get(CONF_ALLOWED, self.entry.data.get(CONF_ALLOWED, []))

    def options_updated(self):
        if self.client and getattr(self.client, "is_gateway", False) is True:
            self.client.learning = self.learning
        self.async_update_listeners()

    def set_word(self, slot, word):
        words = self.words
        if slot is not None and slot not in words:
            raise ValueError("Word no longer exists")
        if word:
            validate_word(word)
            if any(value == word and key != slot for key, value in words.items()):
                raise ValueError("Word already exists")
            words[slot or uuid4().hex] = word
        elif slot is not None:
            words.pop(slot)
        else:
            return
        self.hass.config_entries.async_update_entry(self.entry, options=word_options(self.entry, words))
        self.options_updated()

    def set_allowed(self, key, enabled):
        key = public_key(key)
        if enabled and key not in self.contact_snapshot():
            raise ValueError("Contact is not in the companion contact list")
        allowed = set(self.allowed)
        if enabled:
            allowed.add(key)
        else:
            allowed.discard(key)
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, CONF_ALLOWED: sorted(allowed)})
        self.options_updated()

    async def close(self):
        self.stopping = True
        await self.status_queries.close()
        await self.action_responses.close()
        async with self.lock:
            await self._disconnect()

    async def _disconnect(self):
        if self.client:
            client, self.client = self.client, None
            for sub in self.subscriptions:
                client.unsubscribe(sub)
            self.subscriptions.clear()
            await client.disconnect()

    async def _wake(self, _event):
        if not self.stopping:
            self.hass.async_create_task(self.async_request_refresh())

    async def _contacts_changed(self, event):
        contact = event.payload
        if isinstance(contact, dict) and isinstance(contact.get("public_key"), str):
            key = contact["public_key"]
            discovered = deepcopy(contact)
            if self.discovered.get(key, {}).get("newly_learned"):
                discovered["newly_learned"] = True
            self.discovered[key] = discovered
            if len(self.discovered) > 350:
                self.discovered.popitem(last=False)
        self.contacts_at = 0
        await self._wake(event)

    async def _configure_contact_learning(self):
        if self.entry.data.get(CONF_MODE) != MODE_GATEWAY_COMPANION:
            # Let HA select discoveries. Firmware auto-eviction must not remove favorites.
            if self._learning_applied is not self.client:
                checked(await self.client.commands.set_manual_add_contacts(True), EventType.OK)
                self._learning_applied = self.client

    async def _learn_contacts(self):
        gateway = self.entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION
        policy = self.learning
        await self._configure_contact_learning()
        # Bound writes per refresh so discovery cannot starve messaging or UI changes.
        for _ in range(8):
            if not self.discovered:
                break
            key, candidate = self.discovered.popitem(last=False)
            if not accepts_contact(candidate, policy):
                continue
            try:
                key = public_key(key)
            except ValueError:
                continue
            if gateway:
                if not candidate.get("newly_learned") or key not in self.contact_snapshot():
                    continue
            else:
                if key in self.contact_snapshot():
                    continue
                info = checked(await self.client.commands.send_device_query(), EventType.DEVICE_INFO)
                capacity = info.get("max_contacts")
                if type(capacity) is not int or len(self.contact_snapshot()) >= capacity:
                    continue  # Never evict contacts to make room.
                candidate.pop("newly_learned", None)
                candidate["flags"] = int(policy[LEARN_FAVORITES])
                checked(await self.client.commands.add_contact(candidate), EventType.OK)
                await self._read_contacts()
            if policy[LEARN_ALLOWED] and key in self.contact_snapshot():
                self.set_allowed(key, True)
        if self.discovered and not self.stopping:
            self.hass.async_create_task(self.async_request_refresh())

    async def _connect(self):
        if self.entry.data.get(CONF_MODE) != MODE_GATEWAY_COMPANION:
            return await connect(self.entry.data)
        from .gateway_state import GatewayState
        from .gateway_transport import GatewayAuthError
        if not self.entry.data.get("service_key") or not self.entry.data.get("gateway_identity"):
            raise ConfigEntryAuthFailed("Configure the gateway service key and HA companion identity")
        try:
            state = await GatewayState.load(self.hass, self.entry.data["gateway_identity"])
        except (ValueError, KeyError) as error:
            raise ConfigEntryError("HA companion identity storage is missing or invalid; restore the HA backup") from error
        try:
            return await connect({**self.entry.data, **self.learning}, gateway_state=state)
        except GatewayAuthError as error:
            raise ConfigEntryAuthFailed("Gateway service key rejected") from error

    async def _async_update_data(self):
        async with self.lock:
            if self.stopping:
                return self.state
            try:
                if not self.client or not self.client.is_connected:
                    await self._disconnect()
                    self.client = await self._connect()
                    # Subscribe before requesting contacts to avoid fast-response races.
                    self.subscriptions.append(self.client.subscribe(EventType.MESSAGES_WAITING, self._wake))
                    self.subscriptions.append(self.client.subscribe(EventType.NEW_CONTACT, self._contacts_changed))
                    await self._configure_contact_learning()
                    await self._read_contacts()
                    self.battery_at = 0
                    self.stats_at = 0
                if self.entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION:
                    self.state["voltage"] = None
                    self.state["companion_public_key"] = self.client.self_info["public_key"]
                elif time.monotonic() - self.battery_at >= 300 or not self.battery_at:
                    battery = checked(await self.client.commands.get_bat(), EventType.BATTERY)
                    self.state["voltage"] = battery["level"] / 1000.0
                    self.battery_at = time.monotonic()
                if time.monotonic() - self.contacts_at >= 300:
                    await self._read_contacts()
                await self._learn_contacts()
                if not self.stats_at or time.monotonic() - self.stats_at >= 60:
                    await self._read_stats()
                if not self.messages_ready:
                    return self.state.copy()
                # Bounded draining keeps a busy mesh from monopolizing the HA loop.
                # No radio polling: these requests read the companion's local queue.
                for _ in range(16):
                    event = await self.client.commands.get_msg()
                    if event is None or event.type == EventType.ERROR:
                        raise ConnectionError("Cannot read companion messages")
                    if event.type == EventType.NO_MORE_MSGS:
                        break
                    if event.type == EventType.CONTACT_MSG_RECV:
                        self._message(event.payload)
                    elif event.type == EventType.CHANNEL_MSG_RECV:
                        self._received_message(event.payload, channel=True)
                else:
                    self.hass.async_create_task(self.async_request_refresh())
                return self.state.copy()
            except (OSError, ConnectionError, TimeoutError, ValueError, KeyError) as error:
                await self._disconnect()
                raise UpdateFailed("MeshCore companion unavailable") from error

    def _message(self, payload):
        if self.stopping:
            return
        self._received_message(payload)
        message = trusted_message(payload, self.contact_snapshot(),
                                  self.entry.options.get(CONF_ALLOWED, self.entry.data.get(CONF_ALLOWED, [])))
        if message is None:
            return
        identity = (message["public_key"], message["sender_timestamp"], message["text"])
        if identity in self.seen:
            return
        self.seen[identity] = True
        if len(self.seen) > 256:
            self.seen.popitem(last=False)
        message["entry_id"] = self.entry.entry_id
        context = Context()
        if self.status_queries.receive(message, context):
            return
        request_id = self.action_responses.register(message, context_id=context.id)
        self.hass.bus.async_fire(EVENT_MESSAGE, message, context=context)
        if message["sos"]:
            self.hass.bus.async_fire(EVENT_SOS, message.copy(), context=context)
        for slot, word in self.words.items():
            if word == message["text"]:
                self.hass.bus.async_fire(EVENT_WORD, {
                    **message, "word_id": slot, "request_id": request_id}, context=context)

    def _received_message(self, payload, channel=False):
        text = payload.get("text")
        if self.stopping or not isinstance(text, str):
            return
        identity = (channel, payload.get("channel_idx") if channel else payload.get("pubkey_prefix"),
                    payload.get("txt_type"), payload.get("sender_timestamp"), text)
        if identity in self.received_seen:
            return
        self.received_seen[identity] = True
        if len(self.received_seen) > 256:
            self.received_seen.popitem(last=False)
        prefix = payload.get("pubkey_prefix", "")
        matches = [c for k, c in self.contact_snapshot().items() if prefix and k.startswith(prefix.lower())]
        sender = matches[0].get("adv_name", prefix) if len(matches) == 1 else prefix
        self.hass.bus.async_fire(EVENT_RECEIVED, {
            "entry_id": self.entry.entry_id, "device_id": self.device_id,
            "name": getattr(self.entry, "title", "MeshCore Connect"),
            "kind": "channel" if channel else "direct", "sender": sender,
            "pubkey_prefix": prefix, "channel_idx": payload.get("channel_idx"),
            "text": text, "sender_timestamp": payload.get("sender_timestamp"),
            "snr": payload.get("SNR"), "rssi": payload.get("RSSI"),
        })

    async def _read_stats(self):
        for method, event_type, fields in (
            ("get_stats_radio", EventType.STATS_RADIO,
             ("noise_floor", "last_rssi", "last_snr", "tx_air_secs", "rx_air_secs")),
            ("get_stats_packets", EventType.STATS_PACKETS, ("recv", "sent", "recv_errors")),
        ):
            event = await getattr(self.client.commands, method)()
            values = event.payload if event is not None and event.type == event_type else {}
            for field in fields:
                self.state[field] = values.get(field)
        self.stats_at = time.monotonic()

    async def send_message(self, key, text, *, favorite_only=False, timestamp=None,
                           attempt=0, permitted=None):
        key = public_key(key)
        if not text or len(text.encode("utf-8")) > 130 or "\0" in text:
            raise ValueError("Message must contain 1 to 130 UTF-8 bytes, without NUL")
        async with self.lock:
            if permitted is not None and not permitted():
                return None
            if not self.client or not self.client.is_connected or self.stopping:
                raise ConnectionError("Companion is disconnected")
            contact = self.contact_snapshot().get(key)
            if contact is None:
                raise ValueError("Recipient is not in the companion contact list")
            if favorite_only and not contact.get("flags", 0) & 1:
                raise ValueError("Recipient is no longer a companion favorite")
            options = {} if timestamp is None else {"timestamp": timestamp, "attempt": attempt}
            return checked(await self.client.commands.send_msg(contact, text, **options), EventType.MSG_SENT)
