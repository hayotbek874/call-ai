import asyncio
import time
from dataclasses import dataclass, field

from src.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class CallSession:

    uuid: str
    phone: str = ""
    language: str = "ru"
    start_time: float = field(default_factory=time.monotonic)
    is_active: bool = True
    call_db_id: int | None = None

    @property
    def duration(self) -> float:

        return time.monotonic() - self.start_time

class CallSessionManager:

    def __init__(self, max_concurrent: int = 20):
        self._sessions: dict[str, CallSession] = {}
        self._max = max_concurrent
        self._lock = asyncio.Lock()

    @property
    def count(self) -> int:
        return len(self._sessions)

    def can_accept(self) -> bool:
        return len(self._sessions) < self._max

    def get(self, uuid: str) -> CallSession | None:
        return self._sessions.get(uuid)

    def all_sessions(self) -> list[CallSession]:
        return list(self._sessions.values())

    async def register(self, uuid: str, phone: str = "") -> CallSession | None:

        async with self._lock:
            if not self.can_accept():
                await logger.warning(
                    "call_rejected_capacity",
                    current=len(self._sessions),
                    max=self._max,
                )
                return None
            session = CallSession(uuid=uuid, phone=phone)
            self._sessions[uuid] = session
            await logger.info(
                "call_registered",
                uuid=uuid,
                phone=phone,
                active_calls=len(self._sessions),
            )
            return session

    async def unregister(self, uuid: str) -> CallSession | None:

        async with self._lock:
            session = self._sessions.pop(uuid, None)
            if session:
                session.is_active = False
                await logger.info(
                    "call_unregistered",
                    uuid=uuid,
                    duration=f"{session.duration:.1f}s",
                    active_calls=len(self._sessions),
                )
            return session
