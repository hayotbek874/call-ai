import hashlib
import hmac

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Request, Response

from src.core.config import settings
from src.core.logging import get_logger
from src.services.instagram_service import InstagramService

logger = get_logger(__name__)

router = APIRouter(prefix="/instagram", tags=["instagram"])

@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    await logger.info("instagram_verify_webhook", mode=mode)
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        await logger.info("instagram_webhook_verified")
        return Response(content=challenge, media_type="text/plain")
    await logger.warning("instagram_webhook_verification_failed", mode=mode)
    return Response(status_code=403)

@router.post("/webhook")
@inject
async def instagram_webhook(
    request: Request,
    instagram_svc: FromDishka[InstagramService],
) -> dict:
    signature = request.headers.get("X-Hub-Signature-256", "")
    body_bytes = await request.body()
    expected = (
        "sha256="
        + hmac.new(
            settings.INSTAGRAM_APP_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(signature, expected):
        await logger.warning("instagram_invalid_signature")
        return {"error": "invalid_signature"}
    body = await request.json()
    await logger.info("instagram_webhook_received", entries=len(body.get("entry", [])))
    await instagram_svc.handle_webhook(body)
    return {"status": "ok"}
