"""
handlers/orders.py
------------------
FSM-приём заказов: имя → телефон → доставка → сохранение.
После оформления уведомляет пользователя и отправляет заявку администратору.
Обрабатывает кнопки подтверждения / отклонения заказа от администратора.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import ADMIN_CHAT_ID
from bot.database import crud
from bot.keyboards.inline import order_confirmation_keyboard
from bot.handlers.catalog import main_reply_keyboard

logger = logging.getLogger(__name__)
router = Router()


class OrderStates(StatesGroup):
    waiting_name     = State()
    waiting_phone    = State()
    waiting_delivery = State()


def phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой «Поделиться контактом» для шага ввода телефона."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="❌ Отменить заказ")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены во время FSM."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить заказ")]],
        resize_keyboard=True,
    )


# ─── Запуск FSM по кнопке «Заказать» ─────────────────────────────────────────

@router.callback_query(F.data.startswith("order_"))
async def start_order(callback: CallbackQuery, state: FSMContext):
    """Инициирует оформление заказа — запрашивает имя покупателя."""
    product_id = int(callback.data.split("_")[1])

    try:
        product = await crud.get_product(product_id)
        if not product:
            await callback.answer("Товар не найден.", show_alert=True)
            return

        # Сохраняем product_id и название в состояние для последующих шагов
        await state.set_state(OrderStates.waiting_name)
        await state.update_data(product_id=product_id, product_name=product["name"])

        await callback.message.answer(
            f"🛒 Оформляем заказ: <b>{product['name']}</b>\n\n"
            "Как вас зовут? Введите имя:",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка старта заказа товара %d: %s", product_id, e)
        await callback.answer("Ошибка. Попробуйте снова.", show_alert=True)

    await callback.answer()


# ─── Отмена заказа в любом состоянии ─────────────────────────────────────────

@router.message(F.text == "❌ Отменить заказ")
async def cancel_order_fsm(message: Message, state: FSMContext):
    """Сбрасывает FSM и возвращает главное меню."""
    await state.clear()
    await message.answer(
        "Заказ отменён.",
        reply_markup=main_reply_keyboard(),
    )


# ─── Шаг 1: имя ───────────────────────────────────────────────────────────────

@router.message(OrderStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    """Принимает имя, переходит к запросу телефона."""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите настоящее имя (минимум 2 символа):")
        return

    await state.update_data(customer_name=name)
    await state.set_state(OrderStates.waiting_phone)

    await message.answer(
        f"Отлично, <b>{name}</b>! 👋\n\n"
        "Введите номер телефона или нажмите кнопку ниже:",
        reply_markup=phone_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 2: телефон (текст или контакт) ──────────────────────────────────────

@router.message(OrderStates.waiting_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Принимает телефон через кнопку «Поделиться контактом»."""
    phone = message.contact.phone_number
    # Нормализуем: убираем пробелы и приводим к формату +7
    if phone.startswith("7") and not phone.startswith("+"):
        phone = "+" + phone
    await _ask_delivery(message, state, phone)


@router.message(OrderStates.waiting_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Принимает телефон текстом — базовая проверка формата."""
    raw = message.text.strip()
    # Оставляем только цифры для проверки длины
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) < 10:
        await message.answer(
            "Номер слишком короткий. Введите полный номер, например: +7 999 123-45-67"
        )
        return
    await _ask_delivery(message, state, raw)


async def _ask_delivery(message: Message, state: FSMContext, phone: str):
    """Общая логика после получения телефона — запрашивает способ доставки."""
    await state.update_data(phone=phone)
    await state.set_state(OrderStates.waiting_delivery)

    await message.answer(
        "Укажите способ доставки:\n"
        "• Напишите <b>«самовывоз»</b>\n"
        "• Или укажите <b>город</b> для доставки курьером",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


# ─── Шаг 3: доставка → сохранение заказа ─────────────────────────────────────

@router.message(OrderStates.waiting_delivery)
async def process_delivery(message: Message, state: FSMContext, bot: Bot):
    """Принимает способ доставки, сохраняет заказ и уведомляет стороны."""
    delivery = message.text.strip()
    if len(delivery) < 2:
        await message.answer("Введите город или слово «самовывоз»:")
        return

    data = await state.get_data()
    await state.clear()

    try:
        order_id = await crud.create_order(
            user_id=message.from_user.id,
            username=message.from_user.username,
            product_id=data["product_id"],
            customer_name=data["customer_name"],
            phone=data["phone"],
            delivery=delivery,
        )

        product = await crud.get_product(data["product_id"])
        price_text = f"{product['price']:,} ₽".replace(",", " ") if product["price"] else "—"

        # ── Подтверждение пользователю ──
        await message.answer(
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"📦 Товар: {data['product_name']}\n"
            f"👤 Имя: {data['customer_name']}\n"
            f"📞 Телефон: {data['phone']}\n"
            f"🚚 Доставка: {delivery}\n\n"
            "Менеджер свяжется с вами в течение 1 часа.",
            reply_markup=main_reply_keyboard(),
            parse_mode="HTML",
        )

        # ── Уведомление администратору ──
        username_str = f"@{message.from_user.username}" if message.from_user.username else "без username"
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
                f"📦 {data['product_name']} ({price_text})\n"
                f"👤 {data['customer_name']} | {username_str}\n"
                f"📞 {data['phone']}\n"
                f"🚚 {delivery}"
            ),
            reply_markup=order_confirmation_keyboard(order_id),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error("Ошибка сохранения заказа: %s", e)
        await message.answer(
            "Не удалось сохранить заказ. Попробуйте снова или свяжитесь с менеджером.",
            reply_markup=main_reply_keyboard(),
        )


# ─── Кнопки подтверждения / отклонения (для администратора) ──────────────────

@router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order(callback: CallbackQuery, bot: Bot):
    """Администратор подтверждает заказ — статус → confirmed, уведомляет клиента."""
    order_id = int(callback.data.split("_")[-1])

    try:
        order = await crud.get_order(order_id)
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        await crud.update_order_status(order_id, "confirmed")

        # Уведомляем клиента
        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"✅ <b>Заказ #{order_id} подтверждён!</b>\n\n"
                f"📦 {order['product_name']}\n\n"
                "Менеджер свяжется с вами для уточнения деталей."
            ),
            parse_mode="HTML",
        )

        # Редактируем сообщение у администратора
        await callback.message.edit_text(
            callback.message.text + "\n\n<b>✅ Подтверждён</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка подтверждения заказа %d: %s", order_id, e)
        await callback.answer("Ошибка. Попробуйте снова.", show_alert=True)

    await callback.answer("Заказ подтверждён!")


@router.callback_query(F.data.startswith("cancel_order_"))
async def reject_order(callback: CallbackQuery, bot: Bot):
    """Администратор отклоняет заказ — статус → cancelled, уведомляет клиента."""
    order_id = int(callback.data.split("_")[-1])

    try:
        order = await crud.get_order(order_id)
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        await crud.update_order_status(order_id, "cancelled")

        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ <b>Заказ #{order_id} отклонён.</b>\n\n"
                "Если у вас есть вопросы — напишите нам через раздел «О магазине»."
            ),
            parse_mode="HTML",
        )

        await callback.message.edit_text(
            callback.message.text + "\n\n<b>❌ Отклонён</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка отклонения заказа %d: %s", order_id, e)
        await callback.answer("Ошибка. Попробуйте снова.", show_alert=True)

    await callback.answer("Заказ отклонён.")
