from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.ari.rest_client import ARIRestClientError, ARINotFoundError
from src.ari.service import ARIService
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ari", tags=["ari"])

class AnswerRequest(BaseModel):
    channel_id: str

class HangupRequest(BaseModel):
    channel_id: str
    reason: str = "normal"

class PlayMediaRequest(BaseModel):
    channel_id: str
    media: str
    lang: str = "en"

class CreateBridgeRequest(BaseModel):
    bridge_type: str = "mixing"
    name: str = ""

class AddToBridgeRequest(BaseModel):
    bridge_id: str
    channel_id: str

class BridgeChannelsRequest(BaseModel):
    channel_ids: list[str]
    bridge_type: str = "mixing"

def _get_ari_service(request: Request) -> ARIService:
    svc = getattr(request.app.state, "ari_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="ARI service not available")
    return svc

@router.get("/status")
async def ari_status(request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    status = await svc.status()
    return asdict(status)

@router.get("/sessions")
async def list_sessions(request: Request) -> list[dict[str, Any]]:
    svc = _get_ari_service(request)
    sessions = svc.sessions.get_all()
    return [
        {
            "channel_id": s.channel_id,
            "caller_number": s.caller_number,
            "app_name": s.app_name,
            "bridge_id": s.bridge_id,
            "playback_id": s.playback_id,
            "language": s.language,
            "duration": round(s.duration, 1),
            "is_active": s.is_active,
        }
        for s in sessions
    ]

@router.get("/sessions/{channel_id}")
async def get_session(channel_id: str, request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    session = svc.sessions.get(channel_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "channel_id": session.channel_id,
        "caller_number": session.caller_number,
        "app_name": session.app_name,
        "bridge_id": session.bridge_id,
        "playback_id": session.playback_id,
        "language": session.language,
        "duration": round(session.duration, 1),
        "is_active": session.is_active,
        "metadata": session.metadata,
    }

@router.get("/channels")
async def list_channels(request: Request) -> list[dict[str, Any]]:
    svc = _get_ari_service(request)
    try:
        channels = await svc.rest.list_channels()
        return [
            {
                "id": ch.id,
                "name": ch.name,
                "state": ch.state,
                "caller_number": ch.caller_number,
                "caller_name": ch.caller_name,
            }
            for ch in channels
        ]
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str, request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    try:
        ch = await svc.rest.get_channel(channel_id)
        return {
            "id": ch.id,
            "name": ch.name,
            "state": ch.state,
            "caller_number": ch.caller_number,
            "caller_name": ch.caller_name,
            "connected_number": ch.connected_number,
            "connected_name": ch.connected_name,
            "language": ch.language,
        }
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/channels/answer")
async def answer_channel(body: AnswerRequest, request: Request) -> dict[str, str]:
    svc = _get_ari_service(request)
    try:
        await svc.rest.answer_channel(body.channel_id)
        return {"status": "answered", "channel_id": body.channel_id}
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/channels/hangup")
async def hangup_channel(body: HangupRequest, request: Request) -> dict[str, str]:
    svc = _get_ari_service(request)
    try:
        await svc.hangup_with_cleanup(body.channel_id)
        return {"status": "hungup", "channel_id": body.channel_id}
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/channels/play")
async def play_media(body: PlayMediaRequest, request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    try:
        playback = await svc.rest.play_media(body.channel_id, body.media, lang=body.lang)
        await svc.sessions.update_playback(body.channel_id, playback.id)
        return {
            "playback_id": playback.id,
            "media_uri": playback.media_uri,
            "state": playback.state,
        }
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/bridges")
async def create_bridge(body: CreateBridgeRequest, request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    try:
        bridge = await svc.rest.create_bridge(bridge_type=body.bridge_type, name=body.name)
        return {
            "id": bridge.id,
            "bridge_type": bridge.bridge_type,
            "channels": bridge.channels,
            "name": bridge.name,
        }
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/bridges/add-channel")
async def add_channel_to_bridge(body: AddToBridgeRequest, request: Request) -> dict[str, str]:
    svc = _get_ari_service(request)
    try:
        await svc.rest.add_channel_to_bridge(body.bridge_id, body.channel_id)
        await svc.sessions.update_bridge(body.channel_id, body.bridge_id)
        return {"status": "added", "bridge_id": body.bridge_id, "channel_id": body.channel_id}
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Bridge or channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/bridges/remove-channel")
async def remove_channel_from_bridge(body: AddToBridgeRequest, request: Request) -> dict[str, str]:
    svc = _get_ari_service(request)
    try:
        await svc.rest.remove_channel_from_bridge(body.bridge_id, body.channel_id)
        await svc.sessions.update_bridge(body.channel_id, None)
        return {"status": "removed", "bridge_id": body.bridge_id, "channel_id": body.channel_id}
    except ARINotFoundError:
        raise HTTPException(status_code=404, detail="Bridge or channel not found")
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.post("/bridges/bridge-channels")
async def bridge_channels(body: BridgeChannelsRequest, request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    try:
        bridge = await svc.bridge_channels(body.channel_ids, bridge_type=body.bridge_type)
        return {
            "id": bridge.id,
            "bridge_type": bridge.bridge_type,
            "channels": bridge.channels,
        }
    except ARIRestClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)

@router.get("/health")
async def ari_health(request: Request) -> dict[str, Any]:
    svc = _get_ari_service(request)
    asterisk_ok = await svc.rest.health_check()
    status = await svc.status()
    return {
        "asterisk_reachable": asterisk_ok,
        "ws_connected": status.ws_connected,
        "active_sessions": status.active_sessions,
    }
