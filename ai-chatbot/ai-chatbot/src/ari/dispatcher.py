from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from src.ari.events import (
    ARIEvent,
    ChannelDestroyedEvent,
    PlaybackFinishedEvent,
    StasisEndEvent,
    StasisStartEvent,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[..., Coroutine[Any, Any, None]]

class ARIEventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def on_stasis_start(self, handler: EventHandler) -> EventHandler:
        self._handlers["StasisStart"].append(handler)
        return handler

    def on_stasis_end(self, handler: EventHandler) -> EventHandler:
        self._handlers["StasisEnd"].append(handler)
        return handler

    def on_channel_destroyed(self, handler: EventHandler) -> EventHandler:
        self._handlers["ChannelDestroyed"].append(handler)
        return handler

    def on_playback_finished(self, handler: EventHandler) -> EventHandler:
        self._handlers["PlaybackFinished"].append(handler)
        return handler

    def on(self, event_type: str, handler: EventHandler) -> EventHandler:
        self._handlers[event_type].append(handler)
        return handler

    def on_any(self, handler: EventHandler) -> EventHandler:
        self._global_handlers.append(handler)
        return handler

    def register(self, event_type: str) -> Callable[[EventHandler], EventHandler]:
        def decorator(func: EventHandler) -> EventHandler:
            self._handlers[event_type].append(func)
            return func
        return decorator

    async def dispatch(self, event: ARIEvent) -> None:
        event_type = event.type
        handlers = self._handlers.get(event_type, [])
        all_handlers = [*self._global_handlers, *handlers]

        if not all_handlers:
            await logger.debug("ari_event_no_handler", event_type=event_type)
            return

        await logger.debug(
            "ari_event_dispatching",
            event_type=event_type,
            handler_count=len(all_handlers),
        )

        tasks = [
            asyncio.create_task(self._safe_call(handler, event))
            for handler in all_handlers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call(self, handler: EventHandler, event: ARIEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            await logger.error(
                "ari_event_handler_error",
                handler=handler.__qualname__,
                event_type=event.type,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    def clear(self) -> None:
        self._handlers.clear()
        self._global_handlers.clear()
