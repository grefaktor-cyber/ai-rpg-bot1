import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice)
from aiogram.enums import ParseMode

from db import DB
import ai
from config import (BOT_TOKEN, GIGACHAT_CREDENTIALS,
                    FREE_DAILY_LIMIT, PREMIUM_PRICE_STARS, AI_MARKER)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

CONSENT_TEXT = (
    "📋 <b>Перед началом — важное</b>\n\n"
    "Бот обрабатывает ваши данные (Telegram ID, username) для сохранения прогресса.\n\n"
    "• Данные хранятся в РФ.\n"
    "• Контент сгенерирован ИИ и маркируется.\n"
    "• Игра для лиц <b>18+</b>.\n"
    "• Отозвать согласие → /revoke.\n\n"
    "Нажимая «Согласен», вы подтверждаете согласие и возраст 18+."
)

@dp.message(Command("start"))
async def start(m: Message):
    args = m.text.split()
    referrer_id = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = await db.get_user(m.from_user.id, m.from_user.username or "")

    if referrer_id and user["referred_by"] == 0:
        if await db.set_referrer(m.from_user.id, referrer_id):
            await m.answer("🎉 Вы пришли по приглашению! Ваш друг получил +10 действий.")
            try:
                await bot.send_message(referrer_id,
                    "🎉 По вашей ссылке пришёл новый игрок! Вам начислено +10 действий.")
            except Exception:
                pass

    if user["consent_given"]:
        me = await bot.get_me()
        ref_link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"
        await m.answer(
            f"🎮 С возвращением!\n\n"
            f"⭐ Уровень: {user['level']} · XP: {user['xp']}\n"
            f"📍 Локация: {user['location']}\n\n"
            f"🔗 Ваша ссылка: {ref_link}\n"
            f"👥 Приглашено: {user['referral_count']}\n\n"
            f"Команды: /inventory /map /stats /daily /buy"
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Согласен (18+)", callback_data="consent_yes"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no"),
    ]])
    await m.answer(CONSENT_TEXT, reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await db.give_consent(c.from_user.id)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{c.from_user.id}"
    await c.message.edit_text(
        "✅ Согласие получено. Добро пожаловать в <b>AI-Приключение</b>!\n\n"
        "Просто пиши, что делает герой.\n\n"
        f"📊 Бесплатно: {FREE_DAILY_LIMIT} действий в день.\n"
        f"🔗 Ваша ссылка: {ref_link}\n"
        f"За друга — +10 действий!\n\n"
        f"💎 /buy · 🎁 /daily · 🎒 /inventory\n"
        f"{AI_MARKER}",
        parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс. Вернуться — /start.")

@dp.message(Command("revoke"))
async def revoke(m: Message):
    await db.revoke_consent(m.from_user.id)
    await m.answer("🗑 Согласие отозвано, история удалена. Вернуться — /start.")

@dp.message(Command("reset"))
async def reset(m: Message):
    await db.update_story(m.from_user.id, "")
    await m.answer("🔄 История сброшена.")

@dp.message(Command("inventory"))
async def inventory(m: Message):
    items = await db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст. Исследуй мир — найдёшь что-нибудь!")
        return
    lst = "\n".join(f"• {i}" for i in items)
    await m.answer(f"🎒 <b>Инвентарь</b>\n\n{lst}", parse_mode=ParseMode.HTML)

@dp.message(Command("map"))
async def map_cmd(m: Message):
    locs = await db.get_locations(m.from_user.id)
    if not locs:
        await m.answer("🗺 Вы пока нигде не были. Начните приключение!")
        return
    lst = "\n".join(f"📍 {l}" for l in locs)
    await m.answer(f"🗺 <b>Карта путешествий</b>\n\n{lst}", parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
async def stats(m: Message):
    u = await db.get_user(m.from_user.id)
    need = u["level"] * u["level"] * 100
    await m.answer(
        f"⭐ <b>Статистика</b>\n\n"
        f"Уровень: {u['level']}\n"
        f"XP: {u['xp']} / {need}\n"
        f"Действий всего: {u['action_count']}\n"
        f"Локация: {u['location']}\n"
        f"Премиум: {'✅' if u['is_premium'] else '❌'}",
        parse_mode=ParseMode.HTML)

@dp.message(Command("daily"))
async def daily(m: Message):
    streak = await db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer("🎁 Вы уже получали награду сегодня. Возвращайтесь завтра!")
        return
    bonus = {1:5, 2:5, 3:10, 4:10, 5:15, 6:15, 7:30}.get(streak, 10)
    msg = f"🎁 <b>Ежедневная награда!</b>\n\nДень {streak} подряд\n+{bonus} действий"
    if streak == 7:
        await db.add_item(m.from_user.id, "Редкий амулет удачи")
        msg += "\n\n🏆 <b>Бонус за 7 дней:</b> Редкий амулет удачи добавлен в инвентарь!"
        await db.claim_daily  # сбросим streak — оставляем простым
    await m.answer(msg, parse_mode=ParseMode.HTML)

@dp.message(Command("premium"))
async def premium(m: Message):
    await m.answer("💎 Премиум — безлимит действий. Купить → /buy", parse_mode=ParseMode.HTML)

@dp.message(Command("buy"))
async def buy(m: Message):
    await bot.send_invoice(
        chat_id=m.chat.id,
        title="Премиум-подписка AI-Приключение",
        description="Безлимитные действия, приоритетная обработка",
        payload="premium_30d", provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium")

@dp.pre_checkout_query()
async def pre_checkout(q):
    await q.answer(ok=True)

@dp.message(F.successful_payment)
async def on_payment(m: Message):
    await db.set_premium(m.from_user.id, 1)
    await m.answer("💎 <b>Оплата получена!</b> Премиум активирован на 30 дней.", parse_mode=ParseMode.HTML)

@dp.message(F.text)
async def handle(m: Message):
    uid = m.from_user.id
    user = await db.get_user(uid, m.from_user.username or "")

    if not user["consent_given"]:
        await m.answer("⚠️ Сначала примите условия: /start")
        return

    if not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит исчерпан ({FREE_DAILY_LIMIT} действий).\n\n"
            "💎 /buy — безлимит\n👥 Пригласи друга — +10\n🎁 /daily — ежедневный бонус"
        )
        return

    await bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]
    result = await ai.generate(user["story"], action, user["arc"])
    response = result["text"]

    if result["item"]:
        await db.add_item(uid, result["item"])
        response += f"\n\n🎒 <i>Получен предмет: {result['item']}</i>"

    if result["location"]:
        await db.add_location(uid, result["location"])
        response += f"\n\n📍 <i>Новая локация: {result['location']}</i>"

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    await db.update_story(uid, new_story)
    await db.increment(uid)
    await db.incr_action_count(uid)

    level, xp, leveled_up = await db.add_xp(uid, 10)
    if leveled_up:
        response += f"\n\n⭐ <b>Уровень повышен! Теперь вы уровня {level}.</b>"

    left = "∞" if user["is_premium"] else FREE_DAILY_LIMIT - user["requests_today"] - 1
    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · Осталось: {left}</i>",
        parse_mode=ParseMode.HTML)

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

async def main():
    await db.connect()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
