"""A local MeshCore companion using the RAK only as authenticated raw radio."""
import asyncio
from collections import deque
from copy import deepcopy
import hashlib
import inspect
import struct
import time
from types import SimpleNamespace

from meshcore import EventType

from .gateway_packets import (Packet, acknowledgement, advertisement, decrypt,
                              message_payload, open_private, path_size, private_message)
from .gateway_state import validate_contact
from .gateway_transport import GatewayTransport
from .message import public_key
from .contact_learning import learning_options, accepts_contact, LEARN_FAVORITES


def event(kind, payload=None):
    return SimpleNamespace(type=kind, payload={} if payload is None else payload)


class GatewayClient:
    is_gateway = True

    def __init__(self, data, state):
        self.state = state
        self.transport = GatewayTransport(data["host"], data["port"], data["service_key"])
        self.name = data.get("companion_name", "Home Assistant")
        if not self.name.strip() or "\0" in self.name or len(self.name.encode("utf-8")) > 31:
            raise ValueError("Invalid companion name")
        self.self_info = {"public_key": state.public_key, "name": self.name}
        self.commands = self
        self._subscriptions = {}
        self._worker = None
        self._messages = deque(maxlen=128)
        self._ack_at = {}
        self._stats = {"recv": 0, "sent": 0, "recv_errors": 0}
        self._radio = {}
        self.learning = learning_options(data, gateway=True)

    @property
    def contacts(self):
        return self.state.data["contacts"]

    @property
    def is_connected(self):
        return self.transport.is_connected and not self.state.failed

    async def connect(self):
        await self.transport.connect()
        self._worker = asyncio.create_task(self._receive())

    async def disconnect(self):
        if self._worker:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None
        await self.transport.close()

    def subscribe(self, kind, callback):
        token = object()
        self._subscriptions[token] = kind, callback
        return token

    def unsubscribe(self, token):
        self._subscriptions.pop(token, None)

    async def _emit(self, kind, payload=None):
        for expected, callback in list(self._subscriptions.values()):
            if expected == kind:
                result = callback(event(kind, payload))
                if inspect.isawaitable(result):
                    await result

    async def _send(self, packet):
        await self.transport.send_packet(packet)
        self._stats["sent"] += 1

    async def _receive(self):
        try:
            while self.is_connected:
                incoming = await self.transport.received.get()
                if incoming is None:
                    break
                raw, rssi, snr = incoming
                self._stats["recv"] += 1
                self._radio.update(last_rssi=rssi, last_snr=snr)
                try:
                    await self._packet(raw, rssi, snr)
                except (ValueError, KeyError, UnicodeError):
                    self._stats["recv_errors"] += 1
                except (ConnectionError, TimeoutError):
                    # A rejected radio ACK must not undo an already received message.
                    self._stats["recv_errors"] += 1
                except OSError:
                    break  # Storage failure: reconnect from committed state, no action ACK.
        except asyncio.CancelledError:
            raise
        finally:
            await self.transport.close()

    async def _packet(self, raw, rssi, snr):
        packet = Packet.parse(raw)
        if packet.route == 2 and packet.path:
            return  # A source-routed packet has not yet reached its recipient.
        if packet.kind == 4:
            from .gateway_packets import read_advertisement
            contact = read_advertisement(packet)
            key = contact["public_key"]
            if key == self.state.public_key:
                return
            old = self.contacts.get(key)
            if old:
                # Advertisements must never rename or replace a saved favorite.
                if old.get("flags", 0) & 1 or not accepts_contact(contact, self.learning):
                    return
                if contact["last_advert"] <= old.get("last_advert", 0):
                    return
                contact.update({k: old[k] for k in ("flags", "out_path", "out_path_len", "out_path_hash_mode")})
            elif len(self.contacts) >= 350 or not accepts_contact(contact, self.learning):
                return
            elif self.learning[LEARN_FAVORITES]:
                contact["flags"] = contact.get("flags", 0) | 1
            self.contacts[key] = validate_contact(contact, self.state.signing_key)
            await self.state.save()
            await self._emit(EventType.NEW_CONTACT, {**contact, "newly_learned": old is None})
        elif packet.kind == 3 and len(packet.payload) in (4, 5, 6):
            await self._emit(EventType.ACK, {"code": packet.payload[:4].hex()})
        elif packet.kind in (2, 8):
            contact, secret, plain = open_private(self.state.signing_key, self.contacts, packet)
            if packet.kind == 8:
                length = path_size(plain[0])
                if len(plain) < length + 2:
                    raise ValueError("Truncated path return")
                contact.update(out_path_len=plain[0] & 63, out_path_hash_mode=plain[0] >> 6,
                               out_path=plain[1:1 + length].hex())
                if plain[1 + length] == 3 and len(plain) >= length + 6:
                    await self._emit(EventType.ACK, {"code": plain[2 + length:6 + length].hex()})
                await self.state.save()
                return
            payload = message_payload(plain, contact)
            payload.update(RSSI=rssi, SNR=snr)
            digest = hashlib.sha256(bytes.fromhex(contact["public_key"]) + struct.pack("<I", payload["sender_timestamp"])
                                    + payload["text"].encode("utf-8")).hexdigest()
            await self._queue(EventType.CONTACT_MSG_RECV, payload, digest)
            now = time.monotonic()
            if now - self._ack_at.get(digest, -100) >= 2:
                self._ack_at[digest] = now
                if len(self._ack_at) > 256:
                    del self._ack_at[next(iter(self._ack_at))]
                await self._send(acknowledgement(self.state.signing_key, contact, secret, packet, plain, payload["text"]))
        elif packet.kind == 5:
            matches = []
            for index, channel in enumerate(self.state.data["channels"]):
                key = bytes.fromhex(channel["secret"])
                if not channel["name"] or hashlib.sha256(key).digest()[:1] != packet.payload[:1]:
                    continue
                try:
                    plain = decrypt(key, packet.payload[1:])
                    if plain[4] >> 2 == 0:
                        text = plain[5:].split(b"\0", 1)[0].decode("utf-8")
                        if text and len(text.encode("utf-8")) <= 160:
                            matches.append({"channel_idx": index, "txt_type": 0, "text": text,
                                            "sender_timestamp": struct.unpack_from("<I", plain)[0], "RSSI": rssi, "SNR": snr})
                except (ValueError, UnicodeError):
                    continue
            if len(matches) == 1:
                await self._queue(EventType.CHANNEL_MSG_RECV, matches[0], hashlib.sha256(b"channel" + packet.payload).hexdigest())

    async def _queue(self, kind, payload, digest):
        seen = self.state.data["seen"]
        if digest in seen:
            return
        if len(self._messages) == self._messages.maxlen:
            raise ConnectionError("HA companion message queue full")
        seen.append(digest)
        del seen[:-256]
        await self.state.save()  # Persist replay suppression before exposing an action.
        self._messages.append(event(kind, payload))
        await self._emit(EventType.MESSAGES_WAITING)

    async def send(self, frame, expected, timeout=20):
        if frame != b"\x04":
            raise ValueError("Unsupported local companion command")
        return event(EventType.CONTACTS, deepcopy(self.contacts))

    async def get_msg(self):
        return self._messages.popleft() if self._messages else event(EventType.NO_MORE_MSGS)

    async def get_stats_radio(self):
        return event(EventType.STATS_RADIO, dict(self._radio))

    async def get_stats_packets(self):
        return event(EventType.STATS_PACKETS, {**self._stats,
            "recv_errors": self._stats["recv_errors"] + self.transport.dropped})

    async def _timestamp(self):
        value = max(int(time.time()), self.state.data["timestamp"] + 1)
        self.state.data["timestamp"] = value
        await self.state.save()
        return value

    async def send_msg(self, contact, text, *, timestamp=None, attempt=0):
        contact = self.contacts[public_key(contact["public_key"])]
        timestamp = await self._timestamp() if timestamp is None else timestamp
        packet, ack = private_message(self.state.signing_key, contact, text, timestamp, attempt)
        await self._send(packet)
        # DONE proves local radio completion only. Recipient ACKs arrive via RX.
        return event(EventType.MSG_SENT, {"expected_ack": ack, "suggested_timeout": 25000})

    async def send_advert(self):
        await self._send(advertisement(self.state.signing_key, self.name, await self._timestamp()))
        return event(EventType.OK)

    async def add_contact(self, contact):
        contact = validate_contact(contact, self.state.signing_key)
        key = contact["public_key"]
        if key == self.state.public_key or key in self.contacts or len(self.contacts) >= 350:
            raise ValueError("Cannot add this contact")
        self.contacts[key] = contact
        await self.state.save()
        return event(EventType.OK)

    async def remove_contact(self, key):
        del self.contacts[public_key(key)]
        await self.state.save()
        return event(EventType.OK)

    async def change_contact_flags(self, contact, flags):
        if type(flags) is not int or not 0 <= flags <= 255:
            raise ValueError("Invalid contact flags")
        self.contacts[public_key(contact["public_key"])]["flags"] = flags
        await self.state.save()
        return event(EventType.OK)

    async def reset_path(self, key):
        self.contacts[public_key(key)].update(out_path_len=-1, out_path="", out_path_hash_mode=0)
        await self.state.save()
        return event(EventType.OK)

    async def send_device_query(self):
        return event(EventType.DEVICE_INFO, {"max_channels": 16})

    async def get_channel(self, index):
        channel = self.state.data["channels"][index]
        return event(EventType.CHANNEL_INFO, {"channel_idx": index, "channel_name": channel["name"]})

    async def set_channel(self, index, name, secret):
        if type(index) is not int or not 0 <= index < 16 or len(name.encode("utf-8")) > 31 or "\0" in name:
            raise ValueError("Invalid channel")
        if secret is None and name.startswith("#"):
            secret = hashlib.sha256(name.encode("utf-8")).digest()[:16]
        if not isinstance(secret, bytes) or len(secret) != 16:
            raise ValueError("Invalid channel key")
        self.state.data["channels"][index] = {"name": name, "secret": secret.hex()}
        await self.state.save()
        return event(EventType.OK)
