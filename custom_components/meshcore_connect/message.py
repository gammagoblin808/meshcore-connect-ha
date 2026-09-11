"""Contact validation without trusting mesh payloads as HA commands."""
import re


def public_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("A complete 64-character public key is required")
    return value.lower()


def allowed_keys(value):
    return sorted({public_key(part) for part in re.split(r"[\s,]+", value.strip()) if part})


def trusted_message(payload, contacts, allowed):
    prefix = payload.get("pubkey_prefix", "")
    text = payload.get("text")
    if not isinstance(prefix, str) or not re.fullmatch(r"[0-9a-fA-F]{12}", prefix):
        return None
    if not isinstance(text, str) or len(text.encode("utf-8")) > 256 or "\0" in text:
        return None
    # Only plain messages, not remote CLI replies or room messages.
    if payload.get("txt_type") != 0:
        return None
    matches = [key.lower() for key in contacts if key.lower().startswith(prefix.lower())]
    if len(matches) != 1 or matches[0] not in allowed:
        return None
    return {"public_key": matches[0], "text": text,
            "sender_timestamp": payload.get("sender_timestamp"),
            "sos": text == "SOS!" or text.startswith("SOS! GPS: ")}
