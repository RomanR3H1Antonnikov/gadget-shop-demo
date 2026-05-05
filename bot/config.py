"""
config.py
---------
Загрузка переменных окружения из .env.
Все константы проекта — только здесь.
"""

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHOP_NAME = os.getenv("SHOP_NAME", "GadgetPro")
DB_PATH = os.getenv("DB_PATH", "bot.db")
