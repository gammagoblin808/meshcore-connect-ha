"""Private HA storage for the independent companion, never gateway flash."""
import asyncio
from copy import deepcopy

from homeassistant.helpers.storage import Store
from nacl.signing import SigningKey

from .const import DOMAIN
from .gateway_packets import path_size, shared_secret
from .message import public_key


def validate_contact(contact, signing_key):
    if not isinstance(contact, dict):
        raise ValueError("Invalid stored contact")
    key = public_key(contact["public_key"])
    shared_secret(signing_key, bytes.fromhex(key))
    name = contact["adv_name"]
    if not isinstance(name, str) or not name.strip() or "\0" in name or len(name.encode("utf-8")) > 31:
        raise ValueError("Invalid contact name")
    count, mode = contact.get("out_path_len", -1), contact.get("out_path_hash_mode", 0)
    if type(count) is not int or type(mode) is not int or not -1 <= count <= 63 or not 0 <= mode <= 2:
        raise ValueError("Invalid contact path")
    path = bytes.fromhex(contact.get("out_path", ""))
    if len(path) != (0 if count < 0 else path_size(count | mode << 6)):
        raise ValueError("Invalid contact path length")
    if (contact.get("type") not in (1, 2, 3, 4) or type(contact.get("flags", 0)) is not int
            or not 0 <= contact.get("flags", 0) <= 255):
        raise ValueError("Invalid contact attributes")
    return {**deepcopy(contact), "public_key": key}


class GatewayState:
    def __init__(self, data, save=None):
        if not isinstance(data, dict) or not isinstance(data.get("seed"), str):
            raise ValueError("Invalid companion storage")
        self.data = deepcopy(data)
        seed = bytes.fromhex(data["seed"])
        if len(seed) != 32:
            raise ValueError("Invalid companion identity")
        self.signing_key = SigningKey(seed)
        self.public_key = bytes(self.signing_key.verify_key).hex()
        contacts = self.data.setdefault("contacts", {})
        if not isinstance(contacts, dict) or len(contacts) > 350:
            raise ValueError("Companion contact capacity exceeded")
        for key, contact in list(contacts.items()):
            contacts[key] = validate_contact(contact, self.signing_key)
            if key != contacts[key]["public_key"]:
                raise ValueError("Stored contact identity mismatch")
        channels = self.data.setdefault("channels", [{"name": "", "secret": "00" * 16} for _ in range(16)])
        if not isinstance(channels, list) or len(channels) != 16:
            raise ValueError("Invalid channel store")
        for channel in channels:
            if (not isinstance(channel, dict) or not isinstance(channel.get("name"), str)
                    or not isinstance(channel.get("secret"), str) or "\0" in channel["name"]):
                raise ValueError("Invalid stored channel")
            if len(bytes.fromhex(channel["secret"])) != 16 or len(channel["name"].encode("utf-8")) > 31:
                raise ValueError("Invalid stored channel")
        self.data.setdefault("seen", [])
        self.data.setdefault("timestamp", 0)
        if (not isinstance(self.data["seen"], list) or len(self.data["seen"]) > 256
                or any(not isinstance(item, str) or len(item) != 64 for item in self.data["seen"])
                or type(self.data["timestamp"]) is not int or not 0 <= self.data["timestamp"] <= 0xffffffff):
            raise ValueError("Invalid companion replay or timestamp store")
        self._committed = deepcopy(self.data)
        self.failed = False
        self._save, self._lock = save, asyncio.Lock()

    @classmethod
    def create(cls):
        while True:
            key = SigningKey.generate()
            if bytes(key.verify_key)[0] not in (0, 255):
                return cls({"seed": bytes(key).hex()})

    async def save(self):
        async with self._lock:
            if self.failed:
                raise OSError("Companion storage failed; reload committed state")
            snapshot = deepcopy(self.data)
            try:
                if self._save:
                    await self._save(snapshot)
            except BaseException:
                self.data = deepcopy(self._committed)
                self.failed = True
                raise
            self._committed = snapshot

    def bind(self, hass):
        self._save = Store(hass, 1, f"{DOMAIN}.gateway.{self.public_key}", private=True).async_save

    @classmethod
    async def load(cls, hass, identity):
        identity = public_key(identity)
        store = Store(hass, 1, f"{DOMAIN}.gateway.{identity}", private=True)
        data = await store.async_load()
        if data is None:
            raise ValueError("HA companion identity storage is missing; restore the HA backup")
        state = cls(data, store.async_save)
        if state.public_key != identity:
            raise ValueError("HA companion identity does not match the configured entry")
        return state
