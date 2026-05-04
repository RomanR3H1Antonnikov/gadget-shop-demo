"""
database/crud.py
----------------
Все асинхронные операции с БД.
Каждая функция — атомарная операция, не знает о боте или handlers.
"""

import aiosqlite
from bot.config import DB_PATH


# ─── Категории ────────────────────────────────────────────────────────────────

async def get_root_categories() -> list[dict]:
    """Возвращает корневые категории (parent_id IS NULL)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_subcategories(parent_id: int) -> list[dict]:
    """Возвращает подкатегории для заданного parent_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE parent_id = ? ORDER BY sort_order",
            (parent_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_category(category_id: int) -> dict | None:
    """Возвращает категорию по id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def has_subcategories(category_id: int) -> bool:
    """Проверяет, есть ли у категории подкатегории."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM categories WHERE parent_id = ?", (category_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            return count > 0


# ─── Товары ───────────────────────────────────────────────────────────────────

async def get_products_by_category(category_id: int) -> list[dict]:
    """Возвращает видимые товары в наличии для категории."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category_id = ? AND is_hidden = 0 ORDER BY id",
            (category_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_product(product_id: int) -> dict | None:
    """Возвращает товар по id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_products_for_ai() -> list[dict]:
    """Возвращает все активные товары для передачи в AI-консультант."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, description, price FROM products WHERE in_stock = 1 AND is_hidden = 0"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_all_products_admin(offset: int = 0, limit: int = 10) -> list[dict]:
    """Возвращает все товары для админки с пагинацией."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, c.name as category_name FROM products p "
            "JOIN categories c ON p.category_id = c.id "
            "ORDER BY p.id LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def toggle_product_visibility(product_id: int):
    """Переключает видимость товара (is_hidden)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE products SET is_hidden = NOT is_hidden WHERE id = ?",
            (product_id,)
        )
        await db.commit()


async def add_product(category_id: int, name: str, description: str,
                      price: int, photo_url: str | None) -> int:
    """Добавляет новый товар, возвращает его id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO products (category_id, name, description, price, photo_url) "
            "VALUES (?, ?, ?, ?, ?)",
            (category_id, name, description, price, photo_url)
        )
        await db.commit()
        return cursor.lastrowid


# ─── Заказы ───────────────────────────────────────────────────────────────────

async def create_order(user_id: int, username: str | None, product_id: int,
                       customer_name: str, phone: str, delivery: str) -> int:
    """Создаёт заказ, возвращает его id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, username, product_id, customer_name, phone, delivery) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, product_id, customer_name, phone, delivery)
        )
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id: int) -> dict | None:
    """Возвращает заказ со сведениями о товаре."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT o.*, p.name as product_name, p.price as product_price "
            "FROM orders o JOIN products p ON o.product_id = p.id "
            "WHERE o.id = ?",
            (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_order_status(order_id: int, status: str):
    """Обновляет статус заказа: new / confirmed / done / cancelled."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
        await db.commit()


async def get_recent_orders(limit: int = 20) -> list[dict]:
    """Возвращает последние N заказов для админки."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT o.*, p.name as product_name FROM orders o "
            "JOIN products p ON o.product_id = p.id "
            "ORDER BY o.created_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_user_orders(user_id: int) -> list[dict]:
    """Возвращает заказы конкретного пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT o.*, p.name as product_name, p.price as product_price "
            "FROM orders o JOIN products p ON o.product_id = p.id "
            "WHERE o.user_id = ? ORDER BY o.created_at DESC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─── Статистика ───────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    """Возвращает статистику для админки."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(p.price), 0), COUNT(DISTINCT o.user_id) "
            "FROM orders o JOIN products p ON o.product_id = p.id "
            "WHERE DATE(o.created_at) = DATE('now')"
        ) as cursor:
            today = await cursor.fetchone()

        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            total = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT p.name, COUNT(*) as cnt FROM orders o "
            "JOIN products p ON o.product_id = p.id "
            "GROUP BY o.product_id ORDER BY cnt DESC LIMIT 1"
        ) as cursor:
            top = await cursor.fetchone()

        return {
            "today_orders": today[0],
            "today_sum": today[1],
            "today_users": today[2],
            "total_orders": total,
            "top_product": top[0] if top else "—",
        }
