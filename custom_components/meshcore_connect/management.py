"""Local companion administration, serialized with message traffic."""
from copy import deepcopy
import time

from meshcore import EventType

from .client import checked
from .message import public_key


def device_name(value):
    if not isinstance(value, str) or not value.strip() or "\0" in value or len(value.encode("utf-8")) > 31:
        raise ValueError("Name must contain 1 to 31 UTF-8 bytes, without NUL")
    return value


class CompanionManagement:
    def require_client(self):
        if not self.client or not self.client.is_connected or self.stopping:
            raise ConnectionError("Companion is disconnected")

    def contact_snapshot(self):
        return self.contacts if self.contacts is not None else (self.client.contacts if self.client else {})

    def contact_list(self, favorites_only=False):
        return [{"public_key": key, "name": contact.get("adv_name", key[:12]),
                 "favorite": bool(contact.get("flags", 0) & 1), "type": contact.get("type", 1)}
                for key, contact in self.contact_snapshot().items()
                if not favorites_only or contact.get("flags", 0) & 1]

    async def _read_contacts(self):
        # Register the response listener before sending; get_contacts in meshcore
        # 2.3.0 can miss an immediate USB response.
        contacts = checked(await self.client.commands.send(
            b"\x04", [EventType.CONTACTS, EventType.ERROR], timeout=20), EventType.CONTACTS)
        self.contacts = deepcopy(contacts)
        self.contacts_at = time.monotonic()
        self.state["contacts"] = self.contact_list()

    async def refresh_contacts(self, favorites_only=False):
        async with self.lock:
            self.require_client()
            await self._read_contacts()
            self.async_set_updated_data(self.state.copy())
            return self.contact_list(favorites_only)

    async def add_contact(self, key, name, kind=1, favorite=False):
        key, name = public_key(key), device_name(name)
        if kind not in (1, 2, 3):
            raise ValueError("Invalid contact type")
        async with self.lock:
            self.require_client()
            await self._read_contacts()
            if key in self.contact_snapshot():
                raise ValueError("Contact already exists")
            contact = {"public_key": key, "adv_name": name, "type": kind,
                       "flags": int(favorite), "out_path": "", "out_path_len": -1,
                       "out_path_hash_mode": 0, "last_advert": 0, "adv_lat": 0, "adv_lon": 0}
            checked(await self.client.commands.add_contact(contact), EventType.OK)
            await self._read_contacts()
            self.async_set_updated_data(self.state.copy())

    async def remove_contact(self, key):
        key = public_key(key)
        async with self.lock:
            self.require_client()
            await self._read_contacts()
            if key not in self.contact_snapshot():
                raise ValueError("Contact no longer exists")
            checked(await self.client.commands.remove_contact(key), EventType.OK)
            self.contacts.pop(key, None)
            # The ACK confirms deletion. Do not let a later read failure prevent
            # the options flow from revoking this contact's action permission.
            self.state["contacts"] = self.contact_list()
            self.async_set_updated_data(self.state.copy())

    async def set_favorites(self, keys, known_keys=None):
        keys = {public_key(key) for key in keys}
        async with self.lock:
            self.require_client()
            await self._read_contacts()
            if not keys.issubset(self.contact_snapshot()):
                raise ValueError("Unknown contact")
            try:
                for key, contact in self.contact_snapshot().items():
                    if known_keys is not None and key not in known_keys:
                        continue  # A stale selection cannot clear newly learned favorites.
                    flags = (contact.get("flags", 0) & ~1) | int(key in keys)
                    if flags != contact.get("flags", 0):
                        # The library mutates its argument before receiving an ACK.
                        checked(await self.client.commands.change_contact_flags(
                            deepcopy(contact), flags), EventType.OK)
            finally:
                await self._read_contacts()
                self.async_set_updated_data(self.state.copy())

    async def set_favorite(self, key, enabled):
        key = public_key(key)
        async with self.lock:
            self.require_client()
            await self._read_contacts()
            contact = self.contact_snapshot().get(key)
            if contact is None:
                raise ValueError("Contact no longer exists")
            flags = (contact.get("flags", 0) & ~1) | int(enabled)
            checked(await self.client.commands.change_contact_flags(deepcopy(contact), flags), EventType.OK)
            await self._read_contacts()
            self.async_set_updated_data(self.state.copy())

    async def _read_channels(self):
        info = checked(await self.client.commands.send_device_query(), EventType.DEVICE_INFO)
        count = info.get("max_channels")
        if not isinstance(count, int) or not 1 <= count <= 256:
            raise ValueError("Device does not report its channel capacity")
        channels = []
        for index in range(count):
            channel = checked(await self.client.commands.get_channel(index), EventType.CHANNEL_INFO)
            if channel["channel_idx"] != index:
                raise ConnectionError("Unexpected channel response")
            # Never expose channel secrets in HA states or service responses.
            channels.append({"index": index, "name": channel["channel_name"]})
        self.channels = channels
        return channels

    async def refresh_channels(self):
        async with self.lock:
            self.require_client()
            return await self._read_channels()

    async def add_channel(self, index, name, secret=""):
        name = device_name(name)
        if name.startswith("#"):
            if secret:
                raise ValueError("Hashtag channels derive their key from the name")
            key = None
        else:
            key = bytes.fromhex(secret)
            if len(key) != 16:
                raise ValueError("Private channels require a 32-character hexadecimal key")
        async with self.lock:
            self.require_client()
            channels = await self._read_channels()
            if not isinstance(index, int) or not 0 <= index < len(channels) or channels[index]["name"]:
                raise ValueError("Channel slot is no longer empty")
            checked(await self.client.commands.set_channel(index, name, key), EventType.OK)
            await self._read_channels()

    async def remove_channel(self, index, expected_name):
        async with self.lock:
            self.require_client()
            channels = await self._read_channels()
            if (not isinstance(index, int) or not 0 <= index < len(channels)
                    or not expected_name or channels[index]["name"] != expected_name):
                raise ValueError("Channel changed; refresh the list before removing it")
            checked(await self.client.commands.set_channel(index, "", bytes(16)), EventType.OK)
            await self._read_channels()
