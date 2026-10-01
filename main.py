"""Точка входа: middleware, роутеры, веб-сервер."""
import asyncio
import logging
import os
import traceback
from aiohttp import web
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode

from db import DB
from config import BOT_TOKEN, ADMIN_IDS
from core.globals import set_globals

from handlers import (
    admin as admin_handlers,
    daily_premium as daily_premium_handlers,
    premium as premium_handlers,
    start as start_handlers,
    profile as profile_handlers,
    travel as travel_handlers,
    combat as combat_handlers,
    shop as shop_handlers,
    inventory as inventory_handlers,
    pvp as pvp_handlers,
    craft as craft_handlers,
    guild as guild_handlers,
    quests as quests_handlers,
    pets as pets_handlers,
    world_events as world_events_handlers,
    misc as misc_handlers,
    skills as skills_handlers,
    use as use_handlers,
    trade as trade_handlers,
    journal as journal_handlers,
    world_boss as world_boss_handlers,
    onboarding as onboarding_handlers,
    chat as chat_handlers,
    titles as titles_handlers,
    ai_handler as ai_handler_handlers,
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()


# ================= MIDDLEWARE =================
class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Handler error: {e}\n{tb}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ <b>Ошибка</b>\n\n<code>{e}</code>\n\n<pre>{tb[-800:]}</pre>",
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


# Middleware — ДО роутеров
dp.message.middleware(ErrorMiddleware())
dp.callback_query.middleware(ErrorMiddleware())


# ================= РОУТЕРЫ =================
# Порядок важен!
# 1) Админ + конкретные команды
dp.include_router(admin_handlers.router)
dp.include_router(daily_premium_handlers.router)   # ← ТОЛЬКО /daily
dp.include_router(premium_handlers.router)          # ← новый /premium
dp.include_router(misc_handlers.router)
# 2) Старт и создание героя
dp.include_router(start_handlers.router)
dp.include_router(onboarding_handlers.router)
# 3) Игровые разделы
dp.include_router(profile_handlers.router)
dp.include_router(travel_handlers.router)
dp.include_router(combat_handlers.router)
dp.include_router(shop_handlers.router)
dp.include_router(inventory_handlers.router)
dp.include_router(pvp_handlers.router)
dp.include_router(craft_handlers.router)
dp.include_router(guild_handlers.router)
dp.include_router(quests_handlers.router)
dp.include_router(pets_handlers.router)
dp.include_router(world_events_handlers.router)
dp.include_router(skills_handlers.router)
dp.include_router(use_handlers.router)
dp.include_router(trade_handlers.router)
dp.include_router(chat_handlers.router)
dp.include_router(journal_handlers.router)
dp.include_router(world_boss_handlers.router)
dp.include_router(titles_handlers.router)
# 4) Catch-all — ОБЯЗАТЕЛЬНО ПОСЛЕДНИМ
dp.include_router(ai_handler_handlers.router)


# ================= ВЕБ-СЕРВЕР =================
async def handle_health(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logging.info(f"✅ Веб-сервер на порту {port}")


# ================= ЗАПУСК =================
async def _cleanup_loop():
    """Раз в 5 минут чистить мусор. Раз в час — спавн боссов."""
    from services.world_boss_service import try_spawn_boss
    tick = 0
    while True:
        try:
            await asyncio.sleep(300)
            await db.clean_dropped_items(30)
            await db.clean_expired_events()
            await db.cleanup_chat(7)
            await db.cleanup_journal(days=30, keep_min=50)
            await db.cleanup_location_events(days=7)

            tick += 1
            # Раз в час пробуем спавнить босса (каждые 12 тиков)
            if tick % 12 == 0:
                await db.cleanup_world_bosses(days=3)
                spawned = await try_spawn_boss()
                if spawned:
                    loc_name = spawned.get("location_name", "?")
                    boss_name = spawned.get("boss_name", "?")
                    # Broadcast всем игрокам
                    async with db.pool.acquire() as conn:
                        rows = await conn.fetch(
                            "SELECT user_id FROM users WHERE char_name!=''"
                        )
                    for r in rows:
                        try:
                            await bot.send_message(
                                r["user_id"],
                                f"🐉 <b>МИРОВОЙ БОСС!</b>\n\n"
                                f"<b>{boss_name}</b> появился в «{loc_name}»!\n\n"
                                f"<i>Иди в локацию и напиши /boss.</i>",
                                parse_mode=ParseMode.HTML
                            )
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"cleanup error: {e}")


async def main():
    await db.connect()
    set_globals(bot, db)
    await start_web_server()
    asyncio.create_task(_cleanup_loop())
    logging.info("🚀 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
