from __future__ import annotations

import asyncio
from typing import Any

from src.ari.dto import CallSessionDTO
from src.core.logging import get_logger

logger = get_logger(__name__)

class ARISessionManager:
    def __init__(self, max_concurrent: int = 100):
        self._sessions: dict[str, CallSessionDTO] = {}
        self._max = max_concurrent
        self._lock = asyncio.Lock()

    @property
    def count(self) -> int:
        return len(self._sessions)

    @property
    def max_concurrent(self) -> int:
        return self._max

    def can_accept(self) -> bool:
        return len(self._sessions) < self._max

    def get(self, channel_id: str) -> CallSessionDTO | None:
        return self._sessions.get(channel_id)

    def get_all(self) -> list[CallSessionDTO]:
        return list(self._sessions.values())

    def get_by_bridge(self, bridge_id: str) -> list[CallSessionDTO]:
        return [s for s in self._sessions.values() if s.bridge_id == bridge_id]

    async def create(
        self,
        channel_id: str,
        caller_number: str,
        app_name: str,
        language: str = "en",
    ) -> CallSessionDTO | None:
        async with self._lock:
            if not self.can_accept():
                await logger.warning(
                    "ari_session_rejected",
                    channel_id=channel_id,
                    current=len(self._sessions),
                    max=self._max,
                )
                return None

            if channel_id in self._sessions:
                await logger.warning(
                    "ari_session_duplicate",
                    channel_id=channel_id,
                )
                return self._sessions[channel_id]

            session = CallSessionDTO(
                channel_id=channel_id,
                caller_number=caller_number,
                app_name=app_name,
                language=language,
            )
            self._sessions[channel_id] = session

            await logger.info(
                "ari_session_created",
                channel_id=channel_id,
                caller_number=caller_number,
                active_sessions=len(self._sessions),
            )
            return session

    async def remove(self, channel_id: str) -> CallSessionDTO | None:
        async with self._lock:
            session = self._sessions.pop(channel_id, None)
            if session:
                session.is_active = False
                await logger.info(
                    "ari_session_removed",
                    channel_id=channel_id,
                    duration=f"{session.duration:.1f}s",
                    active_sessions=len(self._sessions),
                )
            return session

    async def update_bridge(self, channel_id: str, bridge_id: str | None) -> None:
        session = self._sessions.get(channel_id)
        if session:
            session.bridge_id = bridge_id

    async def update_playback(self, channel_id: str, playback_id: str | None) -> None:
        session = self._sessions.get(channel_id)
        if session:
            session.playback_id = playback_id

    async def set_metadata(self, channel_id: str, key: str, value: Any) -> None:
        session = self._sessions.get(channel_id)
        if session:
            session.metadata[key] = value

    async def clear_all(self) -> int:
        async with self._lock:
            count = len(self._sessions)
            for session in self._sessions.values():
                session.is_active = False
            self._sessions.clear()
            await logger.info("ari_sessions_cleared", count=count)
            return count
