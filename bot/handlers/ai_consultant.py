"""
handlers/ai_consultant.py
-------------------------
AI-консультант: принимает запрос пользователя, передаёт в GPT-4o вместе
с актуальным каталогом и возвращает персональную рекомендацию.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.openai_api import get_ai_recommendation
from bot.handlers.catalog import main_reply_keyboard

logger = logging.getLogger(__name__)
router = Router()


class AIStates(StatesGroup):
    waiting_query = State()


# Тексты кнопок главного меню — не должны попадать в AI-обработчик
_MENU_TEXTS = frozenset({"Каталог 📦", "Подобрать товар 🤖", "Мои заказы 📋", "О магазине ℹ️"})


def recommended_products_keyboard(products: list) -> InlineKeyboardMarkup | None:
    """Инлайн-кнопки для товаров, упомянутых в ответе GPT."""
    if not products:
        return None
    buttons = [
        [InlineKeyboardButton(
            text=f"🛒 {p['name']}",
            callback_data=f"product_{p['id']}",
        )]
        for p in products
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Запуск: пользователь нажал «Подобрать товар 🤖» ─────────────────────────

@router.message(F.text == "Подобрать товар 🤖")
async def start_ai_consultant(message: Message, state: FSMContext):
    """Предлагает описать задачу и переводит в режим ожидания запроса."""
    await state.set_state(AIStates.waiting_query)
    await message.answer(
        "🤖 <b>AI-консультант GadgetPro</b>\n\n"
        "Опишите, что вам нужно — я подберу лучший вариант из нашего каталога.\n\n"
        "<i>Например:\n"
        "• нужен телефон для работы до 80 000 ₽\n"
        "• ищу планшет для ребёнка 10 лет\n"
        "• хочу ноутбук для дизайна, бюджет до 150 000 ₽</i>",
        parse_mode="HTML",
    )


# ─── Обработка запроса пользователя ──────────────────────────────────────────

@router.message(AIStates.waiting_query, F.text, ~F.text.in_(_MENU_TEXTS))
async def process_ai_query(message: Message, state: FSMContext, bot: Bot):
    """Отправляет запрос в GPT и показывает рекомендацию с кнопками товаров."""
    await state.clear()

    # Typing action пока ждём ответа
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        answer, products = await get_ai_recommendation(message.text)

        keyboard = recommended_products_keyboard(products)

        await message.answer(
            f"🤖 {answer}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        # Подсказка: можно задать ещё вопрос
        await message.answer(
            "Хотите уточнить или задать другой вопрос? Снова нажмите <b>«Подобрать товар 🤖»</b>",
            reply_markup=main_reply_keyboard(),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error("Ошибка AI-консультанта: %s", e)
        await message.answer(
            "Не удалось получить рекомендацию. Попробуйте позже или обратитесь к менеджеру.",
            reply_markup=main_reply_keyboard(),
        )
        await state.clear()
