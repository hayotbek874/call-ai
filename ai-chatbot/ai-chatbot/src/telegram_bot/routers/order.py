import uuid
from datetime import date, datetime, timedelta

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from src.clients.crm_client import CRMClient
from src.core.logging import get_logger
from src.schemas.crm import (
    Address,
    OrderCreate,
    OrderDeliveryInput,
    OrderItemCreate,
    OrderItemOffer,
)
from src.services.ai.crm_service import CRMService
from src.telegram_bot.keyboards import (
    cancel_order_keyboard,
    confirm_keyboard,
    delivery_time_keyboard,
    location_keyboard,
    main_menu_keyboard,
    payment_keyboard,
    phone_keyboard,
    product_card_inline,
    product_input_keyboard,
    product_select_inline,
    quantity_keyboard,
)
from src.telegram_bot.states import Chat, Order, OrderStatus, Registration

logger = get_logger(__name__)

router = Router(name="order")

CANCEL_RU = ["❌ Отменить", "отмена", "отменить"]
CANCEL_UZ = ["❌ Bekor qilish", "bekor", "bekor qilish"]

REGION_MAP = {

    "🏙 Ташкент город": "Tashkent",
    "🏙 Ташкентская область": "Toshkent viloyati",
    "🏙 Самарканд": "Samarqand",
    "🏙 Бухара": "Buxoro",
    "🏙 Андижан": "Andijon",
    "🏙 Фергана": "Farg'ona",
    "🏙 Наманган": "Namangan",
    "🏙 Другой регион": "Other",

    "🏙 Toshkent shahri": "Tashkent",
    "🏙 Toshkent viloyati": "Toshkent viloyati",
    "🏙 Samarqand": "Samarqand",
    "🏙 Buxoro": "Buxoro",
    "🏙 Andijon": "Andijon",
    "🏙 Farg'ona": "Farg'ona",
    "🏙 Namangan": "Namangan",
    "🏙 Boshqa viloyat": "Other",
}

TASHKENT_REGIONS = ["Tashkent", "tashkent", "ташкент", "тошкент", "toshkent"]

MSGS = {
    "ru": {
        "order_start": (
            "🛒 <b>Оформление заказа</b>\n\n"
            "Как вас зовут? (Имя и фамилия)"
        ),
        "ask_product": (
            "📦 <b>Выбор товара</b>\n\n"
            "• <b>Все товары</b> — просмотр каталога\n"
            "• <b>Поиск</b> — найти по названию\n"
            "• <b>По коду</b> — ввести артикул товара"
        ),
        "enter_code": "🔢 Введите артикул товара:",
        "enter_search": "🔍 Введите название товара для поиска:",
        "browse_catalog": "📋 <b>Каталог товаров</b>\n\nВыберите товар для просмотра:",
        "product_found": (
            "✅ <b>Товар найден!</b>\n\n"
            "📦 {name}\n"
            "🏷 Артикул: {article}\n"
            "💰 Цена: {price:,.0f} сум\n"
            "📊 В наличии: {quantity} шт\n\n"
            "Добавить в заказ?"
        ),
        "product_detail": (
            "📦 <b>{name}</b>\n\n"
            "🏷 Артикул: {article}\n"
            "💰 Цена: {price:,.0f} сум\n"
            "📊 В наличии: {quantity} шт"
        ),
        "product_not_found": "❌ Товар с артикулом {article} не найден. Попробуйте другой.",
        "ask_quantity": "🔢 Укажите количество:",
        "ask_location": (
            "📍 <b>Выберите регион доставки</b>\n\n"
            "Нажмите на кнопку региона или отправьте геолокацию"
        ),
        "ask_address": (
            "🏠 <b>Адрес доставки</b>\n\n"
            "Укажите полный адрес:\n"
            "<i>Улица, дом, квартира, ориентир</i>"
        ),
        "ask_delivery_time": "🕐 Когда вам удобно получить заказ?",
        "ask_other_date": "📅 Укажите дату доставки (например: 28.02.2026):",
        "ask_payment": "💳 Выберите способ оплаты:",
        "confirm_order": (
            "📋 <b>Проверьте заказ:</b>\n\n"
            "👤 Имя: {name}\n"
            "📱 Телефон: {phone}\n"
            "📦 Товар: {product}\n"
            "🔢 Количество: {quantity} шт\n"
            "💰 Цена: {item_total:,.0f} сум\n"
            "📍 Регион: {region}\n"
            "🏠 Адрес: {address}\n"
            "📅 Доставка: {delivery_date}\n"
            "🚚 Стоимость доставки: {delivery_cost:,.0f} сум\n"
            "💳 Оплата: {payment}\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 <b>Итого: {total:,.0f} сум</b>\n\n"
            "Всё верно?"
        ),
        "order_created": (
            "✅ <b>Заказ #{order_id} успешно создан!</b>\n\n"
            "📦 Товар: {product}\n"
            "💵 Сумма: {total:,.0f} сум\n"
            "📅 Доставка: {delivery_time}\n\n"
            "Мы свяжемся с вами для подтверждения.\n"
            "Спасибо за заказ! 🙏"
        ),
        "order_cancelled": "❌ Заказ отменён. Возвращаемся в главное меню.",
        "order_error": "⚠️ Произошла ошибка при создании заказа. Попробуйте позже.",
        "need_phone": "📱 Сначала поделитесь номером телефона.",
        "search_results": "🔍 <b>Результаты поиска:</b>\n\nВыберите товар:",
        "no_results": "❌ Товары не найдены. Попробуйте другой запрос.",
        "enter_search": "🔍 Введите название товара для поиска:",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        "my_orders_header": "📦 <b>Ваши заказы:</b>\n\n",
        "no_orders": "У вас пока нет заказов.",
        "order_status": (
            "📦 <b>Заказ #{order_id}</b>\n"
            "📅 {date}\n"
            "📊 Статус: {status}\n"
            "💵 Сумма: {total:,.0f} сум\n"
            "━━━━━━━━━━━━━━━\n"
        ),
    },
    "uz": {
        "order_start": (
            "🛒 <b>Buyurtma berish</b>\n\n"
            "Ismingiz nima? (Ism va familiya)"
        ),
        "ask_product": (
            "📦 <b>Tovar tanlash</b>\n\n"
            "• <b>Barcha mahsulotlar</b> — katalogni ko'rish\n"
            "• <b>Qidirish</b> — nomi bo'yicha qidirish\n"
            "• <b>Kod orqali</b> — artikulni kiritish"
        ),
        "enter_code": "🔢 Tovar artikulini kiriting:",
        "enter_search": "🔍 Tovar nomini kiriting:",
        "browse_catalog": "📋 <b>Tovarlar katalogi</b>\n\nKo'rish uchun tovarni tanlang:",
        "product_found": (
            "✅ <b>Tovar topildi!</b>\n\n"
            "📦 {name}\n"
            "🏷 Artikul: {article}\n"
            "💰 Narxi: {price:,.0f} so'm\n"
            "📊 Mavjud: {quantity} dona\n\n"
            "Buyurtmaga qo'shilsinmi?"
        ),
        "product_detail": (
            "📦 <b>{name}</b>\n\n"
            "🏷 Artikul: {article}\n"
            "💰 Narxi: {price:,.0f} so'm\n"
            "📊 Mavjud: {quantity} dona"
        ),
        "product_not_found": "❌ {article} artikuldagi tovar topilmadi. Boshqasini sinab ko'ring.",
        "ask_quantity": "🔢 Miqdorini kiriting:",
        "ask_location": (
            "📍 <b>Yetkazib berish hududini tanlang</b>\n\n"
            "Hudud tugmasini bosing yoki joylashuvni yuboring"
        ),
        "ask_address": (
            "🏠 <b>Yetkazib berish manzili</b>\n\n"
            "To'liq manzilni kiriting:\n"
            "<i>Ko'cha, uy, kvartira, mo'ljal</i>"
        ),
        "ask_delivery_time": "🕐 Buyurtmani qachon olishni xohlaysiz?",
        "ask_other_date": "📅 Yetkazib berish sanasini kiriting (masalan: 28.02.2026):",
        "ask_payment": "💳 To'lov usulini tanlang:",
        "confirm_order": (
            "📋 <b>Buyurtmani tekshiring:</b>\n\n"
            "👤 Ism: {name}\n"
            "📱 Telefon: {phone}\n"
            "📦 Tovar: {product}\n"
            "🔢 Miqdori: {quantity} dona\n"
            "💰 Narxi: {item_total:,.0f} so'm\n"
            "📍 Hudud: {region}\n"
            "🏠 Manzil: {address}\n"
            "📅 Yetkazish: {delivery_date}\n"
            "🚚 Yetkazib berish: {delivery_cost:,.0f} so'm\n"
            "💳 To'lov: {payment}\n"
            "━━━━━━━━━━━━━━━\n"
            "💵 <b>Jami: {total:,.0f} so'm</b>\n\n"
            "Hammasi to'g'rimi?"
        ),
        "order_created": (
            "✅ <b>Buyurtma #{order_id} muvaffaqiyatli yaratildi!</b>\n\n"
            "📦 Tovar: {product}\n"
            "💵 Summa: {total:,.0f} so'm\n"
            "📅 Yetkazish: {delivery_time}\n\n"
            "Tasdiqlash uchun siz bilan bog'lanamiz.\n"
            "Buyurtma uchun rahmat! 🙏"
        ),
        "order_cancelled": "❌ Buyurtma bekor qilindi. Asosiy menyuga qaytamiz.",
        "order_error": "⚠️ Buyurtma yaratishda xatolik yuz berdi. Keyinroq urinib ko'ring.",
        "need_phone": "📱 Avval telefon raqamingizni ulashing.",
        "search_results": "🔍 <b>Qidiruv natijalari:</b>\n\nTovarni tanlang:",
        "no_results": "❌ Tovar topilmadi. Boshqa so'rov bilan sinab ko'ring.",
        "enter_search": "🔍 Qidirish uchun tovar nomini kiriting:",
        "today": "Bugun",
        "tomorrow": "Ertaga",
        "my_orders_header": "📦 <b>Sizning buyurtmalaringiz:</b>\n\n",
        "no_orders": "Sizda hali buyurtmalar yo'q.",
        "order_status": (
            "📦 <b>Buyurtma #{order_id}</b>\n"
            "📅 {date}\n"
            "📊 Holati: {status}\n"
            "💵 Summa: {total:,.0f} so'm\n"
            "━━━━━━━━━━━━━━━\n"
        ),
    },
}

def _is_cancel(text: str) -> bool:
    return text.lower() in [c.lower() for c in CANCEL_RU + CANCEL_UZ]

def get_msg(lang: str, key: str) -> str:
    return MSGS.get(lang, MSGS["ru"]).get(key, MSGS["ru"][key])

def is_tashkent(region: str) -> bool:
    return any(kw in region.lower() for kw in TASHKENT_REGIONS)

def get_delivery_cost(region: str) -> int:
    return 39_000 if is_tashkent(region) else 49_000

def get_delivery_time(region: str, lang: str) -> str:
    if is_tashkent(region):
        return get_msg(lang, "tomorrow")
    return "3-5 дней" if lang == "ru" else "3-5 kun"

@router.message(Chat.active, F.text.in_(["🛒 Buyurtma berish", "🛒 Оформить заказ"]))
async def start_order(message: types.Message, state: FSMContext, **kwargs) -> None:

    user_repo = kwargs.get("user_repo")

    user = None
    if user_repo:
        user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.phone:
        await state.set_state(Registration.waiting_phone)
        await message.answer(
            MSGS["ru"]["need_phone"] + "\n" + MSGS["uz"]["need_phone"],
            reply_markup=phone_keyboard(),
        )
        return

    lang = user.language or "ru"

    await state.update_data(
        order_lang=lang,
        order_phone=user.phone,
        order_user_id=user.id,
        order_name=None,
        order_product_article=None,
        order_product_name=None,
        order_product_price=0,
        order_product_offer_id=None,
        order_quantity=1,
        order_region=None,
        order_address=None,
        order_delivery_date=None,
        order_payment=None,
    )

    await state.set_state(Order.waiting_name)
    await message.answer(
        get_msg(lang, "order_start"),
        reply_markup=cancel_order_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Order.waiting_name, F.text.func(_is_cancel))
@router.message(Order.waiting_product, F.text.func(_is_cancel))
@router.message(Order.waiting_product_quantity, F.text.func(_is_cancel))
@router.message(Order.waiting_location, F.text.func(_is_cancel))
@router.message(Order.waiting_address, F.text.func(_is_cancel))
@router.message(Order.waiting_delivery_time, F.text.func(_is_cancel))
@router.message(Order.waiting_payment, F.text.func(_is_cancel))
@router.message(Order.confirmation, F.text.func(_is_cancel))
async def cancel_order(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")
    await state.clear()
    await state.set_state(Chat.active)
    await message.answer(
        get_msg(lang, "order_cancelled"),
        reply_markup=main_menu_keyboard(lang),
    )

@router.message(Order.waiting_name, F.text)
async def process_name(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.update_data(order_name=message.text.strip())
    await state.set_state(Order.waiting_product)
    await message.answer(
        get_msg(lang, "ask_product"),
        reply_markup=product_input_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Order.waiting_product, F.text.in_(["� Все товары", "📋 Barcha mahsulotlar"]))
async def browse_all_products(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")
    crm_service: CRMService = kwargs.get("crm_service")

    per_page = 5
    products, total = await crm_service.search_products(limit=per_page, offset=0)

    if not products:
        await message.answer(
            get_msg(lang, "no_results"),
            reply_markup=product_input_keyboard(lang),
        )
        return

    await state.update_data(search_query="", search_page=0, browse_mode=True)

    product_list = []
    for p in products:
        price = 0
        if p.offers and p.offers[0].prices:
            price = p.offers[0].prices[0].price or 0
        product_list.append({
            "article": p.article,
            "name": p.name,
            "price": price,
        })

    header = get_msg(lang, "browse_catalog")
    if total > per_page:
        found_text = f"Jami: {total}" if lang == "uz" else f"Всего: {total}"
        header = f"{header}\n\n{found_text}"

    await message.answer(
        header,
        reply_markup=product_select_inline(product_list, lang, page=0, total=total, per_page=per_page, query="", browse_mode=True),
        parse_mode="HTML",
    )

@router.message(Order.waiting_product, F.text.in_(["🔍 Поиск", "🔍 Qidirish"]))
async def ask_search_product(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.update_data(input_mode="search")
    await message.answer(
        get_msg(lang, "enter_search"),
        reply_markup=cancel_order_keyboard(lang),
    )

@router.message(Order.waiting_product, F.text.in_(["🔢 По коду", "🔢 Kod orqali"]))
async def ask_product_code(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.update_data(input_mode="code")
    await message.answer(
        get_msg(lang, "enter_code"),
        reply_markup=cancel_order_keyboard(lang),
    )

@router.message(Order.waiting_product, F.text)
async def process_product(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")
    crm_service: CRMService = kwargs.get("crm_service")
    input_mode = data.get("input_mode", "auto")

    text = message.text.strip()

    if input_mode == "code":
        product = await crm_service.get_product_by_article(text)
        if product:
            await _show_product_and_proceed(message, state, product, lang)
        else:
            await message.answer(
                get_msg(lang, "product_not_found").format(article=text),
                reply_markup=product_input_keyboard(lang),
            )
        await state.update_data(input_mode="auto")
        return

    if input_mode == "search":
        per_page = 5
        products, total = await crm_service.search_products(query=text, limit=per_page, offset=0)

        if products:
            await state.update_data(search_query=text, search_page=0, browse_mode=False)
            await _show_product_list(message, products, total, per_page, lang, text, browse_mode=False)
        else:
            await message.answer(
                get_msg(lang, "no_results"),
                reply_markup=product_input_keyboard(lang),
            )
        await state.update_data(input_mode="auto")
        return

    product = await crm_service.get_product_by_article(text)

    if product:
        await _show_product_and_proceed(message, state, product, lang)
        return

    per_page = 5
    products, total = await crm_service.search_products(query=text, limit=per_page, offset=0)

    if products:
        await state.update_data(search_query=text, search_page=0, browse_mode=False)
        await _show_product_list(message, products, total, per_page, lang, text, browse_mode=False)
        return

    await message.answer(
        get_msg(lang, "product_not_found").format(article=text),
        reply_markup=product_input_keyboard(lang),
    )

async def _show_product_and_proceed(message: types.Message, state: FSMContext, product, lang: str) -> None:

    price = 0
    quantity = 0
    offer_id = None
    image_url = product.image_url

    if product.offers and len(product.offers) > 0:
        first_offer = product.offers[0]
        if first_offer.prices and len(first_offer.prices) > 0:
            price = first_offer.prices[0].price or 0
        quantity = int(first_offer.quantity or 0)
        offer_id = first_offer.id
        if first_offer.images and len(first_offer.images) > 0:
            image_url = first_offer.images[0]

    await state.update_data(
        order_product_article=product.article,
        order_product_name=product.name,
        order_product_price=price,
        order_product_offer_id=offer_id,
    )

    product_text = get_msg(lang, "product_found").format(
        name=product.name,
        article=product.article,
        price=price,
        quantity=quantity,
    )

    if image_url:
        try:
            await message.answer_photo(photo=image_url, caption=product_text, parse_mode="HTML")
        except Exception:
            await message.answer(product_text, parse_mode="HTML")
    else:
        await message.answer(product_text, parse_mode="HTML")

    await message.answer(
        get_msg(lang, "ask_quantity"),
        reply_markup=quantity_keyboard(lang),
    )
    await state.set_state(Order.waiting_product_quantity)

async def _show_product_list(
    message: types.Message,
    products: list,
    total: int,
    per_page: int,
    lang: str,
    query: str,
    browse_mode: bool = False,
) -> None:

    product_list = []
    for p in products:
        price = 0
        if p.offers and p.offers[0].prices:
            price = p.offers[0].prices[0].price or 0
        product_list.append({
            "article": p.article,
            "name": p.name,
            "price": price,
        })

    header = get_msg(lang, "browse_catalog") if browse_mode else get_msg(lang, "search_results")
    if total > per_page:
        found_text = f"Topildi: {total}" if lang == "uz" else f"Найдено: {total}"
        header = f"{header}\n\n{found_text}"

    await message.answer(
        header,
        reply_markup=product_select_inline(product_list, lang, page=0, total=total, per_page=per_page, query=query, browse_mode=browse_mode),
        parse_mode="HTML",
    )

@router.callback_query(F.data.startswith("view:"))
async def view_product_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    article = callback.data.split(":")[1]
    crm_service: CRMService = kwargs.get("crm_service")
    data = await state.get_data()
    lang = data.get("order_lang", "ru")
    query = data.get("search_query", "")
    page = data.get("search_page", 0)
    browse_mode = data.get("browse_mode", False)

    product = await crm_service.get_product_by_article(article)

    if not product:
        await callback.answer("Товар не найден" if lang == "ru" else "Tovar topilmadi")
        return

    price = 0
    quantity = 0
    image_url = product.image_url

    if product.offers and len(product.offers) > 0:
        first_offer = product.offers[0]
        if first_offer.prices and len(first_offer.prices) > 0:
            price = first_offer.prices[0].price or 0
        quantity = int(first_offer.quantity or 0)
        if first_offer.images and len(first_offer.images) > 0:
            image_url = first_offer.images[0]

    product_text = get_msg(lang, "product_detail").format(
        name=product.name,
        article=product.article,
        price=price,
        quantity=quantity,
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    if image_url:
        try:
            await callback.message.answer_photo(
                photo=image_url,
                caption=product_text,
                reply_markup=product_card_inline(article, lang, query, page, browse_mode),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(
                product_text,
                reply_markup=product_card_inline(article, lang, query, page, browse_mode),
                parse_mode="HTML",
            )
    else:
        await callback.message.answer(
            product_text,
            reply_markup=product_card_inline(article, lang, query, page, browse_mode),
            parse_mode="HTML",
        )

    await callback.answer()

@router.callback_query(F.data.startswith("product:"))
async def select_product_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    article = callback.data.split(":")[1]
    crm_service: CRMService = kwargs.get("crm_service")
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    product = await crm_service.get_product_by_article(article)

    if not product:
        await callback.answer("Товар не найден" if lang == "ru" else "Tovar topilmadi")
        return

    price = 0
    quantity = 0
    offer_id = None

    if product.offers and len(product.offers) > 0:
        first_offer = product.offers[0]
        if first_offer.prices and len(first_offer.prices) > 0:
            price = first_offer.prices[0].price or 0
        quantity = int(first_offer.quantity or 0)
        offer_id = first_offer.id

    await state.update_data(
        order_product_article=product.article,
        order_product_name=product.name,
        order_product_price=price,
        order_product_offer_id=offer_id,
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    product_text = get_msg(lang, "product_found").format(
        name=product.name,
        article=product.article,
        price=price,
        quantity=quantity,
    )

    await callback.message.answer(product_text, parse_mode="HTML")
    await callback.message.answer(
        get_msg(lang, "ask_quantity"),
        reply_markup=quantity_keyboard(lang),
    )
    await state.set_state(Order.waiting_product_quantity)
    await callback.answer()

@router.callback_query(F.data == "order:cancel")
async def cancel_order_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.clear()
    await state.set_state(Chat.active)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_msg(lang, "order_cancelled"),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop_callback(callback: types.CallbackQuery, **kwargs) -> None:

    await callback.answer()

@router.callback_query(F.data.startswith("page:"))
async def pagination_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    parts = callback.data.split(":", 2)
    page = int(parts[1])
    query = parts[2] if len(parts) > 2 else ""

    crm_service: CRMService = kwargs.get("crm_service")
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    per_page = 5
    offset = page * per_page

    products, total = await crm_service.search_products(query=query, limit=per_page, offset=offset)

    if not products:
        await callback.answer("Товары не найдены" if lang == "ru" else "Tovarlar topilmadi")
        return

    await state.update_data(search_page=page, browse_mode=False)

    product_list = []
    for p in products:
        price = 0
        if p.offers and p.offers[0].prices:
            price = p.offers[0].prices[0].price or 0
        product_list.append({
            "article": p.article,
            "name": p.name,
            "price": price,
        })

    header = get_msg(lang, "search_results")
    if total > per_page:
        found_text = f"Topildi: {total}" if lang == "uz" else f"Найдено: {total}"
        header = f"{header}\n\n{found_text}"

    await callback.message.edit_text(
        header,
        reply_markup=product_select_inline(product_list, lang, page=page, total=total, per_page=per_page, query=query, browse_mode=False),
        parse_mode="HTML",
    )
    await callback.answer()

@router.callback_query(F.data.startswith("browse:"))
async def browse_pagination_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    parts = callback.data.split(":", 2)
    page = int(parts[1])

    crm_service: CRMService = kwargs.get("crm_service")
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    per_page = 5
    offset = page * per_page

    products, total = await crm_service.search_products(limit=per_page, offset=offset)

    if not products:
        await callback.answer("Товары не найдены" if lang == "ru" else "Tovarlar topilmadi")
        return

    await state.update_data(search_page=page, browse_mode=True)

    product_list = []
    for p in products:
        price = 0
        if p.offers and p.offers[0].prices:
            price = p.offers[0].prices[0].price or 0
        product_list.append({
            "article": p.article,
            "name": p.name,
            "price": price,
        })

    header = get_msg(lang, "browse_catalog")
    if total > per_page:
        found_text = f"Jami: {total}" if lang == "uz" else f"Всего: {total}"
        header = f"{header}\n\n{found_text}"

    await callback.message.edit_text(
        header,
        reply_markup=product_select_inline(product_list, lang, page=page, total=total, per_page=per_page, query="", browse_mode=True),
        parse_mode="HTML",
    )
    await callback.answer()

@router.message(Order.waiting_product_quantity, F.text)
async def process_quantity(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    text = message.text.strip()

    try:
        qty = int(text)
        if qty < 1:
            qty = 1
        if qty > 100:
            qty = 100
    except ValueError:
        qty = 1

    await state.update_data(order_quantity=qty)
    await state.set_state(Order.waiting_location)
    await message.answer(
        get_msg(lang, "ask_location"),
        reply_markup=location_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Order.waiting_location, F.location)
async def process_location(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    lat = message.location.latitude
    lon = message.location.longitude

    if 40.5 < lat < 42.0 and 68.5 < lon < 70.5:
        region = "Tashkent"
    else:
        region = "Other"

    await state.update_data(order_region=region)
    await state.set_state(Order.waiting_address)
    await message.answer(
        get_msg(lang, "ask_address"),
        reply_markup=cancel_order_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Order.waiting_location, F.text)
async def process_region_text(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    text = message.text.strip()
    region = REGION_MAP.get(text, text)

    await state.update_data(order_region=region)
    await state.set_state(Order.waiting_address)
    await message.answer(
        get_msg(lang, "ask_address"),
        reply_markup=cancel_order_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Order.waiting_address, F.text)
async def process_address(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.update_data(order_address=message.text.strip())
    await state.set_state(Order.waiting_delivery_time)
    await message.answer(
        get_msg(lang, "ask_delivery_time"),
        reply_markup=delivery_time_keyboard(lang),
    )

@router.message(Order.waiting_delivery_time, F.text.in_(["🕐 Сегодня", "🕐 Bugun"]))
async def process_today(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    today = date.today()
    await state.update_data(
        order_delivery_date=today.isoformat(),
        order_delivery_display=get_msg(lang, "today"),
    )
    await state.set_state(Order.waiting_payment)
    await message.answer(get_msg(lang, "ask_payment"), reply_markup=payment_keyboard(lang))

@router.message(Order.waiting_delivery_time, F.text.in_(["🕑 Завтра", "🕑 Ertaga"]))
async def process_tomorrow(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    tomorrow = date.today() + timedelta(days=1)
    await state.update_data(
        order_delivery_date=tomorrow.isoformat(),
        order_delivery_display=get_msg(lang, "tomorrow"),
    )
    await state.set_state(Order.waiting_payment)
    await message.answer(get_msg(lang, "ask_payment"), reply_markup=payment_keyboard(lang))

@router.message(Order.waiting_delivery_time, F.text.in_(["📅 Другой день", "📅 Boshqa kun"]))
async def ask_other_date(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await message.answer(
        get_msg(lang, "ask_other_date"),
        reply_markup=cancel_order_keyboard(lang),
    )

@router.message(Order.waiting_delivery_time, F.text)
async def process_custom_date(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    text = message.text.strip()

    for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            parsed = datetime.strptime(text, fmt).date()
            await state.update_data(
                order_delivery_date=parsed.isoformat(),
                order_delivery_display=parsed.strftime("%d.%m.%Y"),
            )
            await state.set_state(Order.waiting_payment)
            await message.answer(get_msg(lang, "ask_payment"), reply_markup=payment_keyboard(lang))
            return
        except ValueError:
            continue

    await state.update_data(
        order_delivery_date=date.today().isoformat(),
        order_delivery_display=text,
    )
    await state.set_state(Order.waiting_payment)
    await message.answer(get_msg(lang, "ask_payment"), reply_markup=payment_keyboard(lang))

PAYMENT_MAP = {
    "💵 Наличные": ("cash", "Наличные"),
    "💵 Naqd pul": ("cash", "Naqd pul"),
    "💳 Карта (Click/Payme)": ("card", "Карта"),
    "💳 Karta (Click/Payme)": ("card", "Karta"),
}

@router.message(Order.waiting_payment, F.text)
async def process_payment(message: types.Message, state: FSMContext, **kwargs) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    text = message.text.strip()
    payment_code, payment_display = PAYMENT_MAP.get(text, ("cash", text))

    await state.update_data(
        order_payment_code=payment_code,
        order_payment_display=payment_display,
    )

    await state.set_state(Order.confirmation)
    await _show_confirmation(message, state)

async def _show_confirmation(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    region = data.get("order_region", "")
    quantity = data.get("order_quantity", 1)
    price = data.get("order_product_price", 0)
    item_total = price * quantity
    delivery_cost = get_delivery_cost(region)
    total = item_total + delivery_cost

    text = get_msg(lang, "confirm_order").format(
        name=data.get("order_name", "-"),
        phone=data.get("order_phone", "-"),
        product=f"{data.get('order_product_article', '')} - {data.get('order_product_name', '-')}",
        quantity=quantity,
        item_total=item_total,
        region=region,
        address=data.get("order_address", "-"),
        delivery_date=data.get("order_delivery_display", "-"),
        delivery_cost=delivery_cost,
        payment=data.get("order_payment_display", "-"),
        total=total,
    )

    await message.answer(text, reply_markup=confirm_keyboard(lang), parse_mode="HTML")

@router.message(Order.confirmation, F.text.in_(["✅ Подтвердить", "✅ Tasdiqlash"]))
async def confirm_order(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")
    crm: CRMClient = kwargs.get("crm_client")
    crm_service: CRMService = kwargs.get("crm_service")

    await logger.info(
        "order_confirm_start",
        phone=data.get("order_phone"),
        product=data.get("order_product_article"),
    )

    try:

        region = data.get("order_region", "")
        quantity = data.get("order_quantity", 1)
        price = data.get("order_product_price", 0)
        item_total = price * quantity
        delivery_cost = get_delivery_cost(region)
        total = item_total + delivery_cost

        external_id = f"tg-{uuid.uuid4().hex[:12]}"

        delivery_date_str = data.get("order_delivery_date")
        delivery_date = None
        if delivery_date_str:
            try:
                delivery_date = date.fromisoformat(delivery_date_str)
            except (ValueError, TypeError):
                delivery_date = date.today()

        full_name = data.get("order_name", "").strip()
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Клиент"
        last_name = name_parts[1] if len(name_parts) > 1 else None

        items = [
            OrderItemCreate(
                product_name=data.get("order_product_name"),
                quantity=quantity,
                initial_price=price,
            )
        ]

        offer_id = data.get("order_product_offer_id")
        if offer_id:
            items[0].offer = OrderItemOffer(id=offer_id)

        order = OrderCreate(
            external_id=external_id,
            first_name=first_name,
            last_name=last_name,
            phone=data.get("order_phone"),
            customer_comment=f"Telegram: {data.get('order_product_article')} x{quantity}",
            order_method="messenger",
            order_type="eshop",
            status="new",
            items=items,
            delivery=OrderDeliveryInput(
                code="courier",
                cost=delivery_cost,
                delivery_date=delivery_date,
                address=Address(
                    text=data.get("order_address"),
                    region=region,
                ),
            ),
            source={"source": "telegram", "medium": "bot"},
        )

        response = crm.order_create(order)

        if response.is_successful():
            order_id = response.get_response().get("id", external_id)
            await logger.info("order_created", order_id=order_id, external_id=external_id)

            delivery_time = get_delivery_time(region, lang)

            await state.clear()
            await state.set_state(Chat.active)
            await message.answer(
                get_msg(lang, "order_created").format(
                    order_id=order_id,
                    product=f"{data.get('order_product_article')} - {data.get('order_product_name')}",
                    total=total,
                    delivery_time=delivery_time,
                ),
                reply_markup=main_menu_keyboard(lang),
                parse_mode="HTML",
            )
        else:
            await logger.error(
                "order_create_failed",
                errors=response.get_errors(),
                status=response.get_status_code(),
            )
            await message.answer(
                get_msg(lang, "order_error"),
                reply_markup=main_menu_keyboard(lang),
            )
            await state.clear()
            await state.set_state(Chat.active)

    except Exception as e:
        await logger.error("order_create_exception", error=str(e), error_type=type(e).__name__)
        await message.answer(
            get_msg(lang, "order_error"),
            reply_markup=main_menu_keyboard(lang),
        )
        await state.clear()
        await state.set_state(Chat.active)

@router.message(Order.confirmation, F.text.in_(["✏️ Редактировать", "✏️ Tahrirlash"]))
async def edit_order(message: types.Message, state: FSMContext, **kwargs) -> None:

    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    await state.set_state(Order.waiting_name)
    await message.answer(
        get_msg(lang, "order_start"),
        reply_markup=cancel_order_keyboard(lang),
        parse_mode="HTML",
    )

@router.message(Chat.active, F.text.in_(["📦 Мои заказы", "📦 Buyurtmalarim"]))
async def my_orders(message: types.Message, state: FSMContext, **kwargs) -> None:

    user_repo = kwargs.get("user_repo")
    crm_service: CRMService = kwargs.get("crm_service")

    user = None
    if user_repo:
        user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.phone:
        await message.answer(
            MSGS["ru"]["need_phone"] + "\n" + MSGS["uz"]["need_phone"],
            reply_markup=phone_keyboard(),
        )
        return

    lang = user.language or "ru"

    orders = await crm_service.get_customer_orders(user.phone, limit=5)

    if not orders:
        await message.answer(
            get_msg(lang, "no_orders"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    text = get_msg(lang, "my_orders_header")

    status_map = {
        "new": "🆕 Новый" if lang == "ru" else "🆕 Yangi",
        "processing": "⏳ В обработке" if lang == "ru" else "⏳ Jarayonda",
        "shipped": "🚚 Отправлен" if lang == "ru" else "🚚 Jo'natildi",
        "delivered": "✅ Доставлен" if lang == "ru" else "✅ Yetkazildi",
        "cancelled": "❌ Отменён" if lang == "ru" else "❌ Bekor qilindi",
    }

    for order in orders:
        order_date = ""
        if order.created_at:
            order_date = order.created_at.strftime("%d.%m.%Y")

        status = status_map.get(order.status, order.status or "—")
        total = order.total_summ or 0

        text += get_msg(lang, "order_status").format(
            order_id=order.id,
            date=order_date,
            status=status,
            total=total,
        )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

@router.callback_query(F.data.startswith("order_status:"))
async def refresh_order_status(callback: types.CallbackQuery, state: FSMContext, **kwargs) -> None:

    order_id = callback.data.split(":")[1]
    crm_service: CRMService = kwargs.get("crm_service")
    data = await state.get_data()
    lang = data.get("order_lang", "ru")

    order = await crm_service.get_order_by_id(order_id)

    if not order:
        await callback.answer("Заказ не найден" if lang == "ru" else "Buyurtma topilmadi")
        return

    status_map = {
        "new": "🆕 Новый" if lang == "ru" else "🆕 Yangi",
        "processing": "⏳ В обработке" if lang == "ru" else "⏳ Jarayonda",
        "shipped": "🚚 Отправлен" if lang == "ru" else "🚚 Jo'natildi",
        "delivered": "✅ Доставлен" if lang == "ru" else "✅ Yetkazildi",
        "cancelled": "❌ Отменён" if lang == "ru" else "❌ Bekor qilindi",
    }

    status = status_map.get(order.status, order.status or "—")

    await callback.answer(f"Статус: {status}" if lang == "ru" else f"Holati: {status}")
