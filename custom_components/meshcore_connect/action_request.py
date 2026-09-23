"""Request lifecycle shared by owned actions and passive automation observation."""
from dataclasses import dataclass, field
from enum import Enum


class RequestState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "OK"
    ERR = "ERR"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "expired"


@dataclass
class ActionRequest:
    public_key: str
    text: str
    sender_timestamp: int
    created: float
    context_id: str | None
    auto_reply: bool
    state: RequestState = field(default=RequestState.PENDING, init=False)

    def claim(self, *, now: float, ttl: float) -> bool:
        """Reserve execution synchronously, before the caller awaits anything."""
        self.expire(now=now, ttl=ttl)
        if self.state is not RequestState.PENDING:
            return False
        self.state = RequestState.RUNNING
        return True

    def complete(self, status: RequestState, *, expected: RequestState) -> bool:
        """Only the current owner may publish one terminal result."""
        if status not in (RequestState.OK, RequestState.ERR, RequestState.UNKNOWN):
            raise ValueError("A completion needs a result state")
        if expected not in (RequestState.PENDING, RequestState.RUNNING):
            raise ValueError("A completion needs an active owner")
        if self.state is not expected:
            return False
        self.state = status
        return True

    def expire(self, *, now: float, ttl: float) -> bool:
        """Expire an unclaimed request, never an execution already in flight."""
        if self.state is not RequestState.PENDING or now - self.created < ttl:
            return False
        self.state = RequestState.EXPIRED
        return True

    def disable_reply(self) -> None:
        """Suppress this request permanently, even if global replies return."""
        self.auto_reply = False
