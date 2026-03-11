from __future__ import annotations

import asyncio
import json

from dishka import AsyncContainer
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.logging import get_logger
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService

logger = get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

SUPPORTED_LANGUAGES = {"ru", "uz"}

_UNSUPPORTED_LANG_MSG = (
    "Я поддерживаю только русский и узбекский языки. / "
    "Men faqat o'zbek va rus tillarini bilaman."
)

MIN_AUDIO_BYTES = 2000

@router.websocket("/call")
async def voice_call(ws: WebSocket) -> None:
    await ws.accept()
    await logger.info("voice_ws_connected")

    container: AsyncContainer = ws.app.state.dishka_container

    phone = "web-demo"
    language = "ru"

    try:
        async with container() as req:
            orchestrator = await req.get(ChatOrchestrator)
            stt = await req.get(STTService)
            tts = await req.get(TTSService)

            while True:
                msg = await ws.receive()

                if "text" in msg and msg["text"]:
                    try:
                        data = json.loads(msg["text"])
                    except json.JSONDecodeError:
                        continue

                    if data.get("type") == "config":
                        phone = data.get("phone", phone)
                        new_lang = data.get("language", language)
                        if new_lang not in SUPPORTED_LANGUAGES:
                            await ws.send_json({
                                "type": "error",
                                "detail": _UNSUPPORTED_LANG_MSG,
                            })
                            continue
                        language = new_lang
                        await ws.send_json({"type": "config_ack"})
                        continue

                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                        continue

                    continue

                if "bytes" in msg and msg["bytes"]:
                    await _process_audio_turn(
                        ws, orchestrator, stt, tts,
                        msg["bytes"], phone, language,
                    )
                    continue

    except WebSocketDisconnect:
        await logger.info("voice_ws_disconnected")
    except Exception as e:
        await logger.error("voice_ws_error", error=str(e))
        try:
            await ws.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass

async def _process_audio_turn(
    ws: WebSocket,
    orchestrator: ChatOrchestrator,
    stt: STTService,
    tts: TTSService,
    audio_bytes: bytes,
    phone: str,
    language: str,
) -> None:

    if language not in SUPPORTED_LANGUAGES:
        await ws.send_json({"type": "response", "text": _UNSUPPORTED_LANG_MSG})
        return

    if len(audio_bytes) < MIN_AUDIO_BYTES:
        await ws.send_json(
            {"type": "error", "detail": "Audio too short — hold the mic a bit longer"},
        )
        return

    stt_lang: str | None = language if language == "ru" else None
    try:
        text = await stt.transcribe(audio_bytes, stt_lang)
    except Exception as e:
        await ws.send_json({"type": "error", "detail": f"STT failed: {e}"})
        return

    if not text or not text.strip():
        await ws.send_json({"type": "transcript", "text": ""})
        return

    await ws.send_json({"type": "transcript", "text": text})

    try:
        response = await orchestrator.get_text_response(
            phone, text, language, "voice-web",
        )
    except Exception as e:
        await ws.send_json({"type": "error", "detail": f"AI failed: {e}"})
        return

    await ws.send_json({"type": "response", "text": response})

    try:
        stream = tts.synthesize_stream(response, language)

        if asyncio.iscoroutine(stream):
            stream = await stream
        async for chunk in stream:
            await ws.send_bytes(chunk)
        await ws.send_json({"type": "tts_done"})
    except Exception as e:
        await ws.send_json({"type": "error", "detail": f"TTS failed: {e}"})
