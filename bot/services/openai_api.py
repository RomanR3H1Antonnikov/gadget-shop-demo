"""
services/openai_api.py
----------------------
Обёртка над OpenAI API для AI-консультанта магазина.
Получает каталог из БД, формирует системный промпт и возвращает ответ GPT.
"""

import json
import logging
from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY, SHOP_NAME
from bot.database import crud

logger = logging.getLogger(__name__)

# Клиент создаётся при первом запросе — к этому моменту .env уже загружен
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """
Ты — опытный продавец-консультант магазина {shop_name}.
Твоя задача — помочь покупателю выбрать идеальный товар.

Текущий каталог магазина (только товары в наличии):
{catalog_json}

Правила:
1. Рекомендуй ТОЛЬКО товары из каталога выше
2. Будь конкретным: называй точное название модели и цену
3. Объясняй, почему именно этот товар подойдёт для задачи покупателя
4. Если бюджет не указан — спроси
5. Отвечай дружелюбно, без канцелярита
6. Максимум 3 рекомендации за раз
7. В конце предложи нажать «Заказать» под понравившимся товаром
""".strip()


async def get_ai_recommendation(user_query: str) -> tuple[str, list[dict]]:
    """
    Запрашивает рекомендацию у GPT-4o.
    Возвращает (текст_ответа, список_рекомендованных_товаров).
    Товары определяются по совпадению названий в ответе GPT с каталогом.
    """
    products = await crud.get_all_products_for_ai()

    # Формируем компактный JSON каталога для промпта
    catalog_json = json.dumps(
        [{"id": p["id"], "name": p["name"], "price": p["price"]} for p in products],
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = SYSTEM_PROMPT.format(
        shop_name=SHOP_NAME,
        catalog_json=catalog_json,
    )

    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_query},
        ],
        max_tokens=1024,
        temperature=0.7,
    )

    answer = response.choices[0].message.content.strip()

    # Ищем упомянутые товары: проверяем, есть ли название товара в тексте ответа
    mentioned = []
    answer_lower = answer.lower()
    for p in products:
        # Берём первые значимые слова названия для поиска (например "iPhone 15 Pro")
        key = p["name"].lower()
        if key in answer_lower:
            mentioned.append(p)
        if len(mentioned) == 3:
            break

    return answer, mentioned
