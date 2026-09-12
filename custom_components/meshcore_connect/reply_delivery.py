"""Bounded delivery of replies using MeshCore's message and ACK protocol."""
import asyncio
from collections import deque
import logging
import time

from meshcore import EventType

from .client import checked

LOGGER = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
ACK_MIN_SECONDS = 2
ACK_MAX_SECONDS = 30
ACK_DEFAULT_SECONDS = 8


def ack_timeout(payload):
    milliseconds = payload.get("suggested_timeout")
    if type(milliseconds) not in (int, float) or not 0 < milliseconds < float("inf"):
        return ACK_DEFAULT_SECONDS
    return min(ACK_MAX_SECONDS, max(ACK_MIN_SECONDS, milliseconds / 1000 * 1.2))


async def send_reply(hub, key, text, permitted, notify, *, confirm=True):
    """Return whether any attempt was queued, separately reporting radio ACKs."""
    if not permitted():
        return False
    # A progress notice must not hold up the action while waiting for the mesh.
    if not confirm:
        result = await hub.send_message(key, text, permitted=permitted)
        if result is None:
            return False
        notify("queued")
        return True

    hub.require_client()
    client = hub.client
    confirmed = asyncio.Event()
    expected = set()
    early_acks = deque(maxlen=32)

    def received(event):
        code = event.payload.get("code") if isinstance(event.payload, dict) else None
        if not isinstance(code, str) or len(code) != 8:
            return
        code = code.lower()
        early_acks.append(code)
        if code in expected:
            confirmed.set()

    # Listen before sending: an ACK can arrive alongside the local MSG_SENT reply.
    subscription = client.subscribe(EventType.ACK, received)
    timestamp = int(time.time())
    queued = False
    try:
        for attempt in range(MAX_ATTEMPTS):
            if not permitted() or hub.client is not client or not client.is_connected:
                if permitted() and queued:
                    notify("unconfirmed")
                return queued
            if confirmed.is_set():
                notify("delivered")
                return queued
            contact = hub.contact_snapshot().get(key, {})
            if attempt == MAX_ATTEMPTS - 1 and contact.get("out_path_len", -1) >= 0:
                async with hub.lock:
                    if not permitted():
                        return queued
                    hub.require_client()
                    if hub.client is not client:
                        notify("unconfirmed")
                        return queued
                    checked(await client.commands.reset_path(key), EventType.OK)
                    contact.update(out_path_len=-1, out_path="")
                notify("rerouted")
            if not permitted():
                return queued
            if confirmed.is_set():
                notify("delivered")
                return queued
            if attempt:
                notify("retrying")
            result = await hub.send_message(key, text, timestamp=timestamp,
                attempt=attempt, permitted=lambda: permitted() and hub.client is client)
            if result is None:
                if queued and permitted():
                    notify("unconfirmed")
                return queued
            if not queued:
                notify("queued")
            queued = True
            code = result.get("expected_ack")
            if not isinstance(code, bytes) or len(code) != 4:
                notify("unconfirmed")
                return queued
            code = code.hex()
            expected.add(code)
            if code in early_acks:
                confirmed.set()
            try:
                await asyncio.wait_for(confirmed.wait(), ack_timeout(result))
            except TimeoutError:
                continue
            if permitted():
                notify("delivered")
            return queued
        if permitted():
            notify("unconfirmed")
        return queued
    except Exception:
        if not queued:
            raise
        LOGGER.warning("Could not confirm delivery of Home Assistant action reply", exc_info=True)
        if permitted():
            notify("unconfirmed")
        return True
    finally:
        client.unsubscribe(subscription)
