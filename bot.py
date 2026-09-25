import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice)
from aiogram.enums import ParseMode

from config import (BOT_TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID,
                    FREE_DAILY_LIMIT, PREMIUM_PRICE_STARS, AI_MARKER)
from db import DB
import ai

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

# --- ТУТ ВЕСЬ ТВОЙ КОД С ХЕНДЛЕРАМИ (start, consent, buy и т.д.) ---
# ... (оставь его без изменений, как было в предыдущем сообщении) ...

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle_health(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Веб-сервер запущен на порту {port}")

# --- ЗАПУСК ---
async def main():
    await start_web_server()  # Сначала поднимаем веб-сервер, чтобы Render увидел порт
    await dp.start_polling(bot) # Затем запускаем бота

if __name__ == "__main__":
    asyncio.run(main())
