from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from src.core.logging import get_logger
from src.telegram_bot.keyboards import main_menu_keyboard, phone_keyboard
from src.telegram_bot.states import Chat, Registration

logger = get_logger(__name__)

router = Router(name="start")

_WELCOME_MSG = (
    "🇺🇿 <b>Assalomu alaykum!</b> ZargarShop AI botiga xush kelibsiz! 💎\n"
    "Davom etish uchun telefon raqamingizni ulashing.\n\n"
    "🇷🇺 <b>Здравствуйте!</b> Добро пожаловать в ZargarShop AI бот! 💎\n"
    "Для продолжения поделитесь номером телефона."
)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        user = await user_repo.create_from_telegram(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )
        await logger.info("start_new_user", telegram_id=message.from_user.id, user_id=user.id)
    else:
        await logger.info("start_existing_user", telegram_id=message.from_user.id, user_id=user.id)

    if user.phone:
        lang = user.language or "ru"
        await state.set_state(Chat.active)
        await message.answer(
            "🇺🇿 Qaytganingiz bilan! Savolingizni yozing.\n🇷🇺 С возвращением! Напишите ваш вопрос.",
            reply_markup=main_menu_keyboard(lang),
        )
        return
    await state.set_state(Registration.waiting_phone)
    await message.answer(_WELCOME_MSG, reply_markup=phone_keyboard(), parse_mode="HTML")
