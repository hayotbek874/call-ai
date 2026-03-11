from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.logging import get_logger, mask_phone
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.utils.lang_detect import detect_language

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessageRequest(BaseModel):
    phone: str
    message: str
    language: str | None = None
    channel: str = "web"

class ChatVoiceRequest(BaseModel):
    phone: str
    language: str | None = None

async def _resolve_lang(text: str, lang: str | None) -> str:

    if lang and lang in ("ru", "uz"):
        return lang
    return await detect_language(text)

@router.post("/message")
@inject
async def chat_message(
    body: ChatMessageRequest,
    orchestrator: FromDishka[ChatOrchestrator],
) -> StreamingResponse:
    lang = await _resolve_lang(body.message, body.language)
    await logger.info(
        "chat_message_stream",
        phone=mask_phone(body.phone),
        language=lang,
        channel=body.channel,
        message_len=len(body.message),
    )

    async def event_stream():
        token_count = 0
        if lang == "both":

            yield "data:🇷🇺 Русский:\n\n"
            async for token in orchestrator.process_text(
                body.phone, body.message, "ru", body.channel
            ):
                token_count += 1
                yield f"data:{token}\n\n"
            yield "data:\n\n🇺🇿 O'zbekcha:\n\n"
            async for token in orchestrator.process_text(
                body.phone, body.message, "uz", body.channel
            ):
                token_count += 1
                yield f"data:{token}\n\n"
        else:
            async for token in orchestrator.process_text(
                body.phone, body.message, lang, body.channel
            ):
                token_count += 1
                yield f"data:{token}\n\n"
        yield "data:[DONE]\n\n"
        await logger.info(
            "chat_message_stream_done", phone=mask_phone(body.phone), tokens=token_count
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/message/sync")
@inject
async def chat_message_sync(
    body: ChatMessageRequest,
    orchestrator: FromDishka[ChatOrchestrator],
) -> dict:
    lang = await _resolve_lang(body.message, body.language)
    await logger.info(
        "chat_message_sync",
        phone=mask_phone(body.phone),
        language=lang,
        channel=body.channel,
        message_len=len(body.message),
    )

    if lang == "both":
        resp_ru = await orchestrator.get_text_response(body.phone, body.message, "ru", body.channel)
        resp_uz = await orchestrator.get_text_response(body.phone, body.message, "uz", body.channel)
        text = f"🇷🇺 {resp_ru}\n\n🇺🇿 {resp_uz}"
    else:
        text = await orchestrator.get_text_response(body.phone, body.message, lang, body.channel)

    await logger.info(
        "chat_message_sync_done", phone=mask_phone(body.phone), response_len=len(text)
    )
    return {"response": text, "detected_language": lang}
