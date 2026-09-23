"""MeshCore v1 radio packets, matching src/Packet.cpp and BaseChatMesh.cpp.

Ed25519/X25519 use libsodium; AES uses cryptography. Never treat the gateway's
local DONE response as a recipient ACK. Unknown packet versions fail closed.
"""
from dataclasses import dataclass
import hashlib
import hmac
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from nacl.bindings import crypto_scalarmult, crypto_sign_ed25519_pk_to_curve25519
from nacl.exceptions import BadSignatureError, CryptoError
from nacl.signing import SigningKey, VerifyKey


def path_size(encoded):
    width, count = (encoded >> 6) + 1, encoded & 63
    if width > 3 or width * count > 64:
        raise ValueError("Invalid MeshCore path")
    return width * count


@dataclass(frozen=True)
class Packet:
    kind: int
    route: int
    path_code: int
    path: bytes
    payload: bytes

    @classmethod
    def parse(cls, raw):
        raw = bytes(raw)
        if not 3 <= len(raw) <= 255 or raw[0] >> 6 or raw[0] & 3 not in (1, 2):
            raise ValueError("Unsupported MeshCore radio packet")
        length = path_size(raw[1])
        payload = raw[2 + length:]
        if not 1 <= len(payload) <= 184:
            raise ValueError("Invalid MeshCore payload")
        return cls((raw[0] >> 2) & 15, raw[0] & 3, raw[1], raw[2:2 + length], payload)

    def encode(self):
        if len(self.path) != path_size(self.path_code) or not 1 <= len(self.payload) <= 184:
            raise ValueError("Invalid MeshCore packet size")
        return bytes([(self.kind << 2) | self.route, self.path_code]) + self.path + self.payload


def shared_secret(signing_key, peer):
    try:
        return crypto_scalarmult(bytes(signing_key.to_curve25519_private_key()),
                                 crypto_sign_ed25519_pk_to_curve25519(peer))
    except (ValueError, CryptoError) as error:
        raise ValueError("Invalid contact public key") from error


def encrypt(key, plain):
    padded = plain + bytes((-len(plain)) % 16)
    worker = Cipher(algorithms.AES(key[:16]), modes.ECB()).encryptor()
    encrypted = worker.update(padded) + worker.finalize()
    return hmac.digest(key, encrypted, "sha256")[:2] + encrypted


def decrypt(key, sealed):
    if len(sealed) < 18 or (len(sealed) - 2) % 16:
        raise ValueError("Invalid encrypted MeshCore payload")
    if not hmac.compare_digest(sealed[:2], hmac.digest(key, sealed[2:], "sha256")[:2]):
        raise ValueError("MeshCore MAC mismatch")
    worker = Cipher(algorithms.AES(key[:16]), modes.ECB()).decryptor()
    return worker.update(sealed[2:]) + worker.finalize()


def routed(kind, payload, contact=None):
    count = contact.get("out_path_len", -1) if contact else -1
    if count < 0:
        return Packet(kind, 1, 0, b"", payload).encode()
    mode = contact.get("out_path_hash_mode", 0)
    if not 0 <= mode <= 2 or not 0 <= count <= 63:
        raise ValueError("Invalid contact route")
    return Packet(kind, 2, count | (mode << 6), bytes.fromhex(contact["out_path"]), payload).encode()


def private_message(signing_key, contact, text, timestamp, attempt=0):
    if type(timestamp) is not int or not 0 <= timestamp <= 0xffffffff or type(attempt) is not int or not 0 <= attempt <= 3:
        raise ValueError("Invalid message timestamp or attempt")
    encoded = text.encode("utf-8")
    if not 1 <= len(encoded) <= 130 or "\0" in text:
        raise ValueError("Invalid message text")
    own, peer = bytes(signing_key.verify_key), bytes.fromhex(contact["public_key"])
    plain = struct.pack("<IB", timestamp, attempt) + encoded
    ack = hashlib.sha256(plain + own).digest()[:4]
    payload = peer[:1] + own[:1] + encrypt(shared_secret(signing_key, peer), plain)
    return routed(2, payload, contact), ack


def advertisement(signing_key, name, timestamp):
    encoded = name.encode("utf-8")
    if not 1 <= len(encoded) <= 31 or "\0" in name:
        raise ValueError("Invalid companion name")
    head = bytes(signing_key.verify_key) + struct.pack("<I", timestamp)
    app = b"\x81" + encoded
    return routed(4, head + signing_key.sign(head + app).signature + app)


def read_advertisement(packet):
    p = packet.payload
    if packet.kind != 4 or not 101 <= len(p) <= 132:
        raise ValueError("Invalid advertisement size")
    try:
        VerifyKey(p[:32]).verify(p[:36] + p[100:], p[36:100])
    except (ValueError, BadSignatureError) as error:
        raise ValueError("Invalid advertisement signature") from error
    flags = p[100]
    if flags & 15 not in (1, 2, 3, 4) or flags & 0x60:
        raise ValueError("Unsupported advertisement flags")
    offset, lat, lon = 101, 0, 0
    if flags & 0x10:
        if len(p) < offset + 8:
            raise ValueError("Truncated advertisement location")
        lat, lon = struct.unpack_from("<ii", p, offset)
        lat, lon, offset = lat / 1000000, lon / 1000000, offset + 8
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Invalid advertisement location")
    name = p[offset:].decode("utf-8") if flags & 0x80 else p[:6].hex()
    if "\0" in name or len(name.encode("utf-8")) > 31:
        raise ValueError("Invalid advertisement name")
    return {"public_key": p[:32].hex(), "adv_name": name, "type": flags & 15,
            "last_advert": struct.unpack_from("<I", p, 32)[0], "adv_lat": lat, "adv_lon": lon,
            "flags": 0, "out_path_len": -1, "out_path_hash_mode": 0, "out_path": ""}


def open_private(signing_key, contacts, packet):
    own = bytes(signing_key.verify_key)
    if len(packet.payload) < 20 or packet.payload[:1] != own[:1]:
        raise ValueError("Packet is not addressed to this companion")
    matches = []
    for key, contact in contacts.items():
        peer = bytes.fromhex(key)
        if peer[:1] != packet.payload[1:2]:
            continue
        try:
            secret = shared_secret(signing_key, peer)
            plain = decrypt(secret, packet.payload[2:])
            matches.append((contact, secret, plain))
        except ValueError:
            continue
    if len(matches) != 1:
        raise ValueError("Unknown or ambiguous private sender")
    return matches[0]


def message_payload(plain, contact):
    if len(plain) < 6 or plain[4] >> 2 != 0:
        raise ValueError("Unsupported private message type")
    text = plain[5:].split(b"\0", 1)[0].decode("utf-8")
    if not text or len(text.encode("utf-8")) > 130:
        raise ValueError("Invalid private message text")
    return {"pubkey_prefix": contact["public_key"][:12], "txt_type": 0,
            "sender_timestamp": struct.unpack_from("<I", plain)[0], "text": text}


def acknowledgement(signing_key, contact, secret, incoming, plain, text):
    peer = bytes.fromhex(contact["public_key"])
    ack = hashlib.sha256(plain[:5 + len(text.encode("utf-8"))] + peer).digest()[:4]
    if incoming.route == 1:
        data = bytes([incoming.path_code]) + incoming.path + b"\x03" + ack
        payload = peer[:1] + bytes(signing_key.verify_key)[:1] + encrypt(secret, data)
        return routed(8, payload)
    return routed(3, ack, contact)
