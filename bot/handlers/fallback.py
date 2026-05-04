"""
handlers/fallback.py
--------------------
Ловит любые сообщения, не обработанные другими роутерами.
Регистрируется последним в main.py — срабатывает только когда
пользователь не в FSM-состоянии и ни одна другая команда не подошла.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state

from bot.config import SHOP_NAME
from bot.handlers.catalog import main_reply_keyboard

router = Router()


@router.message(StateFilter(default_state), F.text)
async def fallback_text(message: Message):
    """Ответ на любое непредвиденное текстовое сообщение."""
    await message.answer(
        f"👋 Я бот магазина <b>{SHOP_NAME}</b>. Вот что я умею:\n\n"
        "📦 <b>Каталог</b> — смотреть товары и оформлять заказы\n"
        "🤖 <b>Подобрать товар</b> — AI-консультант подберёт по задаче и бюджету\n"
        "📋 <b>Мои заказы</b> — история ваших заявок\n"
        "ℹ️ <b>О магазине</b> — адрес и режим работы\n\n"
        "Воспользуйтесь кнопками меню ниже 👇",
        reply_markup=main_reply_keyboard(),
        parse_mode="HTML",
    )
