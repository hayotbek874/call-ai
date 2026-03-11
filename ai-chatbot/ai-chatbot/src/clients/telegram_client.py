from src.clients.base import ABCClient
from src.core.logging import get_logger

logger = get_logger(__name__)

class TelegramClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def send_message(self, chat_id: int | str, text: str) -> None:
        await logger.info("telegram_send_message", chat_id=chat_id, text_len=len(text))
        token = await self._get_token()
        await self.post(f"/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text})

    async def answer_callback(self, callback_query_id: str) -> None:
        await logger.info("telegram_answer_callback")
        token = await self._get_token()
        await self.post(
            f"/bot{token}/answerCallbackQuery", json={"callback_query_id": callback_query_id}
        )
