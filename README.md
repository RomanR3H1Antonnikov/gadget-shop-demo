# GadgetPro — Telegram-бот для магазина электроники

Демо-продукт IT-студии. Показывает владельцу магазина, как будет выглядеть его собственный бот.

**Демо-магазин:** техника Apple, Samsung, аксессуары, Trade-in.

---

## Возможности

- **Каталог товаров** — категории, подкатегории, карточки с фото и ценами
- **Оформление заказа** — FSM-диалог: имя → телефон → доставка
- **Уведомления администратору** — новый заказ с кнопками «Подтвердить / Отклонить»
- **AI-консультант** — подбирает товар по описанию задачи и бюджету (GPT-4o)
- **Админ-панель** — заказы, управление товарами, статистика

---

## Стек

| | |
|---|---|
| Python | 3.11+ |
| Telegram | aiogram 3.x |
| База данных | SQLite (aiosqlite) |
| AI | OpenAI GPT-4o |

---

## Быстрый старт

```bash
git clone https://github.com/RomanR3H1Antonnikov/gadget-shop-demo.git
cd gadget-shop-demo

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

cp bot/.env.example bot/.env
# Заполни bot/.env своими токенами

python bot/data/seed.py       # Заполнить БД тестовыми товарами
python bot/main.py            # Запустить бота
```

---

## Конфигурация

Скопируй `bot/.env.example` в `bot/.env` и заполни:

```env
BOT_TOKEN=       # Токен от @BotFather
ADMIN_CHAT_ID=   # Твой Telegram chat_id
OPENAI_API_KEY=  # Ключ OpenAI (для AI-консультанта)
SHOP_NAME=       # Название магазина (отображается в приветствии)
DB_PATH=bot.db
```

---

## Структура проекта

```
bot/
├── main.py                  # Точка входа
├── config.py                # Загрузка .env
├── database/
│   ├── models.py            # Схема БД
│   └── crud.py              # Операции с данными
├── handlers/
│   ├── catalog.py           # Каталог товаров
│   ├── orders.py            # Заказы (FSM)
│   ├── ai_consultant.py     # AI-консультант
│   ├── admin.py             # Админ-панель
│   └── my_orders.py         # История заказов пользователя
├── keyboards/
│   └── inline.py            # Инлайн-клавиатуры
├── services/
│   └── openai_api.py        # Обёртка OpenAI API
└── data/
    └── seed.py              # Тестовые данные (15 товаров)
```

---

## Адаптация под свой магазин

Бот не содержит хардкода — весь контент берётся из БД и `.env`:

1. Поменяй `SHOP_NAME` в `.env`
2. Отредактируй `seed.py` под свои категории и товары
3. Запусти `seed.py` на новой БД
4. Запусти бота — готово

---

*Разработано как демо IT-студии. Хочешь такой же бот для своего магазина? Напиши нам.*
