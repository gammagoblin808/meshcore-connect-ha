import asyncio
from collections import OrderedDict
from datetime import timedelta
import logging
import time
from uuid import uuid4

from meshcore import EventType
from homeassistant.core import Context
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import checked, connect
from .const import CONF_ALLOWED, DOMAIN, EVENT_MESSAGE, EVENT_SOS, EVENT_WORD, EVENT_RECEIVED
from .management import CompanionManagement
from .message import public_key, trusted_message
from .words import configured_words, validate_word, word_options
from .action_response import ActionResponses
from .status_query import StatusQueries

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

    @property
    def words(self):
        return configured_words(self.entry)

    @property
    def allowed(self):
        return self.entry.options.get(CONF_ALLOWED, self.entry.data.get(CONF_ALLOWED, []))

    def options_updated(self):
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

    async def _async_update_data(self):
        async with self.lock:
            if self.stopping:
                return self.state
            try:
                if not self.client or not self.client.is_connected:
                    await self._disconnect()
                    self.client = await connect(self.entry.data)
                    # Subscribe before requesting contacts to avoid fast-response races.
                    await self._read_contacts()
                    self.subscriptions.append(self.client.subscribe(EventType.MESSAGES_WAITING, self._wake))
                    self.battery_at = 0
                    self.stats_at = 0
                if time.monotonic() - self.battery_at >= 300 or not self.battery_at:
                    battery = checked(await self.client.commands.get_bat(), EventType.BATTERY)
                    self.state["voltage"] = battery["level"] / 1000.0
                    self.battery_at = time.monotonic()
                if time.monotonic() - self.contacts_at >= 300:
                    await self._read_contacts()
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
