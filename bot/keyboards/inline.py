"""
keyboards/inline.py
-------------------
Все инлайн-клавиатуры бота — в одном файле.
Каждая функция принимает данные и возвращает готовую InlineKeyboardMarkup.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ─── Каталог ──────────────────────────────────────────────────────────────────

def categories_keyboard(categories: list, back_callback: str = None) -> InlineKeyboardMarkup:
    """Кнопки для списка категорий (корневых или подкатегорий).
    back_callback — если передан, добавляет кнопку Назад.
    """
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['emoji']} {c['name']}",
            callback_data=f"cat_{c['id']}"
        )]
        for c in categories
    ]
    if back_callback:
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_keyboard(products: list, category_id: int, parent_id: int = None) -> InlineKeyboardMarkup:
    """Кнопки для списка товаров + кнопка Назад к родительской категории."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{p['name']} — {p['price']:,} ₽".replace(",", " "),
            callback_data=f"product_{p['id']}"
        )]
        for p in products
    ]
    # Назад ведёт к родительской категории, а не к самой себе
    back_cb = f"cat_{parent_id}" if parent_id else "back_to_main"
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_keyboard(product_id: int, category_id: int) -> InlineKeyboardMarkup:
    """Кнопки карточки товара: Заказать + Назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Заказать", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"back_to_cat_{category_id}")],
    ])


def order_confirmation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки для уведомления администратору: подтвердить / отклонить."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"cancel_order_{order_id}"),
    ]])


def back_button(callback_data: str) -> InlineKeyboardMarkup:
    """Универсальная кнопка Назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])


# ─── Админка ──────────────────────────────────────────────────────────────────

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Заказы",        callback_data="admin_orders"),
            InlineKeyboardButton(text="📦 Товары",        callback_data="admin_products_0"),
        ],
        [
            InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product"),
            InlineKeyboardButton(text="📊 Статистика",    callback_data="admin_stats"),
        ],
    ])


def admin_orders_keyboard(orders: list) -> InlineKeyboardMarkup:
    """Список заказов для админки — каждый заказ как кнопка."""
    STATUS_ICON = {"new": "🕐", "confirmed": "✅", "done": "📦", "cancelled": "❌"}
    buttons = []
    for o in orders:
        icon = STATUS_ICON.get(o["status"], "•")
        label = f"{icon} #{o['id']} {o['customer_name']} — {o['product_name'][:20]}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"admin_order_{o['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Меню", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_order_detail_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Кнопки смены статуса для конкретного заказа."""
    all_statuses = [
        ("🕐 Новый",       "new"),
        ("✅ Подтверждён", "confirmed"),
        ("📦 Выполнен",    "done"),
        ("❌ Отменён",     "cancelled"),
    ]
    # Показываем только те статусы, в которые можно перейти
    buttons = [
        [InlineKeyboardButton(
            text=f"{'→ ' if s != current_status else '• '}{label}",
            callback_data=f"admin_set_status_{order_id}_{s}",
        )]
        for label, s in all_statuses
        if s != current_status
    ]
    buttons.append([InlineKeyboardButton(text="◀️ К заказам", callback_data="admin_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_products_keyboard(products: list, page: int, total: int,
                            per_page: int = 10) -> InlineKeyboardMarkup:
    """Список товаров с пагинацией и кнопками действий."""
    buttons = []
    for p in products:
        visibility = "👁 Скрыть" if not p["is_hidden"] else "👁 Показать"
        buttons.append([
            InlineKeyboardButton(
                text=f"{'🚫 ' if p['is_hidden'] else ''}{p['name']}",
                callback_data=f"admin_product_{p['id']}_{page}",
            ),
        ])
        buttons.append([
            InlineKeyboardButton(text="✏️ Цену",  callback_data=f"admin_edit_{p['id']}_{page}"),
            InlineKeyboardButton(text=visibility, callback_data=f"admin_toggle_{p['id']}_{page}"),
        ])

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_products_{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{(total + per_page - 1) // per_page}",
        callback_data="noop",
    ))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_products_{page + 1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Меню", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Выбор категории при добавлении товара — только листовые (без подкатегорий)."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['emoji']} {c['name']}",
            callback_data=f"admin_cat_{c['id']}",
        )]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_confirm_product_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение перед сохранением нового товара."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить",  callback_data="admin_confirm_product"),
            InlineKeyboardButton(text="❌ Отменить",   callback_data="admin_cancel_product"),
        ]
    ])
