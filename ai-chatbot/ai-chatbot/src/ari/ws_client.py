from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import websockets
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidURI,
)

from src.ari.config import ARIConfig
from src.ari.events import ARIEvent, parse_ari_event
from src.core.logging import get_logger

logger = get_logger(__name__)

EventCallback = Callable[[ARIEvent], Coroutine[Any, Any, None]]

_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 60.0
_BACKOFF_MULTIPLIER = 2.0

class ARIWebSocketClient:
    def __init__(
        self,
        config: ARIConfig,
        on_event: EventCallback,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
    ):
        self._config = config
        self._on_event = on_event
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._running = False
        self._task: asyncio.Task | None = None
        self._backoff = _INITIAL_BACKOFF
        self._connected = asyncio.Event()
        self._reconnect_count = 0
        self._ws: Any = None

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_forever(), name="ari-ws-client")
        await logger.info("ari_ws_client_started", ws_url=self._config.ws_url)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._connected.clear()
        await logger.info("ari_ws_client_stopped")

    async def wait_connected(self, timeout: float = 30.0) -> bool:
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _run_forever(self) -> None:
        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except InvalidURI as exc:
                await logger.critical("ari_ws_invalid_uri", error=str(exc))
                self._running = False
                break
            except InvalidHandshake as exc:
                await logger.error(
                    "ari_ws_auth_failed",
                    error=str(exc),
                    backoff=self._backoff,
                )
                await self._wait_backoff()
            except (ConnectionClosed, ConnectionClosedError) as exc:
                await logger.warning(
                    "ari_ws_connection_closed",
                    code=getattr(exc, "code", None),
                    reason=getattr(exc, "reason", ""),
                    backoff=self._backoff,
                )
                self._connected.clear()
                await self._wait_backoff()
            except OSError as exc:
                await logger.error(
                    "ari_ws_network_error",
                    error=str(exc),
                    backoff=self._backoff,
                )
                self._connected.clear()
                await self._wait_backoff()
            except Exception as exc:
                await logger.error(
                    "ari_ws_unexpected_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    backoff=self._backoff,
                )
                self._connected.clear()
                await self._wait_backoff()

    async def _connect_and_listen(self) -> None:
        ws_url = self._config.ws_url
        await logger.info("ari_ws_connecting", url=ws_url)

        async with ws_connect(
            ws_url,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._connected.set()
            self._backoff = _INITIAL_BACKOFF
            self._reconnect_count += 1

            await logger.info(
                "ari_ws_connected",
                app=self._config.app_name,
                reconnect_count=self._reconnect_count,
            )

            async for raw_message in ws:
                if not self._running:
                    break
                await self._process_message(raw_message)

        self._connected.clear()
        self._ws = None

    async def _process_message(self, raw: str | bytes) -> None:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            data = json.loads(raw)
            event = parse_ari_event(data)

            await logger.debug(
                "ari_ws_event_received",
                event_type=event.type,
                channel_id=event.channel.id if event.channel else None,
            )

            await self._on_event(event)

        except json.JSONDecodeError as exc:
            await logger.error("ari_ws_invalid_json", error=str(exc), raw=raw[:200])
        except Exception as exc:
            await logger.error(
                "ari_ws_event_processing_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _wait_backoff(self) -> None:
        await logger.info("ari_ws_reconnecting", backoff=self._backoff)
        await asyncio.sleep(self._backoff)
        self._backoff = min(self._backoff * _BACKOFF_MULTIPLIER, _MAX_BACKOFF)
