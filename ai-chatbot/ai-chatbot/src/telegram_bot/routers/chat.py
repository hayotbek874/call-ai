from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from src.core.logging import get_logger
from src.telegram_bot.keyboards import main_menu_keyboard, phone_keyboard
from src.telegram_bot.states import Chat, Registration
from src.utils.lang_detect import detect_language

logger = get_logger(__name__)

router = Router(name="chat")

_BOTH_LANG_PREFIX = (
    "🇺🇿 Biz faqat o'zbek va rus tillarida xizmat ko'rsatamiz.\n"
    "🇷🇺 Мы обслуживаем только на узбекском и русском языках.\n\n"
)

_NEED_PHONE = "📱 Avval telefon raqamingizni ulashing.\n📱 Сначала поделитесь номером телефона."

_VOICE_PROCESSING = "🎙 Ovozingiz qayta ishlanmoqda... / Обрабатываю голосовое сообщение..."

@router.message(Chat.active, F.text.in_(["📦 Buyurtmalarim", "📦 Мои заказы"]))
async def on_my_orders(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]
    orchestrator = kwargs["orchestrator"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user or not user.phone:
        await state.set_state(Registration.waiting_phone)
        await message.answer(_NEED_PHONE, reply_markup=phone_keyboard())
        return

    lang = user.language or "ru"
    query = "Мои заказы" if lang == "ru" else "Mening buyurtmalarim"
    response = await orchestrator.get_text_response(user.phone, query, lang, "telegram")
    await message.answer(response, reply_markup=main_menu_keyboard(lang))

@router.message(Chat.active, F.text.in_(["💎 Katalog", "💎 Каталог"]))
async def on_catalog(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]
    orchestrator = kwargs["orchestrator"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user or not user.phone:
        await state.set_state(Registration.waiting_phone)
        await message.answer(_NEED_PHONE, reply_markup=phone_keyboard())
        return

    lang = user.language or "ru"
    query = "Покажи категории товаров" if lang == "ru" else "Tovar kategoriyalarini ko'rsat"
    response = await orchestrator.get_text_response(user.phone, query, lang, "telegram")
    await message.answer(response, reply_markup=main_menu_keyboard(lang))

@router.message(Chat.active, F.text.in_(["👤 Operator", "👤 Оператор"]))
async def on_operator(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    lang = (user.language if user else None) or "ru"

    if lang == "ru":
        text = "Я зафиксировал ваш вопрос, наш специалист перезвонит вам в течение часа и поможет с вашим вопросом."
    else:
        text = "Savolingizni qayd etdim, mutaxassisimiz bir soat ichida qo'ng'iroq qiladi va savolingizga yordam beradi."

    await message.answer(text, reply_markup=main_menu_keyboard(lang))

@router.message(Chat.active, F.voice)
async def on_voice_message(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]
    orchestrator = kwargs["orchestrator"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user or not user.phone:
        await state.set_state(Registration.waiting_phone)
        await message.answer(_NEED_PHONE, reply_markup=phone_keyboard())
        return

    processing_msg = await message.answer(_VOICE_PROCESSING)

    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        audio_data = file_bytes.read()

        stt_svc = kwargs.get("stt_svc")
        if not stt_svc:
            await processing_msg.edit_text(
                "⚠️ Ovozli xabarlar hozircha ishlamayapti. Matn yuboring.\n"
                "⚠️ Голосовые сообщения пока недоступны. Отправьте текст."
            )
            return

        lang = user.language or "ru"
        text = await stt_svc.transcribe(audio_data, lang)

        if not text or not text.strip():
            await processing_msg.edit_text(
                "🔇 Ovoz aniqlanmadi. Qaytadan urinib ko'ring.\n"
                "🔇 Не удалось распознать речь. Попробуйте ещё раз."
            )
            return

        await logger.info(
            "voice_transcribed",
            telegram_id=message.from_user.id,
            text_len=len(text),
            lang=lang,
        )

        response = await orchestrator.get_text_response(user.phone, text, lang, "telegram")

        reply = f"🎙 <i>{text}</i>\n\n{response}"
        await processing_msg.edit_text(reply, parse_mode="HTML")

        if user.language != lang:
            await user_repo.update_language_by_telegram_id(message.from_user.id, lang)

    except Exception as e:
        await logger.error("voice_processing_error", error=str(e))
        await processing_msg.edit_text(
            "⚠️ Xatolik yuz berdi. Matn sifatida yuboring.\n"
            "⚠️ Произошла ошибка. Отправьте текстом."
        )

@router.message(Chat.active, F.text)
async def on_chat_message(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]
    orchestrator = kwargs["orchestrator"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user or not user.phone:
        await state.set_state(Registration.waiting_phone)
        await message.answer(_NEED_PHONE, reply_markup=phone_keyboard())
        return

    text = message.text.strip()
    lang = await detect_language(text)
    await logger.info(
        "chat_lang_detected", telegram_id=message.from_user.id, lang=lang, text_len=len(text)
    )

    await message.bot.send_chat_action(message.chat.id, "typing")

    if lang == "both":
        resp_ru = await orchestrator.get_text_response(user.phone, text, "ru", "telegram")
        resp_uz = await orchestrator.get_text_response(user.phone, text, "uz", "telegram")
        response = f"{_BOTH_LANG_PREFIX}🇷🇺 {resp_ru}\n\n🇺🇿 {resp_uz}"
    else:
        response = await orchestrator.get_text_response(user.phone, text, lang, "telegram")
        if user.language != lang:
            await user_repo.update_language_by_telegram_id(message.from_user.id, lang)

    await message.answer(response, reply_markup=main_menu_keyboard(lang))
    await logger.info(
        "chat_response_sent", telegram_id=message.from_user.id, response_len=len(response)
    )

@router.message(F.voice)
async def on_voice_no_state(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user and user.phone:
        await state.set_state(Chat.active)
        await on_voice_message(message, state, **kwargs)
        return

    if not user:
        await user_repo.create_from_telegram(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )

    await state.set_state(Registration.waiting_phone)
    await message.answer(
        "🇺🇿 Davom etish uchun telefon raqamingizni ulashing.\n"
        "🇷🇺 Для продолжения поделитесь номером телефона.",
        reply_markup=phone_keyboard(),
    )

@router.message(F.text)
async def on_message_no_state(message: types.Message, state: FSMContext, **kwargs) -> None:
    user_repo = kwargs["user_repo"]

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user and user.phone:
        await state.set_state(Chat.active)
        await on_chat_message(message, state, **kwargs)
        return

    if not user:
        await user_repo.create_from_telegram(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )

    await state.set_state(Registration.waiting_phone)
    await message.answer(
        "🇺🇿 Davom etish uchun telefon raqamingizni ulashing.\n"
        "🇷🇺 Для продолжения поделитесь номером телефона.",
        reply_markup=phone_keyboard(),
    )
