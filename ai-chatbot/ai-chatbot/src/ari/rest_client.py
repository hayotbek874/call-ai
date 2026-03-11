from __future__ import annotations

import asyncio
from base64 import b64encode
from typing import Any

import httpx

from src.ari.config import ARIConfig
from src.ari.dto import BridgeDTO, ChannelDTO, PlaybackDTO
from src.core.logging import get_logger

logger = get_logger(__name__)

class ARIRestClientError(Exception):
    def __init__(self, status_code: int, detail: str, method: str = "", path: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.path = path
        super().__init__(f"ARI {method} {path} → {status_code}: {detail}")

class ARIAuthError(ARIRestClientError):
    pass

class ARINotFoundError(ARIRestClientError):
    pass

class ARIRestClient:
    def __init__(self, config: ARIConfig, timeout: float = 30.0, max_retries: int = 3):
        self._config = config
        self._base_url = config.rest_base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._auth_header = self._build_auth_header()
        self._client: httpx.AsyncClient | None = None

    def _build_auth_header(self) -> str:
        credentials = f"{self._config.username}:{self._config.password}"
        return f"Basic {b64encode(credentials.encode()).decode()}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                await logger.info(
                    "ari_rest_request",
                    method=method,
                    path=path,
                    attempt=attempt + 1,
                )

                response = await client.request(
                    method, path, json=json, params=params
                )

                if response.status_code == 401:
                    raise ARIAuthError(
                        status_code=401,
                        detail="Authentication failed",
                        method=method,
                        path=path,
                    )

                if response.status_code == 404:
                    raise ARINotFoundError(
                        status_code=404,
                        detail="Resource not found",
                        method=method,
                        path=path,
                    )

                if response.status_code >= 500:
                    await logger.warning(
                        "ari_rest_server_error",
                        method=method,
                        path=path,
                        status_code=response.status_code,
                        attempt=attempt + 1,
                    )
                    if attempt < self._max_retries - 1:
                        backoff = 0.5 * (2 ** attempt)
                        await asyncio.sleep(backoff)
                        continue
                    raise ARIRestClientError(
                        status_code=response.status_code,
                        detail=response.text,
                        method=method,
                        path=path,
                    )

                if response.status_code >= 400:
                    raise ARIRestClientError(
                        status_code=response.status_code,
                        detail=response.text,
                        method=method,
                        path=path,
                    )

                await logger.info(
                    "ari_rest_response",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                )

                if response.status_code == 204 or not response.content:
                    return None

                return response.json()

            except (ARIAuthError, ARINotFoundError, ARIRestClientError):
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                await logger.error(
                    "ari_rest_connection_error",
                    method=method,
                    path=path,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < self._max_retries - 1:
                    backoff = 0.5 * (2 ** attempt)
                    await asyncio.sleep(backoff)
                    continue

        raise ARIRestClientError(
            status_code=0,
            detail=f"Max retries exceeded: {last_exc}",
            method=method,
            path=path,
        )

    async def answer_channel(self, channel_id: str) -> None:
        await self._request("POST", f"/channels/{channel_id}/answer")

    async def continue_channel(
        self,
        channel_id: str,
        context: str,
        extension: str = "s",
        priority: int = 1,
    ) -> None:

        await self._request(
            "POST",
            f"/channels/{channel_id}/continue",
            params={
                "context": context,
                "extension": extension,
                "priority": priority,
            },
        )

    async def hangup_channel(self, channel_id: str, reason: str = "normal") -> None:
        await self._request("DELETE", f"/channels/{channel_id}", params={"reason": reason})

    async def get_channel(self, channel_id: str) -> ChannelDTO:
        data = await self._request("GET", f"/channels/{channel_id}")
        return ChannelDTO.from_ari(data)

    async def list_channels(self) -> list[ChannelDTO]:
        data = await self._request("GET", "/channels")
        return [ChannelDTO.from_ari(ch) for ch in (data or [])]

    async def play_media(
        self,
        channel_id: str,
        media: str,
        lang: str = "en",
        offset_ms: int = 0,
        skipms: int = 3000,
        playback_id: str | None = None,
    ) -> PlaybackDTO:
        params: dict[str, Any] = {
            "media": media,
            "lang": lang,
            "offsetms": offset_ms,
            "skipms": skipms,
        }
        if playback_id:
            params["playbackId"] = playback_id

        data = await self._request("POST", f"/channels/{channel_id}/play", params=params)
        return PlaybackDTO.from_ari(data)

    async def stop_playback(self, playback_id: str) -> None:
        await self._request("DELETE", f"/playbacks/{playback_id}")

    async def create_bridge(
        self,
        bridge_type: str = "mixing",
        name: str = "",
        bridge_id: str | None = None,
    ) -> BridgeDTO:
        params: dict[str, Any] = {"type": bridge_type}
        if name:
            params["name"] = name
        if bridge_id:
            params["bridgeId"] = bridge_id

        data = await self._request("POST", "/bridges", params=params)
        return BridgeDTO.from_ari(data)

    async def get_bridge(self, bridge_id: str) -> BridgeDTO:
        data = await self._request("GET", f"/bridges/{bridge_id}")
        return BridgeDTO.from_ari(data)

    async def delete_bridge(self, bridge_id: str) -> None:
        await self._request("DELETE", f"/bridges/{bridge_id}")

    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str) -> None:
        await self._request(
            "POST",
            f"/bridges/{bridge_id}/addChannel",
            params={"channel": channel_id},
        )

    async def remove_channel_from_bridge(self, bridge_id: str, channel_id: str) -> None:
        await self._request(
            "POST",
            f"/bridges/{bridge_id}/removeChannel",
            params={"channel": channel_id},
        )

    async def mute_channel(self, channel_id: str, direction: str = "both") -> None:
        await self._request("POST", f"/channels/{channel_id}/mute", params={"direction": direction})

    async def unmute_channel(self, channel_id: str, direction: str = "both") -> None:
        await self._request("DELETE", f"/channels/{channel_id}/mute", params={"direction": direction})

    async def set_channel_var(self, channel_id: str, variable: str, value: str) -> None:
        await self._request(
            "POST",
            f"/channels/{channel_id}/variable",
            params={"variable": variable, "value": value},
        )

    async def get_channel_var(self, channel_id: str, variable: str) -> str:
        data = await self._request(
            "GET",
            f"/channels/{channel_id}/variable",
            params={"variable": variable},
        )
        return data.get("value", "") if data else ""

    async def send_dtmf(self, channel_id: str, dtmf: str) -> None:
        await self._request("POST", f"/channels/{channel_id}/dtmf", params={"dtmf": dtmf})

    async def hold_channel(self, channel_id: str) -> None:
        await self._request("POST", f"/channels/{channel_id}/hold")

    async def unhold_channel(self, channel_id: str) -> None:
        await self._request("DELETE", f"/channels/{channel_id}/hold")

    async def start_moh(self, channel_id: str, moh_class: str = "default") -> None:
        await self._request("POST", f"/channels/{channel_id}/moh", params={"mohClass": moh_class})

    async def stop_moh(self, channel_id: str) -> None:
        await self._request("DELETE", f"/channels/{channel_id}/moh")

    async def record_channel(
        self,
        channel_id: str,
        name: str,
        fmt: str = "wav",
        max_duration: int = 0,
        max_silence: int = 0,
        beep: bool = False,
    ) -> dict:
        params: dict[str, Any] = {
            "name": name,
            "format": fmt,
            "beep": beep,
        }
        if max_duration:
            params["maxDurationSeconds"] = max_duration
        if max_silence:
            params["maxSilenceSeconds"] = max_silence

        data = await self._request("POST", f"/channels/{channel_id}/record", params=params)
        return data or {}

    async def stop_recording(self, recording_name: str) -> None:
        await self._request("POST", f"/recordings/live/{recording_name}/stop")

    async def health_check(self) -> bool:
        try:
            await self._request("GET", "/asterisk/info")
            return True
        except Exception:
            return False
