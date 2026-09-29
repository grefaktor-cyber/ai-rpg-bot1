import asyncio
import logging
import os
import traceback
from aiohttp import web
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_IDS
from db import DB

logging.basicConfig(level=logging.INFO)

# ================= БОТ И ДИСПЕТЧЕР =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

# Глобальный доступ для хендлеров
dp["bot"] = bot
dp["db"] = db


# ================= MIDDLEWARE ОШИБОК =================
class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            err_name = type(e).__name__
            # Сетевые ошибки — игнорируем
            if err_name in (
                "TelegramNetworkError", "TelegramRetryAfter",
                "TelegramConflictError", "ClientOSError",
                "ClientConnectionError", "TimeoutError",
                "ServerDisconnectedError", "ClientConnectorError",
            ):
                logging.warning(f"Сетевая ошибка (игнорируем): {err_name}: {e}")
                return

            tb = traceback.format_exc()
            logging.error(f"Handler error: {e}\n{tb}")

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ <b>Ошибка</b>\n\n<code>{e}</code>\n\n"
                        f"<pre>{tb[-800:]}</pre>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

            try:
                if hasattr(event, "message") and event.message:
                    await event.message.answer("⚠️ Произошла ошибка. Уже чиним!")
                elif hasattr(event, "answer"):
                    await event.answer("⚠️ Ошибка. Уже чиним!", show_alert=True)
            except Exception:
                pass


# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
async def handle_health(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logging.info(f"✅ Веб-сервер запущен на порту {port}")


# ================= РЕГИСТРАЦИЯ РОУТЕРОВ =================
def register_routers():
    """Регистрация всех роутеров. Пока — только старый bot.py-логика."""
    # Этот блок заменим по мере переноса хендлеров
    pass


# ================= ЗАПУСК =================
async def main():
    await db.connect()
    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())

    register_routers()

    await start_web_server()
    logging.info("🚀 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
