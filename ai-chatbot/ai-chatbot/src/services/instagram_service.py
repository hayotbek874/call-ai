import re

from src.clients.instagram_client import InstagramClient
from src.core.logging import get_logger
from src.repositories.user_repository import UserRepository
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.utils.lang_detect import detect_language

logger = get_logger(__name__)

_BOTH_LANG_PREFIX = (
    "\U0001f1fa\U0001f1ff Biz faqat o'zbek va rus tillarida xizmat ko'rsatamiz.\n"
    "\U0001f1f7\U0001f1fa \u041c\u044b \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u0435\u043c \u0442\u043e\u043b\u044c\u043a\u043e \u043d\u0430 \u0443\u0437\u0431\u0435\u043a\u0441\u043a\u043e\u043c \u0438 \u0440\u0443\u0441\u0441\u043a\u043e\u043c \u044f\u0437\u044b\u043a\u0430\u0445.\n\n"
)

class InstagramService:
    def __init__(
        self, instagram: InstagramClient, orchestrator: ChatOrchestrator, user_repo: UserRepository
    ):
        self._instagram = instagram
        self._orchestrator = orchestrator
        self._user_repo = user_repo

    async def handle_webhook(self, body: dict) -> None:
        for entry in body.get("entry", []):
            for event in entry.get("messaging", []):
                await logger.info("instagram_event", sender=event.get("sender", {}).get("id"))
                await self._process(event)

    async def _process(self, event: dict) -> None:
        sender_id = event["sender"]["id"]
        text = event.get("message", {}).get("text", "")
        if not text:
            await logger.debug("instagram_no_text", sender_id=sender_id)
            return
        await logger.info("instagram_message", sender_id=sender_id, text_len=len(text))
        user = await self._user_repo.get_by_instagram_id(sender_id)
        if not user or not user.phone:
            if self._is_phone(text):
                phone = self._normalize(text)
                if user:
                    await self._user_repo.update_phone(user.id, phone)
                else:
                    await self._user_repo.create(
                        phone=phone, instagram_id=sender_id, channel="instagram"
                    )
                await self._instagram.send_message(
                    sender_id,
                    "\u2705 Raqam saqlandi! / \u2705 \u041d\u043e\u043c\u0435\u0440 \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d! \u041a\u0430\u043a\u043e\u0435 \u0443\u043a\u0440\u0430\u0448\u0435\u043d\u0438\u0435 \u0432\u0430\u0441 \u0437\u0430\u0438\u043d\u0442\u0435\u0440\u0435\u0441\u043e\u0432\u0430\u043b\u043e?",
                )
            else:
                await self._instagram.send_message(
                    sender_id,
                    "Telefon raqamingizni yuboring / \u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0432\u0430\u0448 \u043d\u043e\u043c\u0435\u0440 \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0430 (+998XXXXXXXXX)",
                )
            return
        lang = await detect_language(text)
        await logger.info("instagram_lang_detected", sender_id=sender_id, lang=lang)

        if lang == "both":
            resp_ru = await self._orchestrator.get_text_response(
                user.phone, text, "ru", "instagram"
            )
            resp_uz = await self._orchestrator.get_text_response(
                user.phone, text, "uz", "instagram"
            )
            response = f"{_BOTH_LANG_PREFIX}\U0001f1f7\U0001f1fa {resp_ru}\n\n\U0001f1fa\U0001f1ff {resp_uz}"
        else:
            response = await self._orchestrator.get_text_response(
                user.phone, text, lang, "instagram"
            )
            if user.language != lang:
                await self._user_repo.update_language(user.phone, lang)

        await self._instagram.send_message(sender_id, response)
        await logger.info(
            "instagram_response_sent", sender_id=sender_id, response_len=len(response)
        )

    def _is_phone(self, text: str) -> bool:
        return bool(re.match(r"^\+?[\d\s\-]{9,15}$", text.strip()))

    def _normalize(self, text: str) -> str:
        digits = re.sub(r"[^\d+]", "", text.strip())
        return digits if digits.startswith("+") else "+" + digits
