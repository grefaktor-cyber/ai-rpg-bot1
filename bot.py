import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice, ReplyKeyboardMarkup,
                           KeyboardButton)
from aiogram.enums import ParseMode

from db import DB
import ai
from config import (BOT_TOKEN, GIGACHAT_CREDENTIALS,
                    FREE_DAILY_LIMIT, PREMIUM_PRICE_STARS, AI_MARKER)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

# === Справочники ===
RACES = {
    "human":    {"name": "Человек",     "desc": "Универсал. Равен во всём.",
                 "stats": {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5}},
    "elf":      {"name": "Эльф",        "desc": "Ловкий, мудрый, но хрупкий.",
                 "stats": {"str": 4, "dex": 6, "con": 4, "int": 6, "wit": 6, "men": 5}},
    "dark_elf": {"name": "Тёмный эльф", "desc": "Сильная магия, слабая защита.",
                 "stats": {"str": 5, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 4}},
    "orc":      {"name": "Орк",         "desc": "Могучий воин, слаб в магии.",
                 "stats": {"str": 7, "dex": 4, "con": 7, "int": 3, "wit": 4, "men": 3}},
    "dwarf":    {"name": "Гном",        "desc": "Выносливый, крепкий.",
                 "stats": {"str": 6, "dex": 4, "con": 7, "int": 4, "wit": 4, "men": 5}},
}

CLASSES = {
    "warrior": {"name": "Воин",   "desc": "Мастер меча и щита.", "bonus": {"str": 3, "con": 2}},
    "mage":    {"name": "Маг",    "desc": "Повелитель стихий.",  "bonus": {"int": 3, "wit": 2}},
    "archer":  {"name": "Лучник", "desc": "Стрелок и следопыт.", "bonus": {"dex": 3, "str": 2}},
    "priest":  {"name": "Жрец",   "desc": "Целитель и дипломат.","bonus": {"men": 3, "wit": 2}},
}

ACHIEVEMENTS = {
    "first_step":  "🌟 Первый шаг — сделал первое действие",
    "explorer_5":  "🗺 Исследователь — посетил 5 локаций",
    "collector_5": "🎒 Коллекционер — собрал 5 предметов",
    "level_5":     "⭐ Опытный — достиг 5 уровня",
    "level_10":    "👑 Ветеран — достиг 10 уровня",
    "first_boss":  "⚔️ Убийца боссов — победил первого босса",
    "boss_5":      "🐉 Легенда — победил 5 боссов",
    "referral_3":  "👥 Друг друзей — пригласил 3 игроков",
    "daily_7":     "🎁 Верный игрок — 7 дней подряд",
}

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🗺 Карта")],
        [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
        [KeyboardButton(text="🌍 Мир"),      KeyboardButton(text="🎁 Награда")],
        [KeyboardButton(text="💎 Премиум"),  KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Что делает герой?"
)

CONSENT_TEXT = (
    "📋 <b>Перед началом — важное</b>\n\n"
    "Бот обрабатывает ваши данные (Telegram ID, username) для сохранения прогресса.\n\n"
    "• Данные хранятся в РФ.\n"
    "• Контент сгенерирован ИИ и маркируется.\n"
    "• Игра для лиц <b>18+</b>.\n"
    "• Отозвать согласие → /revoke.\n\n"
    "Нажимая «Согласен», вы подтверждаете согласие и возраст 18+."
)

HELP_TEXT = (
    "🎮 <b>Как играть</b>\n\n"
    "Просто пиши, что делает герой:\n"
    "• «Осматриваюсь»\n• «Иду в лес»\n• «Атакую гоблина»\n\n"
    "ИИ ведёт сюжет, помнит твои действия и реагирует на них.\n\n"
    "<b>Кнопки внизу:</b>\n"
    "🎒 Инвентарь · 🗺 Карта · ⭐ Профиль · 🏆 Достижения\n"
    "🌍 Мир · 🎁 Награда · 💎 Премиум\n\n"
    "<b>Команды:</b>\n"
    "/reset — сбросить историю\n"
    "/revoke — отозвать согласие"
)


def calc_stats(race_code, class_code):
    race = RACES[race_code]["stats"].copy()
    for k, v in CLASSES[class_code]["bonus"].items():
        race[k] = race.get(k, 0) + v
    return race


# === /start ===
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
            user = await db.get_user(m.from_user.id)

    if not user["consent_given"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Согласен (18+)", callback_data="consent_yes"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no"),
        ]])
        await m.answer(CONSENT_TEXT, reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if not user["race"]:
        await show_race_selection(m)
        return

    if not user["class"]:
        await show_class_selection(m, user["race"])
        return

    if not user["char_name"]:
        await m.answer("✏️ Как зовут вашего героя? Напишите имя (2–20 символов).")
        return

    # Игра началась
    await m.answer(
        f"🎮 <b>С возвращением, {user['char_name']}!</b>\n\n"
        f"⭐ Уровень: {user['level']} · XP: {user['xp']}\n"
        f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
        f"📍 Локация: {user['location']}\n\n"
        f"Опиши действие героя или жми кнопки 👇",
        reply_markup=MAIN_KB,
        parse_mode=ParseMode.HTML
    )


# === Согласие ===
@dp.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await db.give_consent(c.from_user.id)
    await c.message.edit_text(
        "✅ Согласие получено. Добро пожаловать в <b>AI-Приключение</b>!\n\n"
        "Сейчас создадим твоего героя.",
        parse_mode=ParseMode.HTML
    )
    await show_race_selection(c.message)


@dp.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс. Вернуться — /start.")


# === Выбор расы ===
async def show_race_selection(m):
    buttons = []
    for code, r in RACES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{r['name']} — {r['desc']}", callback_data=f"race_{code}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(m.chat.id, "🧝 <b>Выбери расу героя:</b>",
                           reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("race_"))
async def on_race(c: CallbackQuery):
    code = c.data.replace("race_", "")
    if code not in RACES:
        await c.answer("Ошибка выбора")
        return
    await db.set_race(c.from_user.id, code)
    await c.message.edit_text(f"✅ Раса: <b>{RACES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_class_selection(c.message, code)


# === Выбор класса ===
async def show_class_selection(m, race_code):
    buttons = []
    for code, cl in CLASSES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{cl['name']} — {cl['desc']}", callback_data=f"class_{code}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                           reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("class_"))
async def on_class(c: CallbackQuery):
    code = c.data.replace("class_", "")
    if code not in CLASSES:
        await c.answer("Ошибка выбора")
        return
    await db.set_class(c.from_user.id, code)
    await c.message.edit_text(f"✅ Класс: <b>{CLASSES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await bot.send_message(c.from_user.id,
        "✏️ Теперь напиши <b>имя героя</b> (2–20 символов).",
        parse_mode=ParseMode.HTML)


# === Профиль ===
@dp.message(Command("stats"))
@dp.message(F.text == "⭐ Профиль")
async def stats(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала создай героя: /start")
        return
    need = u["level"] * u["level"] * 100
    await m.answer(
        f"⭐ <b>{u['char_name'] or 'Безымянный'}</b>\n\n"
        f"Раса: {RACES.get(u['race'], {}).get('name', '?')}\n"
        f"Класс: {CLASSES.get(u['class'], {}).get('name', '?')}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']}\n\n"
        f"<b>Характеристики:</b>\n"
        f"STR {u['stat_str']} · DEX {u['stat_dex']} · CON {u['stat_con']}\n"
        f"INT {u['stat_int']} · WIT {u['stat_wit']} · MEN {u['stat_men']}\n\n"
        f"📍 Локация: {u['location']}\n"
        f"⚔️ Боссов побеждено: {u['bosses_defeated']}\n"
        f"Действий: {u['action_count']}",
        reply_markup=MAIN_KB,
        parse_mode=ParseMode.HTML
    )


# === Достижения ===
@dp.message(Command("achievements"))
@dp.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    earned = await db.get_achievements(m.from_user.id)
    earned_codes = {a["code"] for a in earned}
    lines = []
    for code, title in ACHIEVEMENTS.items():
        mark = "✅" if code in earned_codes else "🔒"
        lines.append(f"{mark} {title}")
    await m.answer(
        f"🏆 <b>Достижения ({len(earned_codes)}/{len(ACHIEVEMENTS)})</b>\n\n" + "\n".join(lines),
        reply_markup=MAIN_KB,
        parse_mode=ParseMode.HTML
    )


# === Общий мир ===
@dp.message(Command("world"))
@dp.message(F.text == "🌍 Мир")
async def world_cmd(m: Message):
    events = await db.get_world_events(10)
    if not events:
        await m.answer("🌍 Мир пока молчит. Стань первым, кто впишет своё имя в историю!",
                       reply_markup=MAIN_KB)
        return
    lines = [f"• <b>{e['username'] or 'Аноним'}</b>: {e['event_text']}" for e in events]
    await m.answer("🌍 <b>События мира</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Инвентарь ===
@dp.message(Command("inventory"))
@dp.message(F.text == "🎒 Инвентарь")
async def inventory(m: Message):
    items = await db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=MAIN_KB)
        return
    lst = "\n".join(f"• {i}" for i in items)
    await m.answer(f"🎒 <b>Инвентарь</b>\n\n{lst}", reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Карта ===
@dp.message(Command("map"))
@dp.message(F.text == "🗺 Карта")
async def map_cmd(m: Message):
    locs = await db.get_locations(m.from_user.id)
    if not locs:
        await m.answer("🗺 Ты пока нигде не был.", reply_markup=MAIN_KB)
        return
    lst = "\n".join(f"📍 {l}" for l in locs)
    await m.answer(f"🗺 <b>Карта путешествий</b>\n\n{lst}", reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Награда ===
@dp.message(Command("daily"))
@dp.message(F.text == "🎁 Награда")
async def daily(m: Message):
    streak = await db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer("🎁 Уже получал сегодня. Возвращайся завтра!", reply_markup=MAIN_KB)
        return
    bonus = {1: 5, 2: 5, 3: 10, 4: 10, 5: 15, 6: 15, 7: 30}.get(streak, 10)
    msg = f"🎁 <b>Ежедневная награда!</b>\n\nДень {streak} подряд · +{bonus} действий"
    if streak == 7:
        await db.add_item(m.from_user.id, "Редкий амулет удачи")
        msg += "\n\n🏆 <b>Бонус за 7 дней:</b> Редкий амулет удачи!"
    await m.answer(msg, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Премиум ===
@dp.message(Command("premium"))
@dp.message(F.text == "💎 Премиум")
async def premium(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Купить за {PREMIUM_PRICE_STARS} ⭐", callback_data="buy_premium")
    ]])
    await m.answer(
        f"💎 <b>Премиум-подписка</b>\n\n"
        f"• Безлимитные действия\n• Приоритетная обработка\n\n"
        f"Цена: {PREMIUM_PRICE_STARS} ⭐ на 30 дней",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


@dp.message(Command("buy"))
async def buy(m: Message):
    await bot.send_invoice(
        chat_id=m.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium"
    )


@dp.callback_query(F.data == "buy_premium")
async def buy_premium_cb(c: CallbackQuery):
    await bot.send_invoice(
        chat_id=c.message.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium"
    )
    await c.answer()


@dp.pre_checkout_query()
async def pre_checkout(q):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(m: Message):
    await db.set_premium(m.from_user.id, 1)
    await m.answer("💎 <b>Оплата получена!</b> Премиум на 30 дней.",
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Помощь, сброс ===
@dp.message(Command("help"))
@dp.message(F.text == "❓ Помощь")
async def help_cmd(m: Message):
    await m.answer(HELP_TEXT, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.message(Command("revoke"))
async def revoke(m: Message):
    await db.revoke_consent(m.from_user.id)
    await m.answer("🗑 Согласие отозвано.")


@dp.message(Command("reset"))
async def reset(m: Message):
    await db.update_story(m.from_user.id, "")
    await m.answer("🔄 История сброшена.")


# === Проверка достижений ===
async def check_achievements(uid, user):
    new = []
    if user["action_count"] >= 1:
        if await db.add_achievement(uid, "first_step"): new.append("first_step")
    locs = await db.get_locations(uid)
    if len(locs) >= 5:
        if await db.add_achievement(uid, "explorer_5"): new.append("explorer_5")
    items = await db.get_inventory(uid)
    if len(items) >= 5:
        if await db.add_achievement(uid, "collector_5"): new.append("collector_5")
    if user["level"] >= 5:
        if await db.add_achievement(uid, "level_5"): new.append("level_5")
    if user["level"] >= 10:
        if await db.add_achievement(uid, "level_10"): new.append("level_10")
    if user["bosses_defeated"] >= 1:
        if await db.add_achievement(uid, "first_boss"): new.append("first_boss")
    if user["bosses_defeated"] >= 5:
        if await db.add_achievement(uid, "boss_5"): new.append("boss_5")
    if user["referral_count"] >= 3:
        if await db.add_achievement(uid, "referral_3"): new.append("referral_3")
    if user["daily_streak"] >= 7:
        if await db.add_achievement(uid, "daily_7"): new.append("daily_7")
    return new


# === Основной обработчик ===
@dp.message(F.text)
async def handle(m: Message):
    uid = m.from_user.id
    user = await db.get_user(uid, m.from_user.username or "")

    # Согласие
    if not user["consent_given"]:
        await m.answer("⚠️ Сначала /start")
        return

    # Создание героя
    if not user["race"]:
        await show_race_selection(m)
        return
    if not user["class"]:
        await show_class_selection(m, user["race"])
        return
    if not user["char_name"]:
        name = m.text.strip()[:20]
        if len(name) < 2:
            await m.answer("✏️ Имя должно быть от 2 до 20 символов. Попробуй ещё:")
            return
        stats = calc_stats(user["race"], user["class"])
        hp = stats["con"] * 20
        await db.set_char(uid, name, stats, hp)
        await m.answer(
            f"🎉 <b>Герой создан!</b>\n\n"
            f"Имя: {name}\n"
            f"Раса: {RACES[user['race']]['name']}\n"
            f"Класс: {CLASSES[user['class']]['name']}\n\n"
            f"<b>Характеристики:</b>\n"
            f"STR {stats['str']} · DEX {stats['dex']} · CON {stats['con']}\n"
            f"INT {stats['int']} · WIT {stats['wit']} · MEN {stats['men']}\n"
            f"❤️ HP: {hp}\n\n"
            f"📍 Ты в Начальной деревне. Опиши первое действие!",
            reply_markup=MAIN_KB,
            parse_mode=ParseMode.HTML
        )
        return

    # Лимит
    if not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит исчерпан ({FREE_DAILY_LIMIT}).\n\n"
            "💎 Премиум · 👥 Друг · 🎁 Награда",
            reply_markup=MAIN_KB
        )
        return

    # Игра
    await bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]
    result = await ai.generate(user["story"], action, user["arc"], user)
    response = result["text"]

    # Обработка тегов
    if result["item"]:
        await db.add_item(uid, result["item"])
        response += f"\n\n🎒 <i>Получен предмет: {result['item']}</i>"

    if result["location"]:
        await db.add_location(uid, result["location"])
        response += f"\n\n📍 <i>Новая локация: {result['location']}</i>"

    # Урон / лечение
    if result["damage"] > 0:
        new_hp = user["hp"] - result["damage"]
        await db.update_hp(uid, new_hp)
        response += f"\n\n💔 <i>-{result['damage']} HP</i>"

    if result["heal"] > 0:
        new_hp = min(user["max_hp"], user["hp"] + result["heal"])
        await db.update_hp(uid, new_hp)
        response += f"\n\n💚 <i>+{result['heal']} HP</i>"

    # Босс
    if result["boss"]:
        await db.incr_bosses(uid)
        await db.add_world_event(uid, user["username"], f"победил босса «{result['boss']}»")
        response += f"\n\n⚔️ <b>Босс побеждён: {result['boss']}!</b>"
        # Восстановим HP за победу
        await db.update_hp(uid, user["max_hp"])
        response += f"\n❤️ <i>HP восстановлено полностью.</i>"

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    await db.update_story(uid, new_story)
    await db.increment(uid)
    await db.incr_action_count(uid)

    level, xp, leveled_up = await db.add_xp(uid, 10)
    if leveled_up:
        response += f"\n\n⭐ <b>Уровень повышен! Теперь ты уровня {level}.</b>"
        if level in (5, 10):
            await db.add_world_event(uid, user["username"], f"достиг {level} уровня!")

    # Проверка достижений
    updated_user = await db.get_user(uid)
    new_ach = await check_achievements(uid, updated_user)
    if new_ach:
        ach_lines = "\n".join(f"• {ACHIEVEMENTS[c]}" for c in new_ach)
        response += f"\n\n🏆 <b>Новое достижение!</b>\n{ach_lines}"

    left = "∞" if user["is_premium"] else FREE_DAILY_LIMIT - user["requests_today"] - 1
    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · Осталось: {left}</i>",
        parse_mode=ParseMode.HTML
    )


# === Веб-сервер ===
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
