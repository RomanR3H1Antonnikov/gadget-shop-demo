"""
database/models.py
------------------
Инициализация БД и создание таблиц.
Вызывается один раз при старте бота.
"""

import aiosqlite
from bot.config import DB_PATH


async def init_db():
    """Создаёт все таблицы, если они ещё не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                parent_id   INTEGER NULL REFERENCES categories(id),
                emoji       TEXT    NOT NULL DEFAULT '',
                sort_order  INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                name        TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                price       INTEGER NOT NULL,
                photo_url   TEXT    NULL,
                in_stock    BOOLEAN NOT NULL DEFAULT 1,
                is_hidden   BOOLEAN NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id            INTEGER  PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER  NOT NULL,
                username      TEXT     NULL,
                product_id    INTEGER  NOT NULL REFERENCES products(id),
                customer_name TEXT     NOT NULL,
                phone         TEXT     NOT NULL,
                delivery      TEXT     NOT NULL,
                status        TEXT     NOT NULL DEFAULT 'new',
                created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()
