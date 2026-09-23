"""Connection lifecycle using the upstream MeshCore transport implementation."""
import asyncio
from meshcore import EventType, MeshCore
from meshcore.serial_cx import SerialConnection
from meshcore.tcp_cx import TCPConnection

from .const import CONF_MODE, MODE_GATEWAY_COMPANION, MODE_STANDARD


def checked(event, expected):
    if event is None or event.type != expected:
        raise ConnectionError("Companion did not accept the request")
    return event.payload


async def connect(data, *, gateway_state=None):
    mode = data.get(CONF_MODE, MODE_STANDARD)
    if mode == MODE_GATEWAY_COMPANION:
        from .gateway_client import GatewayClient
        if data.get("transport") != "tcp" or gateway_state is None:
            raise ValueError("Gateway companion requires TCP and its stored HA identity")
        client = GatewayClient(data, gateway_state)
        try:
            await client.connect()
            return client
        except BaseException:
            await client.disconnect()
            raise
    if mode != MODE_STANDARD:
        raise ValueError("Unknown companion mode")
    transport = (SerialConnection(data["path"], 115200) if data["transport"] == "serial"
                 else TCPConnection(data["host"], data["port"]))
    client = MeshCore(transport, only_error=True, default_timeout=5, auto_reconnect=False)
    try:
        async with asyncio.timeout(20):
            checked(await client.connect(), EventType.SELF_INFO)
            checked(await client.commands.get_bat(), EventType.BATTERY)
        return client
    except BaseException:
        await client.disconnect()
        raise
