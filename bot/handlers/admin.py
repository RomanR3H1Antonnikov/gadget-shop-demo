"""
handlers/admin.py
-----------------
Админ-панель: заказы, товары, добавление товара, статистика.
Доступ — только для ADMIN_CHAT_ID. Остальные пользователи игнорируются.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import ADMIN_CHAT_ID
from bot.database import crud
from bot.keyboards.inline import (
    admin_menu_keyboard,
    admin_orders_keyboard,
    admin_order_detail_keyboard,
    admin_products_keyboard,
    admin_categories_keyboard,
    admin_confirm_product_keyboard,
    back_button,
)

logger = logging.getLogger(__name__)
router = Router()

PRODUCTS_PER_PAGE = 10

STATUS_LABEL = {
    "new":       "🕐 Новый",
    "confirmed": "✅ Подтверждён",
    "done":      "📦 Выполнен",
    "cancelled": "❌ Отменён",
}


# ─── Фильтр: только администратор ────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


# ─── /admin — вход в панель ───────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔧 <b>Админ-панель GadgetPro</b>\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text(
            "🔧 <b>Админ-панель GadgetPro</b>\n\nВыберите раздел:",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🔧 <b>Админ-панель GadgetPro</b>\n\nВыберите раздел:",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


# ─── 📋 Заказы ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_orders")
async def cb_admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        orders = await crud.get_recent_orders(20)
        if not orders:
            await callback.message.edit_text(
                "Заказов пока нет.",
                reply_markup=back_button("admin_menu"),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"📋 <b>Последние заказы ({len(orders)})</b>:",
            reply_markup=admin_orders_keyboard(orders),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка загрузки заказов: %s", e)
        await callback.answer("Ошибка загрузки заказов.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_"))
async def cb_admin_order_detail(callback: CallbackQuery):
    """Детали конкретного заказа + кнопки смены статуса."""
    if not is_admin(callback.from_user.id):
        return
    # Формат: admin_order_{id}  (не путать с admin_orders — список)
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer()
        return
    order_id = int(parts[2])

    try:
        order = await crud.get_order(order_id)
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        username = f"@{order['username']}" if order["username"] else "без username"
        price = f"{order['product_price']:,} ₽".replace(",", " ")
        status = STATUS_LABEL.get(order["status"], order["status"])

        text = (
            f"🛒 <b>Заказ #{order['id']}</b>\n\n"
            f"📦 {order['product_name']} ({price})\n"
            f"👤 {order['customer_name']} | {username}\n"
            f"📞 {order['phone']}\n"
            f"🚚 {order['delivery']}\n"
            f"📅 {order['created_at'][:16]}\n\n"
            f"Статус: <b>{status}</b>"
        )

        await callback.message.edit_text(
            text,
            reply_markup=admin_order_detail_keyboard(order_id, order["status"]),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка открытия заказа %d: %s", order_id, e)
        await callback.answer("Ошибка.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_status_"))
async def cb_set_order_status(callback: CallbackQuery, bot: Bot):
    """Меняет статус заказа и уведомляет покупателя."""
    if not is_admin(callback.from_user.id):
        return
    # Формат: admin_set_status_{order_id}_{status}
    parts = callback.data.split("_")
    order_id = int(parts[3])
    new_status = parts[4]

    try:
        order = await crud.get_order(order_id)
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        await crud.update_order_status(order_id, new_status)

        # Уведомление покупателю
        status_label = STATUS_LABEL.get(new_status, new_status)
        user_messages = {
            "confirmed": f"✅ Ваш заказ <b>#{order_id}</b> подтверждён! Менеджер свяжется с вами.",
            "done":      f"📦 Ваш заказ <b>#{order_id}</b> выполнен! Спасибо за покупку.",
            "cancelled": f"❌ Ваш заказ <b>#{order_id}</b> отменён. Обратитесь к менеджеру, если это ошибка.",
        }
        if new_status in user_messages:
            try:
                await bot.send_message(
                    chat_id=order["user_id"],
                    text=user_messages[new_status],
                    parse_mode="HTML",
                )
            except Exception:
                pass  # Пользователь мог заблокировать бота

        # Обновляем сообщение у администратора
        username = f"@{order['username']}" if order["username"] else "без username"
        price = f"{order['product_price']:,} ₽".replace(",", " ")
        await callback.message.edit_text(
            f"🛒 <b>Заказ #{order['id']}</b>\n\n"
            f"📦 {order['product_name']} ({price})\n"
            f"👤 {order['customer_name']} | {username}\n"
            f"📞 {order['phone']}\n"
            f"🚚 {order['delivery']}\n"
            f"📅 {order['created_at'][:16]}\n\n"
            f"Статус: <b>{status_label}</b>",
            reply_markup=admin_order_detail_keyboard(order_id, new_status),
            parse_mode="HTML",
        )
        await callback.answer(f"Статус изменён: {status_label}")
    except Exception as e:
        logger.error("Ошибка смены статуса заказа %d: %s", order_id, e)
        await callback.answer("Ошибка.", show_alert=True)


# ─── 📦 Товары ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_products_"))
async def cb_admin_products(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page = int(callback.data.split("_")[2])

    try:
        products = await crud.get_all_products_admin(
            offset=page * PRODUCTS_PER_PAGE,
            limit=PRODUCTS_PER_PAGE,
        )
        # Считаем общее количество
        all_products = await crud.get_all_products_admin(offset=0, limit=10_000)
        total = len(all_products)

        if not products:
            await callback.message.edit_text(
                "Товаров нет.",
                reply_markup=back_button("admin_menu"),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"📦 <b>Товары</b> (стр. {page + 1}, всего {total}):",
            reply_markup=admin_products_keyboard(products, page, total, PRODUCTS_PER_PAGE),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка загрузки товаров: %s", e)
        await callback.answer("Ошибка загрузки.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_toggle_"))
async def cb_toggle_product(callback: CallbackQuery):
    """Переключает видимость товара и обновляет список."""
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    product_id = int(parts[2])
    page = int(parts[3])

    try:
        await crud.toggle_product_visibility(product_id)
        # Обновляем страницу
        products = await crud.get_all_products_admin(
            offset=page * PRODUCTS_PER_PAGE,
            limit=PRODUCTS_PER_PAGE,
        )
        all_products = await crud.get_all_products_admin(offset=0, limit=10_000)
        total = len(all_products)

        await callback.message.edit_text(
            f"📦 <b>Товары</b> (стр. {page + 1}, всего {total}):",
            reply_markup=admin_products_keyboard(products, page, total, PRODUCTS_PER_PAGE),
            parse_mode="HTML",
        )
        await callback.answer("Видимость изменена.")
    except Exception as e:
        logger.error("Ошибка переключения видимости товара %d: %s", product_id, e)
        await callback.answer("Ошибка.", show_alert=True)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    """Кнопка-заглушка (счётчик страниц) — ничего не делает."""
    await callback.answer()


# ─── ✏️ Редактирование цены товара (FSM) ─────────────────────────────────────

class EditProductStates(StatesGroup):
    waiting_price = State()


@router.callback_query(F.data.startswith("admin_edit_"))
async def cb_edit_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    product_id = int(parts[2])
    page = int(parts[3])

    try:
        product = await crud.get_product(product_id)
        if not product:
            await callback.answer("Товар не найден.", show_alert=True)
            return

        await state.set_state(EditProductStates.waiting_price)
        await state.update_data(product_id=product_id, page=page)

        await callback.message.answer(
            f"✏️ Редактирование цены: <b>{product['name']}</b>\n"
            f"Текущая цена: <b>{product['price']:,} ₽</b>\n\n".replace(",", " ") +
            "Введите новую цену (только цифры):",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка открытия редактирования: %s", e)
        await callback.answer("Ошибка.", show_alert=True)
    await callback.answer()


@router.message(EditProductStates.waiting_price)
async def process_edit_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    raw = message.text.strip().replace(" ", "").replace(",", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Введите корректную цену (положительное число):")
        return

    data = await state.get_data()
    await state.clear()
    new_price = int(raw)

    try:
        async with __import__("aiosqlite").connect(__import__("bot.config", fromlist=["DB_PATH"]).DB_PATH) as db:
            await db.execute(
                "UPDATE products SET price = ? WHERE id = ?",
                (new_price, data["product_id"])
            )
            await db.commit()

        product = await crud.get_product(data["product_id"])
        await message.answer(
            f"✅ Цена обновлена: <b>{product['name']}</b> — "
            f"<b>{new_price:,} ₽</b>".replace(",", " "),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка обновления цены: %s", e)
        await message.answer("Ошибка обновления цены.")


# ─── ➕ Добавление товара (FSM) ───────────────────────────────────────────────

class AddProductStates(StatesGroup):
    waiting_category    = State()
    waiting_name        = State()
    waiting_description = State()
    waiting_price       = State()
    waiting_photo       = State()
    waiting_confirm     = State()


@router.callback_query(F.data == "admin_add_product")
async def cb_add_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    try:
        # Показываем только листовые категории (у которых нет подкатегорий)
        all_cats_raw = await crud.get_root_categories()
        leaf_cats = []
        for cat in all_cats_raw:
            if not await crud.has_subcategories(cat["id"]):
                leaf_cats.append(cat)
            else:
                subs = await crud.get_subcategories(cat["id"])
                leaf_cats.extend(subs)

        await state.set_state(AddProductStates.waiting_category)
        await callback.message.edit_text(
            "➕ <b>Добавление товара</b>\n\nВыберите категорию:",
            reply_markup=admin_categories_keyboard(leaf_cats),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка старта добавления товара: %s", e)
        await callback.answer("Ошибка.", show_alert=True)
    await callback.answer()


@router.callback_query(AddProductStates.waiting_category, F.data.startswith("admin_cat_"))
async def cb_add_product_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    category_id = int(callback.data.split("_")[2])
    category = await crud.get_category(category_id)

    await state.update_data(category_id=category_id, category_name=category["name"])
    await state.set_state(AddProductStates.waiting_name)

    await callback.message.edit_text(
        f"Категория: <b>{category['name']}</b>\n\nВведите название товара:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddProductStates.waiting_name)
async def process_add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if len(message.text.strip()) < 3:
        await message.answer("Слишком короткое название (минимум 3 символа):")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductStates.waiting_description)
    await message.answer("Введите описание товара (2-4 предложения):")


@router.message(AddProductStates.waiting_description)
async def process_add_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if len(message.text.strip()) < 10:
        await message.answer("Слишком короткое описание:")
        return
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProductStates.waiting_price)
    await message.answer("Введите цену в рублях (только цифры):")


@router.message(AddProductStates.waiting_price)
async def process_add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "").replace(",", "")
    if not raw.isdigit() or int(raw) < 0:
        await message.answer("Введите корректную цену (например: 79990):")
        return
    await state.update_data(price=int(raw))
    await state.set_state(AddProductStates.waiting_photo)
    await message.answer(
        "Отправьте фото товара или нажмите /skip чтобы пропустить:"
    )


@router.message(AddProductStates.waiting_photo, F.photo)
async def process_add_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    # Берём file_id фото наилучшего качества
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_url=photo_id)
    await _show_add_confirm(message, state)


@router.message(AddProductStates.waiting_photo, F.text == "/skip")
async def process_add_photo_skip(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(photo_url=None)
    await _show_add_confirm(message, state)


@router.message(AddProductStates.waiting_photo)
async def process_add_photo_invalid(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Отправьте фото или введите /skip чтобы пропустить:")


async def _show_add_confirm(message: Message, state: FSMContext):
    """Показывает итоговые данные и просит подтверждение."""
    data = await state.get_data()
    await state.set_state(AddProductStates.waiting_confirm)
    price_str = f"{data['price']:,} ₽".replace(",", " ")
    photo_str = "✅ Есть" if data.get("photo_url") else "❌ Нет"

    await message.answer(
        f"📦 <b>Проверьте данные нового товара:</b>\n\n"
        f"📁 Категория: {data['category_name']}\n"
        f"🏷 Название: {data['name']}\n"
        f"📝 Описание: {data['description']}\n"
        f"💰 Цена: {price_str}\n"
        f"🖼 Фото: {photo_str}",
        reply_markup=admin_confirm_product_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(AddProductStates.waiting_confirm, F.data == "admin_confirm_product")
async def cb_confirm_add_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    await state.clear()

    try:
        product_id = await crud.add_product(
            category_id=data["category_id"],
            name=data["name"],
            description=data["description"],
            price=data["price"],
            photo_url=data.get("photo_url"),
        )
        await callback.message.edit_text(
            f"✅ Товар <b>{data['name']}</b> добавлен (id={product_id}).",
            reply_markup=back_button("admin_menu"),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка сохранения товара: %s", e)
        await callback.message.edit_text(
            "Ошибка сохранения товара.",
            reply_markup=back_button("admin_menu"),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_cancel_product")
async def cb_cancel_add_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "Добавление товара отменено.",
        reply_markup=back_button("admin_menu"),
    )
    await callback.answer()


# ─── 📊 Статистика ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        stats = await crud.get_stats()
        today_sum = f"{stats['today_sum']:,} ₽".replace(",", " ")

        await callback.message.edit_text(
            "📊 <b>Статистика за сегодня</b>\n\n"
            f"🛒 Заказов: <b>{stats['today_orders']}</b>\n"
            f"💰 Сумма заказов: <b>{today_sum}</b>\n"
            f"👥 Уникальных пользователей: <b>{stats['today_users']}</b>\n"
            f"📦 Популярный товар: <b>{stats['top_product']}</b>\n\n"
            f"<b>За всё время:</b>\n"
            f"🛒 Всего заказов: <b>{stats['total_orders']}</b>",
            reply_markup=back_button("admin_menu"),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка загрузки статистики: %s", e)
        await callback.answer("Ошибка загрузки статистики.", show_alert=True)
    await callback.answer()
