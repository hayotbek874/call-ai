import re

from src.clients.telegram_client import TelegramClient
from src.core.logging import get_logger
from src.repositories.user_repository import UserRepository
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.utils.lang_detect import detect_language

logger = get_logger(__name__)

_BOTH_LANG_PREFIX = (
    "🇺🇿 Biz faqat o'zbek va rus tillarida xizmat ko'rsatamiz.\n"
    "🇷🇺 Мы обслуживаем только на узбекском и русском языках.\n\n"
)

class TelegramBotService:
    def __init__(
        self, telegram: TelegramClient, orchestrator: ChatOrchestrator, user_repo: UserRepository
    ):
        self._telegram = telegram
        self._orchestrator = orchestrator
        self._user_repo = user_repo

    async def handle_webhook_update(self, update: dict) -> None:
        message = update.get("message")
        if not message:
            return
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        contact = message.get("contact")

        if contact:
            phone = self._normalize(contact.get("phone_number", ""))
            if phone:
                await self._user_repo.set_phone_by_telegram_id(chat_id, phone)
                await self._telegram.send_message(
                    chat_id,
                    "✅ Raqam saqlandi! / ✅ Номер сохранён!\n"
                    "Qaysi zargarlik buyumi sizni qiziqtiradi? / Какое украшение вас заинтересовало?",
                )
            return

        if not text:
            return

        user = await self._user_repo.get_by_telegram_id(chat_id)
        if not user or not user.phone:
            await self._telegram.send_message(
                chat_id,
                "📱 Telefon raqamingizni yuboring / Отправьте ваш номер телефона (+998XXXXXXXXX)",
            )
            return

        lang = await detect_language(text)
        await logger.info("tg_webhook_lang", chat_id=chat_id, lang=lang)

        if lang == "both":
            resp_ru = await self._orchestrator.get_text_response(user.phone, text, "ru", "telegram")
            resp_uz = await self._orchestrator.get_text_response(user.phone, text, "uz", "telegram")
            response = f"{_BOTH_LANG_PREFIX}🇷🇺 {resp_ru}\n\n🇺🇿 {resp_uz}"
        else:
            response = await self._orchestrator.get_text_response(
                user.phone, text, lang, "telegram"
            )
            if user.language != lang:
                await self._user_repo.update_language_by_telegram_id(chat_id, lang)

        await self._telegram.send_message(chat_id, response)

    @staticmethod
    def _normalize(raw: str) -> str:
        digits = re.sub(r"[^\d+]", "", raw.strip())
        return digits if digits.startswith("+") else "+" + digits
