import re

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from src.core.logging import get_logger, mask_phone
from src.telegram_bot.keyboards import main_menu_keyboard, phone_keyboard
from src.telegram_bot.states import Chat, Registration

logger = get_logger(__name__)

router = Router(name="phone")

_PHONE_SAVED_MSG = (
    "✅ Raqam saqlandi! / ✅ Номер сохранён!\n\n"
    "🇺🇿 Endi savolingizni yozishingiz mumkin. Qaysi zargarlik buyumi sizni qiziqtiradi?\n"
    "🇷🇺 Теперь можете задавать вопросы. Какое украшение вас заинтересовало?"
)

_PLEASE_SHARE_PHONE = (
    "📱 Iltimos, pastdagi tugmani bosib raqamingizni ulashing.\n"
    "📱 Пожалуйста, нажмите кнопку ниже и поделитесь номером."
)

def _normalize(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw.strip())
    return digits if digits.startswith("+") else "+" + digits

@router.message(Registration.waiting_phone, F.contact)
async def on_contact_shared(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]
    phone = _normalize(message.contact.phone_number)

    await user_repo.set_phone_by_telegram_id(message.from_user.id, phone)
    await logger.info(
        "phone_registered_via_contact", telegram_id=message.from_user.id, phone=mask_phone(phone)
    )

    await state.set_state(Chat.active)
    await message.answer(_PHONE_SAVED_MSG, reply_markup=main_menu_keyboard())

@router.message(Registration.waiting_phone, F.text)
async def on_phone_text(message: types.Message, state: FSMContext, **kwargs) -> None:
    text = (message.text or "").strip()

    if re.match(r"^\+?998\d{9}$", re.sub(r"[\s\-]", "", text)):
        user_repo = kwargs["user_repo"]
        phone = _normalize(text)
        await user_repo.set_phone_by_telegram_id(message.from_user.id, phone)
        await logger.info(
            "phone_registered_via_text", telegram_id=message.from_user.id, phone=mask_phone(phone)
        )
        await state.set_state(Chat.active)
        await message.answer(_PHONE_SAVED_MSG, reply_markup=main_menu_keyboard())
    else:
        await logger.debug("phone_invalid_input", telegram_id=message.from_user.id)
        await message.answer(_PLEASE_SHARE_PHONE, reply_markup=phone_keyboard())
