import asyncio
import json
from collections.abc import AsyncIterator

import websockets
from pydantic import BaseModel

from src.clients.base import ABCClient
from src.core.logging import get_logger, mask_phone

logger = get_logger(__name__)

class ChannelDTO(BaseModel):
    id: str
    caller_phone: str
    state: str

class AsteriskEventDTO(BaseModel):
    type: str
    channel_id: str | None = None
    phone: str | None = None
    data: dict = {}

class PlaybackDTO(BaseModel):
    id: str
    state: str

class RecordingDTO(BaseModel):
    name: str
    state: str
    format: str

class AsteriskClient(ABCClient):
    async def authenticate(self) -> str:
        import base64

        return base64.b64encode(f"{self._login}:{self._password}".encode()).decode()

    async def _build_headers(self) -> dict:
        token = await self._get_token()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    async def get_channel(self, channel_id: str) -> ChannelDTO:
        r = await self.get(f"/ari/channels/{channel_id}")
        return ChannelDTO(
            id=r.data["id"],
            caller_phone=r.data["caller"]["number"],
            state=r.data["state"],
        )

    async def answer(self, channel_id: str) -> None:
        await self.post(f"/ari/channels/{channel_id}/answer")

    async def hangup(self, channel_id: str) -> None:
        await self.delete(f"/ari/channels/{channel_id}")

    async def play(self, channel_id: str, media_url: str) -> PlaybackDTO:
        r = await self.post(
            f"/ari/channels/{channel_id}/play", json={"media": f"sound:{media_url}"}
        )
        return PlaybackDTO(**r.data)

    async def stop_playback(self, playback_id: str) -> None:
        await self.delete(f"/ari/playbacks/{playback_id}")

    async def record(self, channel_id: str, name: str) -> RecordingDTO:
        r = await self.post(
            f"/ari/channels/{channel_id}/record",
            json={"name": name, "format": "wav", "beep": False},
        )
        return RecordingDTO(**r.data)

    async def stop_record(self, name: str) -> None:
        await self.post(f"/ari/recordings/live/{name}/stop")

    async def stream_events(self, app: str) -> AsyncIterator[AsteriskEventDTO]:
        ws_url = (
            f"ws://{self._base_url.replace('http://', '').replace('https://', '')}"
            f"/ari/events?api_key={self._login}:{self._password}&app={app}"
        )
        backoff = 1
        while True:
            try:
                await logger.info("asterisk_ws_connecting", app=app)
                async with websockets.connect(ws_url) as ws:
                    backoff = 1
                    await logger.info("asterisk_ws_connected", app=app)
                    async for raw in ws:
                        event = json.loads(raw)
                        phone = None
                        if "channel" in event:
                            phone = event["channel"].get("caller", {}).get("number")
                        event_type = event.get("type", "")
                        await logger.debug(
                            "asterisk_event",
                            event_type=event_type,
                            phone=mask_phone(phone) if phone else None,
                        )
                        yield AsteriskEventDTO(
                            type=event_type,
                            channel_id=event.get("channel", {}).get("id"),
                            phone=phone,
                            data=event,
                        )
            except Exception as e:
                await logger.error("asterisk_ws_error", error=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
