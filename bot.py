import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice, ReplyKeyboardMarkup,
                           KeyboardButton)
from aiogram.enums import ParseMode

from db import DB
import ai
from config import (BOT_TOKEN, GIGACHAT_CREDENTIALS, ADMIN_IDS,
                    FREE_DAILY_LIMIT, PREMIUM_PRICE_STARS, AI_MARKER)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

POTION_PRICE = 25
POTION_HEAL = 30

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
    "rich":        "💰 Богач — накопил 1000 золота",
    "equipped":    "⚔️ Снаряжён — надел первый предмет",
    "survivor":    "💀 Выживший — погиб и вернулся в бой",
    "first_blood": "🩸 Первая кровь — выиграл первый бой",
}

SHOP = {
    "Железный меч":       {"type": "weapon", "price": 50,   "bonus": {"str": 2},           "desc": "Простой, но надёжный"},
    "Стальной меч":       {"type": "weapon", "price": 250,  "bonus": {"str": 5},           "desc": "Оружие настоящего воина"},
    "Клинок тьмы":        {"type": "weapon", "price": 1200, "bonus": {"str": 10, "dex": 2},"desc": "Легендарный клинок"},
    "Посох мага":         {"type": "weapon", "price": 200,  "bonus": {"int": 4},           "desc": "Усиливает магию"},
    "Лук охотника":       {"type": "weapon", "price": 200,  "bonus": {"dex": 4},           "desc": "Точный и быстрый"},
    "Кожаная броня":      {"type": "armor",  "price": 50,   "bonus": {"con": 2},           "desc": "Лёгкая защита"},
    "Кольчуга":           {"type": "armor",  "price": 300,  "bonus": {"con": 5},           "desc": "Крепкая защита"},
    "Мантия мага":        {"type": "armor",  "price": 250,  "bonus": {"int": 3, "wit": 2}, "desc": "Ткань с рунами"},
    "Латы рыцаря":        {"type": "armor",  "price": 1200, "bonus": {"con": 10},          "desc": "Тяжёлая броня"},
    "Амулет удачи":       {"type": "accessory", "price": 150, "bonus": {"men": 3},          "desc": "+удача"},
    "Кольцо силы":        {"type": "accessory", "price": 200, "bonus": {"str": 3},          "desc": "+сила"},
    "Перстень мудрости":  {"type": "accessory", "price": 200, "bonus": {"int": 3},          "desc": "+магия"},
    "Кольцо ловкости":    {"type": "accessory", "price": 200, "bonus": {"dex": 3},          "desc": "+ловкость"},
    "Амулет мудреца":     {"type": "accessory", "price": 800, "bonus": {"int": 5, "wit": 3},"desc": "Редкий артефакт"},
}

DROP_TABLE = ["Кожаная броня", "Железный меч", "Амулет удачи", "Кольцо силы",
              "Кольцо ловкости", "Перстень мудрости", "Посох мага", "Лук охотника"]

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
        [KeyboardButton(text="🗺 Карта"),     KeyboardButton(text="🌍 Мир")],
        [KeyboardButton(text="🎁 Награда"),   KeyboardButton(text="🏅 Рейтинг")],
        [KeyboardButton(text="💎 Премиум"),   KeyboardButton(text="❓ Помощь")],
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
    "Пиши, что делает герой:\n«Осматриваюсь», «Иду в лес», «Атакую гоблина».\n\n"
    "<b>⚔️ Бой:</b>\n"
    "Когда начинается бой, появятся кнопки:\n"
    "⚔️ Атака · 🛡 Защита · 💚 Зелье · 🏃 Бежать\n\n"
    "<b>Оценка врага:</b>\n"
    "🟢 Легко · 🟡 Средне · 🟠 Равный · 🔴 Опасно · 💀 Смертельно · 🐉 Босс\n\n"
    "<b>Смерть:</b> теряешь 30% золота и воскресаешь в деревне. Уровень и XP сохраняются.\n\n"
    "<b>Кнопки:</b>\n"
    "🎒 Инвентарь · 🛒 Магазин · ⭐ Профиль · 🏆 Достижения\n"
    "🗺 Карта · 🌍 Мир · 🎁 Награда · 🏅 Рейтинг · 💎 Премиум"
)


def calc_stats(race_code, class_code):
    race = RACES[race_code]["stats"].copy()
    for k, v in CLASSES[class_code]["bonus"].items():
        race[k] = race.get(k, 0) + v
    return race


def effective_stats(user):
    base = {
        "str": user.get("stat_str", 5),
        "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5),
        "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5),
        "men": user.get("stat_men", 5),
    }
    for slot in ["equipped_weapon", "equipped_armor", "equipped_accessory"]:
        item = user.get(slot, "")
        if item and item in SHOP:
            for k, v in SHOP[item]["bonus"].items():
                base[k] = base.get(k, 0) + v
    return base


def calc_max_hp(user):
    eff = effective_stats(user)
    return eff["con"] * 20 + user["level"] * 15


def hp_bar(current, maximum, length=10):
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def danger_emoji(player_level, enemy_level, is_boss):
    if is_boss:
        return "🐉"
    diff = enemy_level - player_level
    if diff <= -3:
        return "🟢"
    elif diff <= -1:
        return "🟡"
    elif diff <= 1:
        return "🟠"
    elif diff <= 3:
        return "🔴"
    else:
        return "💀"


def combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="combat_attack"),
         InlineKeyboardButton(text="🛡 Защита", callback_data="combat_defend")],
        [InlineKeyboardButton(text=f"💚 Зелье ({POTION_PRICE}💰)", callback_data="combat_potion"),
         InlineKeyboardButton(text="🏃 Бежать", callback_data="combat_flee")],
    ])


async def send_combat_state(chat_id, user, combat, round_text=""):
    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    emoji = danger_emoji(user["level"], combat["enemy_level"], combat["is_boss"])
    boss_label = " 🐉 БОСС" if combat["is_boss"] else ""
    header = f"⚔️ <b>РАУНД {combat['round_num']}</b>"
    enemy_block = (f"{emoji} <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']}){boss_label}\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']})\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}\n"
                    f"💰 {user['gold']}")
    text = f"{header}\n\n{enemy_block}\n\n{player_block}"
    if round_text:
        text += f"\n\n{round_text}"
    await bot.send_message(chat_id, text, reply_markup=combat_kb(), parse_mode=ParseMode.HTML)


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
        await show_race_selection(m); return
    if not user["class"]:
        await show_class_selection(m, user["race"]); return
    if not user["char_name"]:
        await m.answer("✏️ Как зовут вашего героя? Напишите имя (2–20 символов).")
        return

    combat = await db.get_combat(m.from_user.id)
    if combat:
        await send_combat_state(m.chat.id, user, combat, "Ты в бою! Используй кнопки.")
        return

    is_admin = m.from_user.id in ADMIN_IDS
    admin_tag = " 🛠 <i>ADMIN</i>" if is_admin else ""
    await m.answer(
        f"🎮 <b>С возвращением, {user['char_name']}!</b>{admin_tag}\n\n"
        f"⭐ Уровень: {user['level']} · XP: {user['xp']}\n"
        f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
        f"💰 Золото: {user['gold']}\n"
        f"📍 Локация: {user['location']}\n\n"
        f"Опиши действие героя или жми кнопки 👇",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await db.give_consent(c.from_user.id)
    await c.message.edit_text(
        "✅ Согласие получено. Добро пожаловать!\n\nСейчас создадим твоего героя.",
        parse_mode=ParseMode.HTML
    )
    await show_race_selection(c.message)


@dp.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс. Вернуться — /start.")


async def show_race_selection(m):
    buttons = [[InlineKeyboardButton(text=f"{r['name']} — {r['desc']}", callback_data=f"race_{code}")]
               for code, r in RACES.items()]
    await bot.send_message(m.chat.id, "🧝 <b>Выбери расу героя:</b>",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                           parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("race_"))
async def on_race(c: CallbackQuery):
    code = c.data.replace("race_", "")
    if code not in RACES:
        await c.answer("Ошибка выбора"); return
    await db.set_race(c.from_user.id, code)
    await c.message.edit_text(f"✅ Раса: <b>{RACES[code]['name']}</b>", parse_mode=ParseMode.HTML)
    await show_class_selection(c.message, code)


async def show_class_selection(m, race_code):
    buttons = [[InlineKeyboardButton(text=f"{cl['name']} — {cl['desc']}", callback_data=f"class_{code}")]
               for code, cl in CLASSES.items()]
    await bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                           parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("class_"))
async def on_class(c: CallbackQuery):
    code = c.data.replace("class_", "")
    if code not in CLASSES:
        await c.answer("Ошибка выбора"); return
    await db.set_class(c.from_user.id, code)
    await c.message.edit_text(f"✅ Класс: <b>{CLASSES[code]['name']}</b>", parse_mode=ParseMode.HTML)
    await bot.send_message(c.from_user.id, "✏️ Теперь напиши <b>имя героя</b> (2–20 символов).",
                           parse_mode=ParseMode.HTML)


# === Профиль ===
@dp.message(Command("stats"))
@dp.message(F.text == "⭐ Профиль")
async def stats(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала создай героя: /start"); return
    need = u["level"] * u["level"] * 100
    eff = effective_stats(u)
    equip_lines = []
    for slot, label in [("equipped_weapon", "🗡"), ("equipped_armor", "🛡"),
                        ("equipped_accessory", "💍")]:
        item = u.get(slot) or "—"
        equip_lines.append(f"{label} {item}")
    await m.answer(
        f"⭐ <b>{u['char_name']}</b>\n\n"
        f"Раса: {RACES.get(u['race'], {}).get('name', '?')}\n"
        f"Класс: {CLASSES.get(u['class'], {}).get('name', '?')}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']}\n"
        f"💰 Золото: {u['gold']}\n\n"
        f"<b>Характеристики:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Экипировка:</b>\n" + "\n".join(equip_lines) + f"\n\n"
        f"📍 {u['location']}\n"
        f"⚔️ Боссов: {u['bosses_defeated']} · 💀 Смертей: {u['deaths']}\n"
        f"Действий: {u['action_count']}",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


# === Магазин ===
@dp.message(Command("shop"))
@dp.message(F.text == "🛒 Магазин")
async def shop(m: Message):
    u = await db.get_user(m.from_user.id)
    text = f"🛒 <b>Магазин NPC</b>\n\n💰 Золото: <b>{u['gold']}</b>\n\n"
    for category, label in [("weapon", "🗡 Оружие"), ("armor", "🛡 Броня"),
                            ("accessory", "💍 Аксессуары")]:
        text += f"<b>{label}:</b>\n"
        for name, data in SHOP.items():
            if data["type"] == category:
                bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in data["bonus"].items())
                text += f"• {name} ({data['price']}💰) — {bonus_str}\n"
        text += "\n"
    buttons = [[InlineKeyboardButton(text=f"{name} — {data['price']}💰",
                                     callback_data=f"shop_buy_{name}")]
               for name, data in SHOP.items()]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery):
    item_name = c.data.replace("shop_buy_", "")
    if item_name not in SHOP:
        await c.answer("Товар не найден"); return
    data = SHOP[item_name]
    # Админы покупают бесплатно
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin:
        ok = await db.spend_gold(c.from_user.id, data["price"])
        if not ok:
            await c.answer(f"❌ Не хватает золота. Нужно {data['price']}", show_alert=True); return
    await db.add_item(c.from_user.id, item_name)
    await c.answer(f"✅ Куплено: {item_name}")
    await c.message.answer(
        f"✅ <b>Куплено:</b> {item_name}\n\nЭкипировать: /equip {item_name}",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("equip"))
async def equip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /equip Название"); return
    item_name = parts[1].strip()
    if item_name not in SHOP:
        await m.answer("❌ Этот предмет нельзя экипировать."); return
    inv = await db.get_inventory(m.from_user.id)
    if item_name not in inv:
        await m.answer("❌ У тебя нет этого предмета."); return
    slot = SHOP[item_name]["type"]
    old = await db.equip_item(m.from_user.id, slot, item_name)
    await db.remove_item(m.from_user.id, item_name)
    if old:
        await db.add_item(m.from_user.id, old)
        await m.answer(f"⚔️ Экипировано: <b>{item_name}</b>\nСнято: {old}",
                       reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    else:
        await m.answer(f"⚔️ Экипировано: <b>{item_name}</b>",
                       reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    u = await db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    new_hp = min(u["hp"], new_max)
    await db.update_hp_max(m.from_user.id, new_hp, new_max)
    if await db.add_achievement(m.from_user.id, "equipped"):
        await m.answer("🏆 <b>Достижение:</b> ⚔️ Снаряжён", parse_mode=ParseMode.HTML)


@dp.message(Command("unequip"))
async def unequip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /unequip weapon|armor|accessory"); return
    slot = parts[1].strip().lower()
    if slot not in ("weapon", "armor", "accessory"):
        await m.answer("Слоты: weapon, armor, accessory"); return
    item = await db.unequip_item(m.from_user.id, slot)
    if item:
        await db.add_item(m.from_user.id, item)
        await m.answer(f"✅ Снято: {item}", reply_markup=MAIN_KB)
    else:
        await m.answer("Слот пуст.", reply_markup=MAIN_KB)
    u = await db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    new_hp = min(u["hp"], new_max)
    await db.update_hp_max(m.from_user.id, new_hp, new_max)


# === Рейтинг ===
@dp.message(Command("top"))
@dp.message(F.text == "🏅 Рейтинг")
async def top_cmd(m: Message):
    top = await db.get_top_players(10)
    if not top:
        await m.answer("🏅 Пока нет игроков.", reply_markup=MAIN_KB); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["char_name"] or "Аноним"
        race = RACES.get(p["race"], {}).get("name", "?")
        cls = CLASSES.get(p["class"], {}).get("name", "?")
        lines.append(f"{medal} <b>{name}</b> ({race} {cls}) — Ур.{p['level']} · Боссов: {p['bosses_defeated']}")
    await m.answer("🏅 <b>Топ-10</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Инвентарь ===
@dp.message(Command("inventory"))
@dp.message(F.text == "🎒 Инвентарь")
async def inventory(m: Message):
    items = await db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=MAIN_KB); return
    lines = []
    for i in items:
        if i in SHOP:
            bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in SHOP[i]["bonus"].items())
            lines.append(f"• {i} — {bonus_str}")
        else:
            lines.append(f"• {i}")
    text = "🎒 <b>Инвентарь</b>\n\n" + "\n".join(lines) + "\n\n<i>Экипировать: /equip Название</i>"
    await m.answer(text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Карта ===
@dp.message(Command("map"))
@dp.message(F.text == "🗺 Карта")
async def map_cmd(m: Message):
    locs = await db.get_locations(m.from_user.id)
    if not locs:
        await m.answer("🗺 Ты пока нигде не был.", reply_markup=MAIN_KB); return
    lst = "\n".join(f"📍 {l}" for l in locs)
    await m.answer(f"🗺 <b>Карта</b>\n\n{lst}", reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


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
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


# === Мир ===
@dp.message(Command("world"))
@dp.message(F.text == "🌍 Мир")
async def world_cmd(m: Message):
    events = await db.get_world_events(10)
    if not events:
        await m.answer("🌍 Мир молчит. Стань первым героем!", reply_markup=MAIN_KB); return
    lines = [f"• <b>{e['username'] or 'Аноним'}</b>: {e['event_text']}" for e in events]
    await m.answer("🌍 <b>События мира</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Награда ===
@dp.message(Command("daily"))
@dp.message(F.text == "🎁 Награда")
async def daily(m: Message):
    streak = await db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer("🎁 Уже получал сегодня. Завтра!", reply_markup=MAIN_KB); return
    bonus = {1: 5, 2: 5, 3: 10, 4: 10, 5: 15, 6: 15, 7: 30}.get(streak, 10)
    gold_bonus = streak * 20
    await db.add_gold(m.from_user.id, gold_bonus)
    msg = f"🎁 <b>Ежедневная награда!</b>\n\nДень {streak}\n+{bonus} действий · +{gold_bonus}💰"
    if streak == 7:
        await db.add_item(m.from_user.id, "Амулет мудреца")
        msg += "\n\n🏆 <b>Бонус:</b> Амулет мудреца!"
    await m.answer(msg, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# === Премиум ===
@dp.message(Command("premium"))
@dp.message(F.text == "💎 Премиум")
async def premium(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Купить за {PREMIUM_PRICE_STARS} ⭐", callback_data="buy_premium")
    ]])
    await m.answer(
        f"💎 <b>Премиум</b>\n\n• Безлимит действий\n• Приоритет\n\n"
        f"Цена: {PREMIUM_PRICE_STARS} ⭐ / 30 дней",
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


# === Помощь ===
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


# === АДМИН-КОМАНДЫ ===
@dp.message(Command("admin_help"))
async def admin_help(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    await m.answer(
        "🛠 <b>Админ-команды</b>\n\n"
        "/admin_reset — обнулить лимит, восстановить HP\n"
        "/admin_gold N — добавить N золота (можно отрицательное)\n"
        "/admin_hp — восстановить HP\n"
        "/admin_levelup — +1 уровень (мгновенно)\n"
        "/admin_endcombat — принудительно завершить бой\n"
        "/admin_stats — посмотреть свою строку в БД\n\n"
        "<i>Также: покупки в магазине бесплатны для админов.</i>",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("admin_reset"))
async def admin_reset(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    u = await db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, new_max, new_max)
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE users SET requests_today=0 WHERE user_id=$1", m.from_user.id)
    await m.answer(
        f"🛠 <b>Админ-сброс</b>\n\n"
        f"• Лимит обнулён\n"
        f"• HP: {new_max}/{new_max}\n"
        f"• Золото: {u['gold']}",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("admin_gold"))
async def admin_gold(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("Использование: /admin_gold 5000")
        return
    try:
        amount = int(parts[1])
    except ValueError:
        await m.answer("Число должно быть целым.")
        return
    await db.add_gold(m.from_user.id, amount)
    u = await db.get_user(m.from_user.id)
    await m.answer(f"🛠 Золото: {amount:+d}. Теперь: {u['gold']}💰")


@dp.message(Command("admin_hp"))
async def admin_hp(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    u = await db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, new_max, new_max)
    await m.answer(f"🛠 HP: {new_max}/{new_max}")


@dp.message(Command("admin_levelup"))
async def admin_levelup(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    await db.add_xp(m.from_user.id, 999999)
    u = await db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, new_max, new_max)
    await m.answer(f"🛠 Уровень: {u['level']}. HP: {new_max}/{new_max}")


@dp.message(Command("admin_endcombat"))
async def admin_endcombat(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    await db.end_combat(m.from_user.id)
    await m.answer("🛠 Бой завершён.", reply_markup=MAIN_KB)


@dp.message(Command("admin_stats"))
async def admin_stats(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌ Нет доступа.")
        return
    u = await db.get_user(m.from_user.id)
    text = "\n".join(f"<code>{k}</code> = {v}" for k, v in u.items())
    await m.answer(f"🛠 <b>Твоя строка</b>\n\n{text}", parse_mode=ParseMode.HTML)


# === БОЕВАЯ СИСТЕМА ===

async def start_combat_from_ai(chat_id, user, enemy):
    await db.start_combat(user["user_id"], enemy["name"], enemy["level"],
                          enemy["hp"], 1 if enemy["is_boss"] else 0)
    combat = await db.get_combat(user["user_id"])
    intro = "🐉 <b>БОСС!</b> Готовься к тяжёлой битве!" if enemy["is_boss"] else "Бой начался!"
    await send_combat_state(chat_id, user, combat, intro)


async def process_combat_round(chat_id, user, combat, action_type, extra_text=""):
    if action_type == "attack":
        eff = effective_stats(user)
        base = eff["str"] * 2 + eff["dex"]
        rand = random.randint(0, 5)
        dmg = base + rand
        is_crit = random.randint(1, 100) <= eff["dex"]
        if is_crit:
            dmg = int(dmg * 2)
        new_enemy_hp = combat["enemy_hp"] - dmg
        await db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
        if is_crit:
            extra_text = f"💥 <b>КРИТ!</b> Ты наносишь {dmg} урона!"
        else:
            extra_text = f"⚔️ Ты наносишь {dmg} урона."
        await db.set_combat_defending(user["user_id"], 0)

    elif action_type == "defend":
        await db.set_combat_defending(user["user_id"], 1)
        heal = int(user["max_hp"] * 0.05)
        new_hp = min(user["max_hp"], user["hp"] + heal)
        await db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text = f"🛡 Ты в защите. +{heal} HP. Следующий удар слабее."
        enemy_dmg = max(1, int((combat["enemy_level"] * 5 + random.randint(0, 5)) * 0.5))
        new_hp = max(0, user["hp"] - enemy_dmg)
        await db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text += f"\n💔 {combat['enemy_name']} бьёт на {enemy_dmg} (снижено)."
        combat = await db.get_combat(user["user_id"])
        if user["hp"] <= 0:
            await handle_death(chat_id, user, combat)
            return False
        await db.incr_combat_round(user["user_id"])
        combat = await db.get_combat(user["user_id"])
        await send_combat_state(chat_id, user, combat, extra_text)
        return True

    if new_enemy_hp <= 0:
        await handle_victory(chat_id, user, combat, extra_text)
        return False

    enemy_dmg = combat["enemy_level"] * 5 + random.randint(0, 5)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await db.update_hp(user["user_id"], new_hp)
    user["hp"] = new_hp
    extra_text += f"\n💔 {combat['enemy_name']} наносит {enemy_dmg} урона."

    if user["hp"] <= 0:
        await handle_death(chat_id, user, combat)
        return False

    await db.incr_combat_round(user["user_id"])
    combat = await db.get_combat(user["user_id"])
    await send_combat_state(chat_id, user, combat, extra_text)
    return True


async def handle_victory(chat_id, user, combat, prefix_text):
    await db.end_combat(user["user_id"])
    exp = combat["enemy_level"] * 15
    gold = combat["enemy_level"] * 10
    if combat["is_boss"]:
        exp *= 3
        gold *= 3
    await db.add_gold(user["user_id"], gold)
    level, xp, leveled_up = await db.add_xp(user["user_id"], exp)
    text = f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
    text += f"<b>{combat['enemy_name']}</b> повержен!\n"
    text += f"+{exp} XP · +{gold}💰"

    if combat["is_boss"]:
        await db.incr_bosses(user["user_id"])
        await db.add_world_event(user["user_id"], user["username"],
                                 f"победил босса «{combat['enemy_name']}»")
        await db.update_hp(user["user_id"], user["max_hp"])
        text += f"\n\n🐉 <b>БОСС ПОВЕРЖЕН!</b> HP восстановлено."
        if await db.add_achievement(user["user_id"], "first_boss"):
            text += "\n🏆 Достижение: ⚔️ Убийца боссов"

    if random.randint(1, 100) <= 30:
        item = random.choice(DROP_TABLE)
        await db.add_item(user["user_id"], item)
        text += f"\n\n🎒 <b>Добыча:</b> {item}"

    if leveled_up:
        u = await db.get_user(user["user_id"])
        new_max = calc_max_hp(u)
        await db.update_hp_max(user["user_id"], new_max, new_max)
        text += f"\n\n⭐ <b>Уровень {level}!</b> HP: {new_max}."
        if level in (5, 10):
            await db.add_world_event(user["user_id"], user["username"], f"достиг {level} уровня!")

    if await db.add_achievement(user["user_id"], "first_blood"):
        text += "\n🏆 Достижение: 🩸 Первая кровь"
    u = await db.get_user(user["user_id"])
    if u["bosses_defeated"] >= 5:
        if await db.add_achievement(user["user_id"], "boss_5"):
            text += "\n🏆 Достижение: 🐉 Легенда"

    text += f"\n\n<i>{AI_MARKER}</i>"
    await bot.send_message(chat_id, text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


async def handle_death(chat_id, user, combat):
    await db.end_combat(user["user_id"])
    lost_gold = int(user["gold"] * 0.30)
    new_gold = user["gold"] - lost_gold
    await db.set_gold(user["user_id"], new_gold)
    u = await db.get_user(user["user_id"])
    new_max = calc_max_hp(u)
    await db.update_hp_max(user["user_id"], new_max, new_max)
    await db.update_story(user["user_id"], "")
    await db.incr_deaths(user["user_id"])
    await db.add_achievement(user["user_id"], "survivor")
    await db.add_world_event(user["user_id"], user["username"],
                             f"пал в бою с «{combat['enemy_name']}»")
    text = (f"💀 <b>ТЫ ПАЛ В БОЮ</b>\n\n"
            f"<b>{combat['enemy_name']}</b> оказался сильнее.\n\n"
            f"Ты очнулся в Начальной деревне.\n"
            f"Жрецы забрали <b>{lost_gold}💰</b> (30%).\n\n"
            f"❤️ HP: {new_max}/{new_max}\n"
            f"💰 Золото: {new_gold}\n\n"
            f"<i>Уровень и опыт сохранены.</i>")
    await bot.send_message(chat_id, text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "combat_attack")
async def cb_attack(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой окончен."); await c.message.edit_reply_markup(reply_markup=None); return
    await c.answer("⚔️ Атака!")
    await process_combat_round(c.message.chat.id, user, combat, "attack")


@dp.callback_query(F.data == "combat_defend")
async def cb_defend(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой окончен."); await c.message.edit_reply_markup(reply_markup=None); return
    await c.answer("🛡 Защита")
    await process_combat_round(c.message.chat.id, user, combat, "defend")


@dp.callback_query(F.data == "combat_potion")
async def cb_potion(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой окончен."); await c.message.edit_reply_markup(reply_markup=None); return
    if user["hp"] >= user["max_hp"]:
        await c.answer("❤️ HP уже полное!", show_alert=True); return
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin and user["gold"] < POTION_PRICE:
        await c.answer(f"❌ Нужно {POTION_PRICE} золота!", show_alert=True); return
    if not is_admin:
        await db.spend_gold(c.from_user.id, POTION_PRICE)
    new_hp = min(user["max_hp"], user["hp"] + POTION_HEAL)
    await db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    await c.answer(f"💚 +{POTION_HEAL} HP")
    enemy_dmg = combat["enemy_level"] * 5 + random.randint(0, 5)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    if user["hp"] <= 0:
        await handle_death(c.message.chat.id, user, combat)
        return
    await db.incr_combat_round(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    text = f"💚 Ты выпил зелье (+{POTION_HEAL} HP).\n💔 Враг бьёт на {enemy_dmg}."
    await send_combat_state(c.message.chat.id, user, combat, text)


@dp.callback_query(F.data == "combat_flee")
async def cb_flee(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой окончен."); await c.message.edit_reply_markup(reply_markup=None); return
    if combat["is_boss"]:
        await c.answer("🐉 От босса не убежать!", show_alert=True); return
    if random.randint(1, 100) <= 50:
        await db.end_combat(c.from_user.id)
        await c.answer("🏃 Побег удался!")
        await c.message.answer("🏃 Ты успешно сбежал из боя.",
                               reply_markup=MAIN_KB)
    else:
        await c.answer("❌ Побег не удался!")
        enemy_dmg = (combat["enemy_level"] * 5 + random.randint(0, 5)) // 2
        new_hp = max(0, user["hp"] - enemy_dmg)
        await db.update_hp(c.from_user.id, new_hp)
        user["hp"] = new_hp
        if user["hp"] <= 0:
            await handle_death(c.message.chat.id, user, combat)
            return
        await db.incr_combat_round(c.from_user.id)
        combat = await db.get_combat(c.from_user.id)
        text = f"❌ Побег не удался! -{enemy_dmg} HP."
        await send_combat_state(c.message.chat.id, user, combat, text)


@dp.message(Command("flee"))
async def flee_cmd(m: Message):
    user = await db.get_user(m.from_user.id)
    combat = await db.get_combat(m.from_user.id)
    if not combat:
        await m.answer("Ты не в бою.", reply_markup=MAIN_KB); return
    if combat["is_boss"]:
        await m.answer("🐉 От босса не убежать!"); return
    if random.randint(1, 100) <= 50:
        await db.end_combat(m.from_user.id)
        await m.answer("🏃 Ты сбежал!", reply_markup=MAIN_KB)
    else:
        enemy_dmg = (combat["enemy_level"] * 5 + random.randint(0, 5)) // 2
        new_hp = max(0, user["hp"] - enemy_dmg)
        await db.update_hp(m.from_user.id, new_hp)
        user["hp"] = new_hp
        if user["hp"] <= 0:
            await handle_death(m.chat.id, user, combat)
            return
        combat = await db.get_combat(m.from_user.id)
        await send_combat_state(m.chat.id, user, combat, f"❌ Побег не удался! -{enemy_dmg} HP")


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
    if user["referral_count"] >= 3:
        if await db.add_achievement(uid, "referral_3"): new.append("referral_3")
    if user["daily_streak"] >= 7:
        if await db.add_achievement(uid, "daily_7"): new.append("daily_7")
    if user["gold"] >= 1000:
        if await db.add_achievement(uid, "rich"): new.append("rich")
    return new


# === Основной обработчик ===
@dp.message(F.text)
async def handle(m: Message):
    uid = m.from_user.id
    user = await db.get_user(uid, m.from_user.username or "")

    if not user["consent_given"]:
        await m.answer("⚠️ Сначала /start"); return
    if not user["race"]:
        await show_race_selection(m); return
    if not user["class"]:
        await show_class_selection(m, user["race"]); return
    if not user["char_name"]:
        name = m.text.strip()[:20]
        if len(name) < 2:
            await m.answer("✏️ Имя от 2 до 20 символов:"); return
        stats = calc_stats(user["race"], user["class"])
        hp = stats["con"] * 20 + 1 * 15
        await db.set_char(uid, name, stats, hp)
        await m.answer(
            f"🎉 <b>Герой создан!</b>\n\n"
            f"<b>{name}</b>\n"
            f"{RACES[user['race']]['name']} · {CLASSES[user['class']]['name']}\n\n"
            f"STR {stats['str']} · DEX {stats['dex']} · CON {stats['con']}\n"
            f"INT {stats['int']} · WIT {stats['wit']} · MEN {stats['men']}\n"
            f"❤️ HP: {hp} · 💰 100\n\n"
            f"📍 Ты в Начальной деревне.",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
        )
        return

    combat = await db.get_combat(uid)
    if combat:
        await m.answer("⚔️ Ты в бою! Используй кнопки ниже.",
                       reply_markup=combat_kb())
        return

    # Лимит (админы обходят)
    is_admin = uid in ADMIN_IDS
    if not is_admin and not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит исчерпан ({FREE_DAILY_LIMIT}).\n\n"
            "💎 Премиум · 👥 Друг · 🎁 Награда",
            reply_markup=MAIN_KB
        )
        return

    await bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]

    user_for_ai = dict(user)
    eff = effective_stats(user)
    user_for_ai["stat_str"] = eff["str"]
    user_for_ai["stat_dex"] = eff["dex"]
    user_for_ai["stat_con"] = eff["con"]
    user_for_ai["stat_int"] = eff["int"]
    user_for_ai["stat_wit"] = eff["wit"]
    user_for_ai["stat_men"] = eff["men"]

    result = await ai.generate(user["story"], action, user["arc"], user_for_ai)
    response = result["text"]

    if result["enemy"]:
        await db.increment(uid)
        await db.incr_action_count(uid)
        new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
        await db.update_story(uid, new_story)
        await m.answer(f"{response}\n\n<i>{AI_MARKER}</i>", parse_mode=ParseMode.HTML)
        await start_combat_from_ai(m.chat.id, user, result["enemy"])
        return

    if result["item"]:
        await db.add_item(uid, result["item"])
        response += f"\n\n🎒 <i>Получен предмет: {result['item']}</i>"
    if result["location"]:
        await db.add_location(uid, result["location"])
        response += f"\n\n📍 <i>Новая локация: {result['location']}</i>"
    if result["damage"] > 0:
        new_hp = user["hp"] - result["damage"]
        await db.update_hp(uid, new_hp)
        response += f"\n\n💔 <i>-{result['damage']} HP</i>"
        if new_hp <= 0:
            await db.update_hp_max(uid, user["max_hp"], user["max_hp"])
            response += "\n\n💀 <i>Ты потерял сознание. Очнулся в деревне.</i>"
    if result["heal"] > 0:
        new_hp = min(user["max_hp"], user["hp"] + result["heal"])
        await db.update_hp(uid, new_hp)
        response += f"\n\n💚 <i>+{result['heal']} HP</i>"

    await db.add_gold(uid, 5 + result["gold"])
    if result["gold"] > 0:
        response += f"\n\n💰 <i>+{result['gold']} золота</i>"

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    await db.update_story(uid, new_story)
    await db.increment(uid)
    await db.incr_action_count(uid)

    level, xp, leveled_up = await db.add_xp(uid, 10)
    if leveled_up:
        u = await db.get_user(uid)
        new_max = calc_max_hp(u)
        await db.update_hp_max(uid, new_max, new_max)
        response += f"\n\n⭐ <b>Уровень {level}!</b> HP: {new_max}/{new_max}"
        if level in (5, 10):
            await db.add_world_event(uid, user["username"], f"достиг {level} уровня!")

    updated_user = await db.get_user(uid)
    new_ach = await check_achievements(uid, updated_user)
    if new_ach:
        ach_lines = "\n".join(f"• {ACHIEVEMENTS[c]}" for c in new_ach)
        response += f"\n\n🏆 <b>Достижение!</b>\n{ach_lines}"

    if is_admin:
        left = "∞ (admin)"
    elif user["is_premium"]:
        left = "∞"
    else:
        left = FREE_DAILY_LIMIT - user["requests_today"] - 1

    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · 💰 {updated_user['gold']} · ❤️ {updated_user['hp']}/{updated_user['max_hp']} · Осталось: {left}</i>",
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
