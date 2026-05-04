"""
handlers/my_orders.py
---------------------
История заказов пользователя.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from bot.database import crud

logger = logging.getLogger(__name__)
router = Router()

STATUS_EMOJI = {
    "new":       "🕐 Новый",
    "confirmed": "✅ Подтверждён",
    "done":      "📦 Выполнен",
    "cancelled": "❌ Отменён",
}


@router.message(F.text == "Мои заказы 📋")
async def my_orders(message: Message):
    """Показывает последние заказы пользователя."""
    try:
        orders = await crud.get_user_orders(message.from_user.id)
        if not orders:
            await message.answer(
                "У вас пока нет заказов.\n\nОткройте <b>Каталог 📦</b> и выберите товар!",
                parse_mode="HTML",
            )
            return

        lines = ["📋 <b>Ваши заказы:</b>\n"]
        for o in orders[:10]:  # показываем последние 10
            status = STATUS_EMOJI.get(o["status"], o["status"])
            price = f"{o['product_price']:,} ₽".replace(",", " ")
            lines.append(
                f"<b>#{o['id']}</b> {o['product_name']} — {price}\n"
                f"    {status} · {o['created_at'][:10]}"
            )

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error("Ошибка загрузки заказов пользователя %d: %s", message.from_user.id, e)
        await message.answer("Не удалось загрузить заказы. Попробуйте позже.")
