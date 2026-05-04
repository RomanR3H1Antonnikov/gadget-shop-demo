"""
handlers/catalog.py
-------------------
Обработчики каталога товаров.
Логика: категории → подкатегории → карточка товара.
Адаптируется под любой магазин — структура берётся из БД.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

from bot.config import SHOP_NAME
from bot.database import crud
from bot.keyboards.inline import (
    categories_keyboard,
    products_keyboard,
    product_detail_keyboard,
    back_button,
)

logger = logging.getLogger(__name__)
router = Router()


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню — всегда видна пользователю."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Каталог 📦"),       KeyboardButton(text="Подобрать товар 🤖")],
            [KeyboardButton(text="Мои заказы 📋"),    KeyboardButton(text="О магазине ℹ️")],
        ],
        resize_keyboard=True,
    )


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветственное сообщение с названием магазина из конфига."""
    await message.answer(
        f"👋 Добро пожаловать в <b>{SHOP_NAME}</b>!\n\n"
        "Здесь вы найдёте технику Apple, Samsung, Xiaomi и аксессуары по лучшим ценам.\n\n"
        "🤖 Не знаете, что выбрать? Наш AI-консультант поможет за секунды.\n\n"
        "Выберите, с чего начать:",
        reply_markup=main_reply_keyboard(),
        parse_mode="HTML",
    )


# ─── Главное меню — кнопка «Каталог» ─────────────────────────────────────────

@router.message(F.text == "Каталог 📦")
async def show_catalog(message: Message):
    """Показывает корневые категории."""
    try:
        categories = await crud.get_root_categories()
        if not categories:
            await message.answer("Каталог пока пуст. Загляните позже!")
            return
        await message.answer(
            "📦 <b>Каталог товаров</b>\n\nВыберите категорию:",
            reply_markup=categories_keyboard(categories),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка загрузки каталога: %s", e)
        await message.answer("Не удалось загрузить каталог. Попробуйте позже.")


# ─── О магазине ───────────────────────────────────────────────────────────────

@router.message(F.text == "О магазине ℹ️")
async def about_shop(message: Message):
    await message.answer(
        f"ℹ️ <b>{SHOP_NAME}</b>\n\n"
        "Магазин электроники — техника Apple, Samsung, Xiaomi, аксессуары и Trade-in.\n\n"
        "📍 Работаем ежедневно 10:00–21:00\n"
        "📞 Для связи нажмите <b>«Подобрать товар 🤖»</b> или оформите заказ из каталога.",
        parse_mode="HTML",
    )


# ─── Навигация по категориям ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_"))
async def open_category(callback: CallbackQuery):
    """
    Открывает категорию.
    Если есть подкатегории — показывает их.
    Если нет — показывает товары.
    """
    category_id = int(callback.data.split("_")[1])

    try:
        category = await crud.get_category(category_id)
        if not category:
            await callback.answer("Категория не найдена.", show_alert=True)
            return

        # Проверяем — Trade-in (нет подкатегорий и нет обычных товаров)
        subcategories = await crud.get_subcategories(category_id)

        parent_id = category.get("parent_id")
        # Назад из подкатегорий/товаров ведёт к родителю или в главное меню
        back_cb = f"cat_{parent_id}" if parent_id else "back_to_main"

        if subcategories:
            # Показываем подкатегории + кнопка Назад
            await callback.message.edit_text(
                f"{category['emoji']} <b>{category['name']}</b>\n\nВыберите подкатегорию:",
                reply_markup=categories_keyboard(subcategories, back_callback=back_cb),
                parse_mode="HTML",
            )
        else:
            # Показываем товары
            products = await crud.get_products_by_category(category_id)
            if not products:
                # Для Trade-in и пустых категорий
                await callback.message.edit_text(
                    f"{category['emoji']} <b>{category['name']}</b>\n\n"
                    "В этой категории пока нет товаров. Свяжитесь с менеджером.",
                    reply_markup=back_button(back_cb),
                    parse_mode="HTML",
                )
            else:
                await callback.message.edit_text(
                    f"{category['emoji']} <b>{category['name']}</b>\n\nВыберите товар:",
                    reply_markup=products_keyboard(products, category_id, parent_id=parent_id),
                    parse_mode="HTML",
                )

    except Exception as e:
        logger.error("Ошибка открытия категории %d: %s", category_id, e)
        await callback.answer("Ошибка загрузки. Попробуйте снова.", show_alert=True)

    await callback.answer()


# ─── Карточка товара ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("product_"))
async def open_product(callback: CallbackQuery):
    """Показывает карточку товара с описанием, ценой и кнопкой заказа."""
    product_id = int(callback.data.split("_")[1])

    try:
        product = await crud.get_product(product_id)
        if not product:
            await callback.answer("Товар не найден.", show_alert=True)
            return

        stock_text = "✅ В наличии" if product["in_stock"] else "❌ Нет в наличии"
        price_text = f"{product['price']:,} ₽".replace(",", " ") if product["price"] else "Уточните у менеджера"
        text = (
            f"<b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: <b>{price_text}</b>\n"
            f"{stock_text}"
        )

        keyboard = product_detail_keyboard(product["id"], product["category_id"])

        if product.get("photo_url"):
            # Удаляем старое сообщение и отправляем фото (edit_media сложнее, используем delete+send)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=product["photo_url"],
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error("Ошибка открытия товара %d: %s", product_id, e)
        await callback.answer("Ошибка загрузки. Попробуйте снова.", show_alert=True)

    await callback.answer()


# ─── Кнопки «Назад» ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("back_to_cat_"))
async def back_to_category(callback: CallbackQuery):
    """Возврат в категорию (может прийти после карточки с фото — нужен answer вместо edit)."""
    category_id = int(callback.data.split("_")[-1])

    try:
        category = await crud.get_category(category_id)
        if not category:
            await callback.answer("Категория не найдена.", show_alert=True)
            return

        parent_id = category.get("parent_id")
        back_cb = f"cat_{parent_id}" if parent_id else "back_to_main"

        subcategories = await crud.get_subcategories(category_id)
        if subcategories:
            text = f"{category['emoji']} <b>{category['name']}</b>\n\nВыберите подкатегорию:"
            markup = categories_keyboard(subcategories, back_callback=back_cb)
        else:
            products = await crud.get_products_by_category(category_id)
            text = f"{category['emoji']} <b>{category['name']}</b>\n\nВыберите товар:"
            markup = products_keyboard(products, category_id, parent_id=parent_id)

        # Пробуем edit; если сообщение с фото — удаляем и шлём новое
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        logger.error("Ошибка возврата в категорию %d: %s", category_id, e)
        await callback.answer("Ошибка. Попробуйте снова.", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню — показываем корневые категории."""
    try:
        categories = await crud.get_root_categories()
        try:
            await callback.message.edit_text(
                "📦 <b>Каталог товаров</b>\n\nВыберите категорию:",
                reply_markup=categories_keyboard(categories),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                "📦 <b>Каталог товаров</b>\n\nВыберите категорию:",
                reply_markup=categories_keyboard(categories),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error("Ошибка возврата в главное меню: %s", e)

    await callback.answer()
