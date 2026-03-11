from src.clients.base import ABCClient
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class InstagramClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._password}",
            "Content-Type": "application/json",
        }

    async def send_message(self, recipient_id: str, text: str) -> None:
        await logger.info("instagram_send_message", recipient_id=recipient_id, text_len=len(text))
        resp = await self.post(
            f"/{settings.INSTAGRAM_API_VERSION}/me/messages",
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
            },
        )
        if not resp.ok:
            await logger.error(
                "instagram_send_failed",
                status_code=resp.status_code,
                response=resp.data,
                recipient_id=recipient_id,
            )
