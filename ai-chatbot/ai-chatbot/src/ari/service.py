from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.ari.config import ARIConfig
from src.ari.dispatcher import ARIEventDispatcher
from src.ari.dto import BridgeDTO, CallSessionDTO, PlaybackDTO
from src.ari.events import (
    ARIEvent,
    ChannelDestroyedEvent,
    PlaybackFinishedEvent,
    StasisEndEvent,
    StasisStartEvent,
)
from src.ari.rest_client import ARIRestClient
from src.ari.session_manager import ARISessionManager
from src.ari.ws_client import ARIWebSocketClient
from src.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ARIServiceStatus:
    ws_connected: bool
    active_sessions: int
    max_sessions: int
    reconnect_count: int

class ARIService:
    def __init__(
        self,
        config: ARIConfig,
        rest_client: ARIRestClient,
        session_manager: ARISessionManager,
        dispatcher: ARIEventDispatcher,
    ):
        self._config = config
        self._rest = rest_client
        self._sessions = session_manager
        self._dispatcher = dispatcher
        self._ws_client: ARIWebSocketClient | None = None
        self._register_default_handlers()

    @property
    def rest(self) -> ARIRestClient:
        return self._rest

    @property
    def sessions(self) -> ARISessionManager:
        return self._sessions

    @property
    def dispatcher(self) -> ARIEventDispatcher:
        return self._dispatcher

    def _register_default_handlers(self) -> None:
        self._dispatcher.on_stasis_start(self._handle_stasis_start)
        self._dispatcher.on_stasis_end(self._handle_stasis_end)
        self._dispatcher.on_channel_destroyed(self._handle_channel_destroyed)
        self._dispatcher.on_playback_finished(self._handle_playback_finished)

    async def start(self) -> None:
        self._ws_client = ARIWebSocketClient(
            config=self._config,
            on_event=self._on_event,
        )
        await self._ws_client.start()
        await logger.info(
            "ari_service_started",
            app=self._config.app_name,
            host=self._config.host,
            port=self._config.port,
        )

    async def stop(self) -> None:
        if self._ws_client:
            await self._ws_client.stop()
        await self._rest.close()
        await self._sessions.clear_all()
        await logger.info("ari_service_stopped")

    async def status(self) -> ARIServiceStatus:
        return ARIServiceStatus(
            ws_connected=self._ws_client.is_connected if self._ws_client else False,
            active_sessions=self._sessions.count,
            max_sessions=self._sessions.max_concurrent,
            reconnect_count=self._ws_client.reconnect_count if self._ws_client else 0,
        )

    async def _on_event(self, event: ARIEvent) -> None:
        await self._dispatcher.dispatch(event)

    async def _handle_stasis_start(self, event: StasisStartEvent) -> None:
        channel = event.channel
        caller_number = channel.caller.number if channel.caller else ""

        await logger.info(
            "ari_stasis_start",
            channel_id=channel.id,
            caller=caller_number,
            app=event.application,
        )

        session = await self._sessions.create(
            channel_id=channel.id,
            caller_number=caller_number,
            app_name=event.application,
            language=channel.language,
        )

        if session is None:
            await logger.warning(
                "ari_stasis_start_rejected",
                channel_id=channel.id,
                reason="capacity",
            )
            try:
                await self._rest.hangup_channel(channel.id, reason="congestion")
            except Exception as exc:
                await logger.error(
                    "ari_hangup_after_reject_failed",
                    channel_id=channel.id,
                    error=str(exc),
                )
            return

        try:
            await self._rest.answer_channel(channel.id)
        except Exception as exc:
            await logger.error(
                "ari_answer_failed",
                channel_id=channel.id,
                error=str(exc),
            )
            await self._sessions.remove(channel.id)
            return

        try:
            await self._rest.continue_channel(
                channel.id,
                context="voicebot-ai",
                extension="s",
                priority=1,
            )
            await logger.info(
                "ari_channel_continued",
                channel_id=channel.id,
                context="voicebot-ai",
            )
        except Exception as exc:
            await logger.error(
                "ari_continue_failed",
                channel_id=channel.id,
                error=str(exc),
            )
            try:
                await self._rest.hangup_channel(channel.id)
            except Exception:
                pass
            await self._sessions.remove(channel.id)

    async def _handle_stasis_end(self, event: StasisEndEvent) -> None:
        channel_id = event.channel.id

        await logger.info(
            "ari_stasis_end",
            channel_id=channel_id,
        )

        session = await self._sessions.remove(channel_id)
        if session and session.bridge_id:
            try:
                await self._rest.delete_bridge(session.bridge_id)
            except Exception as exc:
                await logger.error(
                    "ari_bridge_cleanup_failed",
                    bridge_id=session.bridge_id,
                    error=str(exc),
                )

    async def _handle_channel_destroyed(self, event: ChannelDestroyedEvent) -> None:
        channel_id = event.channel.id

        await logger.info(
            "ari_channel_destroyed",
            channel_id=channel_id,
            cause=event.cause,
            cause_txt=event.cause_txt,
        )

        await self._sessions.remove(channel_id)

    async def _handle_playback_finished(self, event: PlaybackFinishedEvent) -> None:
        playback = event.playback

        await logger.info(
            "ari_playback_finished",
            playback_id=playback.id,
            state=playback.state,
            target_uri=playback.target_uri,
        )

        channel_id = playback.target_uri.replace("channel:", "") if playback.target_uri.startswith("channel:") else None
        if channel_id:
            await self._sessions.update_playback(channel_id, None)

    async def answer_and_play(self, channel_id: str, media: str) -> PlaybackDTO:
        await self._rest.answer_channel(channel_id)
        playback = await self._rest.play_media(channel_id, media)
        await self._sessions.update_playback(channel_id, playback.id)
        return playback

    async def bridge_channels(self, channel_ids: list[str], bridge_type: str = "mixing") -> BridgeDTO:
        bridge = await self._rest.create_bridge(bridge_type=bridge_type)

        for ch_id in channel_ids:
            await self._rest.add_channel_to_bridge(bridge.id, ch_id)
            await self._sessions.update_bridge(ch_id, bridge.id)

        await logger.info(
            "ari_channels_bridged",
            bridge_id=bridge.id,
            channel_ids=channel_ids,
        )
        return bridge

    async def hangup_with_cleanup(self, channel_id: str) -> None:
        session = self._sessions.get(channel_id)
        if session:
            if session.playback_id:
                try:
                    await self._rest.stop_playback(session.playback_id)
                except Exception:
                    pass
            if session.bridge_id:
                try:
                    await self._rest.remove_channel_from_bridge(session.bridge_id, channel_id)
                except Exception:
                    pass

        try:
            await self._rest.hangup_channel(channel_id)
        except Exception as exc:
            await logger.error(
                "ari_hangup_failed",
                channel_id=channel_id,
                error=str(exc),
            )

        await self._sessions.remove(channel_id)
