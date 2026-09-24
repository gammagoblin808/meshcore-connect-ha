"""Authenticated RAK raw-radio service transport; never uses admin port 5000."""
import asyncio
import hashlib
import hmac
import re
import secrets
import struct


class GatewayAuthError(ConnectionError):
    """The service key was rejected, without including credentials in the error."""


class GatewayProtocolError(ConnectionError):
    """The endpoint does not speak the supported raw gateway protocol."""


class GatewayRejectedError(ConnectionError):
    """An explicit rejection is known, unlike an interrupted write."""

    def __init__(self, message="Gateway rejected the operation or radio transmission failed", *, code="rejected"):
        super().__init__(message)
        self.code = code if code in {"tx-disabled", "disabled", "airtime", "queue-full", "expired",
                                    "radio", "packet", "auth", "updating", "duplicate"} else "rejected"


def validate_endpoint(host, port, key):
    if not isinstance(host, str) or not host.strip() or any(c.isspace() for c in host):
        raise ValueError("Invalid gateway host")
    if type(port) is not int or port not in (5001, 5002, 5003):
        raise ValueError("Gateway services require port 5001, 5002 or 5003")
    if not isinstance(key, str) or not re.fullmatch(r"[!-~]{8,64}", key):
        raise ValueError("A service key of 8 to 64 printable ASCII characters is required")


class GatewayTransport:
    def __init__(self, host, port, key):
        validate_endpoint(host, port, key)
        self.host, self.port, self._key = host, port, key
        self.reader = self.writer = None
        self._reader_task = self._keepalive_task = None
        self._lock = asyncio.Lock()
        self._pending = None
        self._counter = 0
        self.is_connected = False
        self.received = asyncio.Queue(maxsize=128)
        self.dropped = 0

    async def _line(self):
        try:
            raw = await self.reader.readuntil(b"\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as error:
            raise GatewayProtocolError("Gateway closed the connection or sent an invalid record") from error
        if len(raw) > 701 or any(c < 32 or c > 126 for c in raw[:-1]):
            raise GatewayProtocolError("Invalid gateway record")
        return raw[:-1].decode("ascii")

    async def _write(self, line):
        self.writer.write(line.encode("ascii") + b"\n")
        await self.writer.drain()

    async def connect(self):
        try:
            async with asyncio.timeout(12):
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port, limit=701)
                if await self._line() != "RAK-GATEWAY 1":
                    raise GatewayProtocolError("This endpoint is not a RAK raw gateway")
                nonce = secrets.token_bytes(16)
                await self._write("AUTH1 " + nonce.hex())
                try:
                    challenge = await self._line()
                except GatewayProtocolError as error:
                    raise GatewayAuthError("Gateway service authentication failed") from error
                if not re.fullmatch(r"AUTH2 [0-9a-fA-F]{32}", challenge):
                    raise GatewayAuthError("Gateway service authentication failed")
                message = b"meshcore-mpg-v1" + struct.pack("<H", self.port) + nonce + bytes.fromhex(challenge[6:])
                proof = hmac.new(self._key.encode("ascii"), message, hashlib.sha256).hexdigest()
                await self._write("AUTH3 " + proof)
                try:
                    accepted = await self._line()
                except GatewayProtocolError as error:
                    raise GatewayAuthError("Gateway service authentication failed") from error
                if accepted != "OK AUTH":
                    raise GatewayAuthError("Gateway service authentication failed")
            self.is_connected = True
            self._reader_task = asyncio.create_task(self._receive())
            await self.ping()
            self._keepalive_task = asyncio.create_task(self._keepalive())
        except BaseException:
            await self.close()
            raise
        finally:
            self._key = ""

    async def _receive(self):
        try:
            while self.is_connected:
                line = await self._line()
                if line.startswith("RX "):
                    match = re.fullmatch(r"RX (-?\d{1,3}) (-?\d{1,3}) ([0-9a-fA-F]{2,510})", line)
                    if not match or len(match[3]) % 2:
                        raise GatewayProtocolError("Invalid gateway radio record")
                    rssi, snr = int(match[1]), int(match[2])
                    if not -200 <= rssi <= 100 or not -512 <= snr <= 512:
                        raise GatewayProtocolError("Invalid gateway radio metrics")
                    if self.received.full():
                        self.dropped += 1
                    else:
                        self.received.put_nowait((bytes.fromhex(match[3]), rssi, snr / 4))
                    continue
                if self._pending is None:
                    raise GatewayProtocolError("Unexpected gateway response")
                kind, number, future = self._pending
                if line == f"QUEUED {number}" and kind == "TX":
                    continue
                if line == f"{'DONE' if kind == 'TX' else 'PONG'} {number}":
                    if not future.done():
                        future.set_result(None)
                elif line.startswith("ERR ") or (kind == "TX" and line.startswith(f"FAIL {number} ")):
                    if not future.done():
                        future.set_exception(GatewayRejectedError(code=line.rsplit(" ", 1)[-1]))
                else:
                    raise GatewayProtocolError("Mismatched gateway response")
        except asyncio.CancelledError:
            raise
        except (OSError, ValueError, ConnectionError):
            pass
        finally:
            self.is_connected = False
            if self._pending and not self._pending[2].done():
                self._pending[2].set_exception(ConnectionError("Gateway disconnected; operation not replayed"))
            if self.writer:
                self.writer.close()
            # Wake the bounded radio consumer even when its queue is full.
            if self.received.full():
                self.received.get_nowait()
            self.received.put_nowait(None)

    async def _request(self, kind, payload="", timeout=8):
        async with self._lock:
            if not self.is_connected:
                raise ConnectionError("Gateway disconnected")
            self._counter = self._counter % 0xffffffff + 1
            future = asyncio.get_running_loop().create_future()
            self._pending = kind, self._counter, future
            try:
                async with asyncio.timeout(timeout):
                    await self._write(f"{kind} {self._counter}" + (" " + payload if payload else ""))
                    await future
            except GatewayRejectedError:
                raise
            except (OSError, TimeoutError, asyncio.CancelledError):
                # A timeout leaves the outcome unknown. Never resend a write.
                await self.close()
                raise
            finally:
                if future.done() and not future.cancelled():
                    future.exception()
                else:
                    future.cancel()
                self._pending = None

    async def ping(self):
        await self._request("PING")

    async def send_packet(self, packet):
        if not isinstance(packet, bytes) or not 1 <= len(packet) <= 255:
            raise ValueError("Invalid radio packet")
        await self._request("TX", packet.hex(), timeout=40)

    async def _keepalive(self):
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                await self.ping()
        except (OSError, TimeoutError, ConnectionError):
            await self.close()

    async def close(self):
        self.is_connected = False
        current = asyncio.current_task()
        for task in (self._reader_task, self._keepalive_task):
            if task and task is not current:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        if self.writer:
            self.writer.close()
            try:
                async with asyncio.timeout(2):
                    await self.writer.wait_closed()
            except (OSError, TimeoutError):
                pass
