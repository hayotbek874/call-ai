from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Raqamni yuborish / Отправить номер",
                    request_contact=True,
                ),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="💎 Katalog"),
                    KeyboardButton(text="🛒 Buyurtma berish"),
                ],
                [
                    KeyboardButton(text="📦 Buyurtmalarim"),
                    KeyboardButton(text="👤 Operator"),
                ],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💎 Каталог"),
                KeyboardButton(text="🛒 Оформить заказ"),
            ],
            [
                KeyboardButton(text="📦 Мои заказы"),
                KeyboardButton(text="👤 Оператор"),
            ],
        ],
        resize_keyboard=True,
    )

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

def cancel_order_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    text = "❌ Bekor qilish" if lang == "uz" else "❌ Отменить"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True,
    )

def skip_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    skip = "⏭ O'tkazib yuborish" if lang == "uz" else "⏭ Пропустить"
    cancel = "❌ Bekor qilish" if lang == "uz" else "❌ Отменить"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=skip)],
            [KeyboardButton(text=cancel)],
        ],
        resize_keyboard=True,
    )

def product_input_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="� Barcha mahsulotlar")],
                [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="🔢 Kod orqali")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Все товары")],
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="🔢 По коду")],
            [KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True,
    )

def quantity_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    cancel = "❌ Bekor qilish" if lang == "uz" else "❌ Отменить"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
            [KeyboardButton(text="5"), KeyboardButton(text="10")],
            [KeyboardButton(text=cancel)],
        ],
        resize_keyboard=True,
    )

def location_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
                [KeyboardButton(text="🏙 Toshkent shahri")],
                [KeyboardButton(text="🏙 Toshkent viloyati")],
                [KeyboardButton(text="🏙 Samarqand")],
                [KeyboardButton(text="🏙 Buxoro")],
                [KeyboardButton(text="🏙 Andijon")],
                [KeyboardButton(text="🏙 Farg'ona")],
                [KeyboardButton(text="🏙 Namangan")],
                [KeyboardButton(text="🏙 Boshqa viloyat")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
            [KeyboardButton(text="🏙 Ташкент город")],
            [KeyboardButton(text="🏙 Ташкентская область")],
            [KeyboardButton(text="🏙 Самарканд")],
            [KeyboardButton(text="🏙 Бухара")],
            [KeyboardButton(text="🏙 Андижан")],
            [KeyboardButton(text="🏙 Фергана")],
            [KeyboardButton(text="🏙 Наманган")],
            [KeyboardButton(text="🏙 Другой регион")],
            [KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True,
    )

def payment_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💵 Naqd pul")],
                [KeyboardButton(text="💳 Karta (Click/Payme)")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 Наличные")],
            [KeyboardButton(text="💳 Карта (Click/Payme)")],
            [KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True,
    )

def confirm_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Tasdiqlash")],
                [KeyboardButton(text="✏️ Tahrirlash")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить")],
            [KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True,
    )

def delivery_time_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:

    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🕐 Bugun"), KeyboardButton(text="🕑 Ertaga")],
                [KeyboardButton(text="📅 Boshqa kun")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕐 Сегодня"), KeyboardButton(text="🕑 Завтра")],
            [KeyboardButton(text="📅 Другой день")],
            [KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True,
    )

def product_select_inline(
    products: list[dict],
    lang: str = "ru",
    page: int = 0,
    total: int = 0,
    per_page: int = 5,
    query: str = "",
    browse_mode: bool = False,
) -> InlineKeyboardMarkup:

    buttons = []

    for p in products:
        article = p.get("article", "")
        name = p.get("name", "")[:25]
        price = p.get("price", 0)
        currency = "so'm" if lang == "uz" else "сум"
        text = f"📦 {name} — {price:,.0f} {currency}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"view:{article}")])

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    if total_pages > 1:
        nav_buttons = []
        page_prefix = "browse" if browse_mode else "page"
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"{page_prefix}:{page - 1}:{query}")
            )
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
        )
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"{page_prefix}:{page + 1}:{query}")
            )
        buttons.append(nav_buttons)

    cancel_text = "❌ Bekor qilish" if lang == "uz" else "❌ Отменить"
    buttons.append([InlineKeyboardButton(text=cancel_text, callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_card_inline(article: str, lang: str = "ru", query: str = "", page: int = 0, browse_mode: bool = False) -> InlineKeyboardMarkup:

    order_text = "🛒 Buyurtma berish" if lang == "uz" else "🛒 Заказать"
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад"

    page_prefix = "browse" if browse_mode else "page"
    back_callback = f"{page_prefix}:{page}:{query}" if query or browse_mode else "order:cancel"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=order_text, callback_data=f"product:{article}")],
        [InlineKeyboardButton(text=back_text, callback_data=back_callback)],
    ])

def order_status_inline(order_id: int | str, lang: str = "ru") -> InlineKeyboardMarkup:

    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"order_status:{order_id}")],
            [InlineKeyboardButton(text="📞 Bog'lanish", callback_data="contact:operator")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"order_status:{order_id}")],
        [InlineKeyboardButton(text="📞 Связаться", callback_data="contact:operator")],
    ])
