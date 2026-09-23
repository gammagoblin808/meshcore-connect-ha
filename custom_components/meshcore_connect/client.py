"""Connection lifecycle using the upstream MeshCore transport implementation."""
import asyncio
from meshcore import EventType, MeshCore
from meshcore.serial_cx import SerialConnection
from meshcore.tcp_cx import TCPConnection

from .const import CONF_MODE, MODE_GATEWAY_COMPANION


def checked(event, expected):
    if event is None or event.type != expected:
        raise ConnectionError("Companion did not accept the request")
    return event.payload


async def connect(data):
    mode = data.get(CONF_MODE)
    if mode == MODE_GATEWAY_COMPANION:
        # A gateway companion is deliberately TCP-only.  Refusing a malformed
        # entry here prevents a later migration or manual edit from falling
        # back to a local USB device.
        if data.get("transport") != "tcp" or not data.get("host"):
            raise ValueError("Gateway companion requires a TCP host")
        port = data.get("port", 5001)
        if not isinstance(port, int) or not 5001 <= port <= 5003:
            raise ValueError("Gateway companion requires TCP port 5001, 5002 or 5003")
        transport = TCPConnection(data["host"], port)
    elif data["transport"] == "serial":
        transport = SerialConnection(data["path"], 115200)
    else:
        transport = TCPConnection(data["host"], data["port"])
    client = MeshCore(transport, only_error=True, default_timeout=5, auto_reconnect=False)
    try:
        async with asyncio.timeout(20):
            checked(await client.connect(), EventType.SELF_INFO)
            checked(await client.commands.get_bat(), EventType.BATTERY)
        return client
    except BaseException:
        await client.disconnect()
        raise
