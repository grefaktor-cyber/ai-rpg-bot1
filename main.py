import asyncio
import logging
import os
import random
import json
import traceback
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice, ReplyKeyboardMarkup,
                           KeyboardButton)
from aiogram.enums import ParseMode

from db import DB
import ai
import world as W
from config import (BOT_TOKEN, GIGACHAT_CREDENTIALS, ADMIN_IDS,
                    FREE_DAILY_LIMIT, PREMIUM_PRICE_STARS, AI_MARKER)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()


class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Handler error: {e}\n{tb}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id,
                        f"⚠️ <b>Ошибка</b>\n\n<code>{e}</code>\n\n<pre>{tb[-800:]}</pre>",
                        parse_mode=ParseMode.HTML)
                except Exception:
                    pass
            try:
                if hasattr(event, "message") and event.message:
                    await event.message.answer("⚠️ Произошла ошибка. Уже чиним!")
                elif hasattr(event, "answer"):
                    await event.answer("⚠️ Ошибка. Уже чиним!", show_alert=True)
            except Exception:
                pass


POTION_PRICE = 25
POTION_HEAL = 30

RACES = {
    "human":    {"name": "Человек",     "desc": "Универсал.",
                 "stats": {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5}},
    "elf":      {"name": "Эльф",        "desc": "Ловкий, мудрый.",
                 "stats": {"str": 4, "dex": 6, "con": 4, "int": 6, "wit": 6, "men": 5}},
    "dark_elf": {"name": "Тёмный эльф", "desc": "Сильная магия.",
                 "stats": {"str": 5, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 4}},
    "orc":      {"name": "Орк",         "desc": "Могучий воин.",
                 "stats": {"str": 7, "dex": 4, "con": 7, "int": 3, "wit": 4, "men": 3}},
    "dwarf":    {"name": "Гном",        "desc": "Выносливый.",
                 "stats": {"str": 6, "dex": 4, "con": 7, "int": 4, "wit": 4, "men": 5}},
}

CLASSES = {
    "warrior": {"name": "Воин",   "desc": "Мастер меча.", "bonus": {"str": 3, "con": 2}},
    "mage":    {"name": "Маг",    "desc": "Стихии.",      "bonus": {"int": 3, "wit": 2}},
    "archer":  {"name": "Лучник", "desc": "Стрелок.",     "bonus": {"dex": 3, "str": 2}},
    "priest":  {"name": "Жрец",   "desc": "Целитель.",    "bonus": {"men": 3, "wit": 2}},
}

FACTIONS = {
    "light": {"name": "Орден Света",     "desc": "+10% HP, скидка 10%",
              "hp_mult": 1.10, "shop_mult": 0.90, "gold_mult": 0.90, "dmg_mult": 1.00},
    "dark":  {"name": "Тёмное Братство", "desc": "+15% урона, +20% золота",
              "hp_mult": 0.80, "shop_mult": 1.00, "gold_mult": 1.20, "dmg_mult": 1.15},
}

ACHIEVEMENTS = {
    "first_step":  "🌟 Первый шаг",
    "explorer_5":  "🗺 Исследователь — 5 локаций",
    "explorer_10": "🗺 Странник — 10 локаций",
    "explorer_all":"🌍 Покоритель мира",
    "collector_5": "🎒 Коллекционер",
    "level_5":     "⭐ Опытный — 5 уровень",
    "level_10":    "👑 Ветеран — 10 уровень",
    "level_20":    "🔥 Легенда — 20 уровень",
    "first_boss":  "⚔️ Убийца боссов",
    "boss_5":      "🐉 Легенда — 5 боссов",
    "referral_3":  "👥 Друг друзей",
    "daily_7":     "🎁 Верный игрок",
    "rich":        "💰 Богач",
    "equipped":    "⚔️ Снаряжён",
    "survivor":    "💀 Выживший",
    "first_blood": "🩸 Первая кровь",
    "duelist":     "🗡 Дуэлянт",
    "arena_king":  "⚜️ Гроза арены",
    "coward":      "🏳️ Трус",
    "graffiti":    "✍️ Летописец",
    "social":      "👥 Общительный",
    "pet_owner":   "🐾 Хозяин",
    "pet_10":      "🐕 Друг навек",
    "dungeon_1":   "🏰 Пещерный ход",
    "dungeon_5":   "🏰 Покоритель подземелий",
    "crafter":     "⚒️ Кузнец",
    "upgrader":    "🔨 Улучшатель",
    "guild_founder":"🏛 Основатель гильдии",
    "guild_member":"🏛 Член гильдии",
    "conqueror":   "⚔️ Захватчик",
    "event_hunter":"🎯 Охотник за событиями",
    "quest_master":"📜 Мастер квестов",
}

SHOP = {
    "Железный меч":       {"type": "weapon", "price": 50,   "bonus": {"str": 2}},
    "Стальной меч":       {"type": "weapon", "price": 250,  "bonus": {"str": 5}},
    "Клинок тьмы":        {"type": "weapon", "price": 1200, "bonus": {"str": 10, "dex": 2}},
    "Посох мага":         {"type": "weapon", "price": 200,  "bonus": {"int": 4}},
    "Лук охотника":       {"type": "weapon", "price": 200,  "bonus": {"dex": 4}},
    "Кожаная броня":      {"type": "armor",  "price": 50,   "bonus": {"con": 2}},
    "Кольчуга":           {"type": "armor",  "price": 300,  "bonus": {"con": 5}},
    "Мантия мага":        {"type": "armor",  "price": 250,  "bonus": {"int": 3, "wit": 2}},
    "Латы рыцаря":        {"type": "armor",  "price": 1200, "bonus": {"con": 10}},
    "Амулет удачи":       {"type": "accessory", "price": 150, "bonus": {"men": 3}},
    "Кольцо силы":        {"type": "accessory", "price": 200, "bonus": {"str": 3}},
    "Перстень мудрости":  {"type": "accessory", "price": 200, "bonus": {"int": 3}},
    "Кольцо ловкости":    {"type": "accessory", "price": 200, "bonus": {"dex": 3}},
    "Амулет мудреца":     {"type": "accessory", "price": 800, "bonus": {"int": 5, "wit": 3}},
}

DROP_TABLE = ["Кожаная броня", "Железный меч", "Амулет удачи", "Кольцо силы",
              "Кольцо ловкости", "Перстень мудрости", "Посох мага", "Лук охотника"]

PETS = {
    "wolf":    {"name": "Волк",      "price": 500,  "desc": "Атака +5×(ур)",
                "bonus": {"str": 2, "dex": 1}},
    "owl":     {"name": "Сова",      "price": 500,  "desc": "+15% крита",
                "bonus": {"wit": 2, "int": 1}},
    "dragon":  {"name": "Дракончик", "price": 2000, "desc": "Атака через ход",
                "bonus": {"str": 3, "con": 1}},
    "phoenix": {"name": "Феникс",    "price": 3000, "desc": "Лечит 5% HP каждый раунд",
                "bonus": {"men": 3, "con": 2}},
}

DUNGEONS = {
    "goblin_cave": {"name": "Пещера гоблинов",  "level_req": 1,  "entry": 50,
                    "rooms": 3, "reward_mult": 1.0,
                    "enemies": ["Гоблин-разведчик", "Гоблин-воин", "Вождь гоблинов"]},
    "old_ruins":   {"name": "Древние руины",    "level_req": 4,  "entry": 200,
                    "rooms": 4, "reward_mult": 2.0,
                    "enemies": ["Скелет-страж", "Проклятый рыцарь", "Каменный голем", "Древний лич"]},
    "crypt":       {"name": "Проклятый склеп",  "level_req": 9,  "entry": 600,
                    "rooms": 5, "reward_mult": 4.0,
                    "enemies": ["Вампир-новичок", "Призрак", "Некромант", "Тёмный жрец", "Король вампиров"]},
    "abyss":       {"name": "Бездна",           "level_req": 16, "entry": 2000,
                    "rooms": 5, "reward_mult": 8.0,
                    "enemies": ["Демон", "Архидемон", "Пожиратель душ", "Повелитель Бездны", "Древний дракон"]},
}

CRAFT_RECIPES = {
    "Стальной меч":     {"base": "Железный меч",   "count": 3, "mat": "iron",    "mat_count": 5},
    "Кольчуга":         {"base": "Кожаная броня",  "count": 3, "mat": "leather", "mat_count": 5},
    "Латы рыцаря":      {"base": "Кольчуга",       "count": 2, "mat": "iron",    "mat_count": 15},
    "Клинок тьмы":      {"base": "Стальной меч",   "count": 2, "mat": "crystal", "mat_count": 10},
    "Мантия мага":      {"base": "Кожаная броня",  "count": 2, "mat": "dust",    "mat_count": 8},
    "Амулет мудреца":   {"base": "Амулет удачи",   "count": 2, "mat": "crystal", "mat_count": 5},
    "Кольцо силы":      {"base": "Амулет удачи",   "count": 1, "mat": "iron",    "mat_count": 3},
    "Кольцо ловкости":  {"base": "Амулет удачи",   "count": 1, "mat": "dust",    "mat_count": 3},
    "Перстень мудрости":{"base": "Амулет удачи",   "count": 1, "mat": "crystal", "mat_count": 3},
}

MATERIAL_NAMES = {"iron": "железо", "leather": "кожа",
                  "dust": "магическая пыль", "crystal": "кристалл"}

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
        [KeyboardButton(text="📋 Квесты"),    KeyboardButton(text="🗺 Карта")],
        [KeyboardButton(text="🚶 Идти"),      KeyboardButton(text="🌍 Мир")],
        [KeyboardButton(text="👥 Кто здесь"), KeyboardButton(text="🐾 Питомец")],
        [KeyboardButton(text="🏰 Подземелья"),KeyboardButton(text="⚒️ Кузница")],
        [KeyboardButton(text="🏛 Гильдия"),   KeyboardButton(text="🎁 Награда")],
        [KeyboardButton(text="🏅 Рейтинг"),   KeyboardButton(text="💎 Премиум")],
        [KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Что делает герой?"
)

CONSENT_TEXT = (
    "📋 <b>Перед началом — важное</b>\n\n"
    "Бот обрабатывает ваши данные для сохранения прогресса.\n\n"
    "• Данные хранятся в РФ.\n"
    "• Контент сгенерирован ИИ и маркируется.\n"
    "• Игра для лиц <b>18+</b>.\n"
    "• Отозвать согласие → /revoke.\n\n"
    "Нажимая «Согласен», вы подтверждаете согласие и возраст 18+."
)

HELP_TEXT = (
    "🎮 <b>Как играть</b>\n\n"
    "Пиши, что делает герой: «Осматриваюсь», «Атакую гоблина».\n\n"
    "<b>🚶 Путешествия:</b> /travel или кнопка внизу.\n"
    "Мир — 12 локаций, соединённых дорогами.\n\n"
    "<b>📜 NPC-квесты:</b> NPC в локациях дают задания\n"
    "<b>🏛 Гильдии:</b> /guild — создать, воевать, захватывать\n"
    "<b>🌍 События:</b> в локациях случаются нашествия и клады\n"
    "<b>🐉 Боссы локаций:</b> уникальные враги\n\n"
    "<b>⚔️ Бой:</b> ⚔️ Атака · 🛡 Защита · 💚 Зелье · 🏃 Бежать\n"
    "<b>📋 Ежедневные квесты:</b> /quests\n"
)


def parse_item(s):
    if not s:
        return "", 0
    import re as _re
    m = _re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def calc_stats(race_code, class_code):
    race = RACES[race_code]["stats"].copy()
    for k, v in CLASSES[class_code]["bonus"].items():
        race[k] = race.get(k, 0) + v
    return race


def effective_stats(user):
    base = {
        "str": user.get("stat_str", 5), "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5), "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5), "men": user.get("stat_men", 5),
    }
    for slot in ["equipped_weapon", "equipped_armor", "equipped_accessory"]:
        raw = user.get(slot, "")
        if raw:
            name, lvl = parse_item(raw)
            if name in SHOP:
                for k, v in SHOP[name]["bonus"].items():
                    bonus = int(v * (1 + lvl * 0.10))
                    base[k] = base.get(k, 0) + bonus
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"])
        if pet:
            for k, v in pet["bonus"].items():
                base[k] = base.get(k, 0) + v
    return base


def calc_max_hp(user):
    eff = effective_stats(user)
    hp = eff["con"] * 20 + user["level"] * 15
    faction = FACTIONS.get(user.get("faction", ""), None)
    if faction:
        hp = int(hp * faction["hp_mult"])
    return hp


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
    if diff <= -3: return "🟢"
    if diff <= -1: return "🟡"
    if diff <= 1:  return "🟠"
    if diff <= 3:  return "🔴"
    return "💀"


def faction_mult(user, key):
    f = FACTIONS.get(user.get("faction", ""))
    if not f:
        return 1.0
    return f.get(key, 1.0)


def combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="combat_attack"),
         InlineKeyboardButton(text="🛡 Защита", callback_data="combat_defend")],
        [InlineKeyboardButton(text=f"💚 Зелье ({POTION_PRICE}💰)", callback_data="combat_potion"),
         InlineKeyboardButton(text="🏃 Бежать", callback_data="combat_flee")],
    ])


def dungeon_continue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="dungeon_next")],
        [InlineKeyboardButton(text="🏃 Выйти с добычей", callback_data="dungeon_leave")],
    ])


def pvp_kb(my_turn):
    if my_turn:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атака", callback_data="pvp_attack")],
            [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="pvp_surrender")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="pvp_surrender")],
    ])


def duel_offer_kb(offer_id, is_caller=False):
    if is_caller:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"duel_cancel_{offer_id}")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept_{offer_id}"),
         InlineKeyboardButton(text="💰 Своя ставка", callback_data=f"duel_counter_{offer_id}")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"duel_decline_{offer_id}")],
    ])


def travel_kb(location_code, player_level):
    rows = []
    for code, info in W.get_neighbors(location_code):
        can, reason = W.can_enter(code, player_level)
        if can:
            rows.append([InlineKeyboardButton(text=f"→ {info['name']}",
                                              callback_data=f"travel_to_{code}")])
        else:
            rows.append([InlineKeyboardButton(text=f"🔒 {info['name']} (ур.{info['level_req']}+)",
                                              callback_data="travel_locked")])
    rows.append([InlineKeyboardButton(text="❌ Остаться", callback_data="travel_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def npc_list_kb(location_code):
    rows = []
    for code, info in W.get_npcs_in_location(location_code):
        rows.append([InlineKeyboardButton(text=f"👤 {info['name']}", callback_data=f"npc_{code}")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="npc_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def npc_menu_kb(npc_code):
    npc = W.get_npc(npc_code)
    if not npc:
        return None
    rows = []
    for qcode in npc.get("quests", []):
        q = W.get_quest(qcode)
        if not q:
            continue
        rows.append([InlineKeyboardButton(text=f"📜 {q['title']}",
                                          callback_data=f"npcquest_{qcode}")])
    rows.append([InlineKeyboardButton(text="💬 Поговорить",
                                      callback_data=f"npctalk_{npc_code}")])
    rows.append([InlineKeyboardButton(text="❌ Уйти", callback_data="npc_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def guild_menu_kb(has_guild):
    if has_guild:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Инфо", callback_data="guild_info")],
            [InlineKeyboardButton(text="👥 Участники", callback_data="guild_members")],
            [InlineKeyboardButton(text="⚔️ Захватить локацию", callback_data="guild_capture")],
            [InlineKeyboardButton(text="🚪 Выйти из гильдии", callback_data="guild_leave")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛 Создать гильдию (1000💰)",
                              callback_data="guild_create_start")],
        [InlineKeyboardButton(text="🏆 Топ гильдий", callback_data="guild_top")],
    ])


async def send_combat_state(chat_id, user, combat, round_text="", event=None):
    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    emoji = danger_emoji(user["level"], combat["enemy_level"], combat["is_boss"])
    boss_label = " 🐉 БОСС" if combat["is_boss"] else ""
    header = f"⚔️ <b>РАУНД {combat['round_num']}</b>"
    if event:
        header += f" · {event['event_name']}"
    enemy_block = (f"{emoji} <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']}){boss_label}\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    pet_line = ""
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"], {})
        pet_line = f"\n🐾 {user.get('pet_name', pet.get('name', 'Питомец'))} (ур. {user.get('pet_level', 1)})"
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']}){pet_line}\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}\n"
                    f"💰 {user['gold']}")
    text = f"{header}\n\n{enemy_block}\n\n{player_block}"
    if round_text:
        text += f"\n\n{round_text}"
    await bot.send_message(chat_id, text, reply_markup=combat_kb(), parse_mode=ParseMode.HTML)


async def send_pvp_state(uid, user, combat):
    if not combat:
        return
    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    header = f"⚔️ <b>ДУЭЛЬ · РАУНД {combat['round_num']}</b>"
    turn_text = "🎯 <b>Твой ход!</b>" if combat["my_turn"] else "⏳ Ждём хода противника..."
    enemy_block = (f"🛡 <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']})\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']})\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}\n"
                    f"💰 Ставка: {combat['stake']}")
    text = f"{header}\n\n{enemy_block}\n\n{player_block}\n\n{turn_text}"
    try:
        await bot.send_message(uid, text, reply_markup=pvp_kb(combat["my_turn"]),
                               parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"send_pvp_state error: {e}")


async def broadcast_to_location(location_code, text, exclude_uid=0):
    players = await db.get_players_at_location(location_code, exclude_uid)
    for p in players:
        try:
            await bot.send_message(p["user_id"], text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


# ================= START / CONSENT =================
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
            await m.answer("🎉 Вы пришли по приглашению!")
            try:
                await bot.send_message(referrer_id,
                    "🎉 По вашей ссылке пришёл новый игрок! +10 действий.")
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
    if not user["faction"]:
        await show_faction_selection(m); return
    if not user["char_name"]:
        await m.answer("✏️ Как зовут вашего героя? (2–20 символов)")
        return

    combat = await db.get_combat(m.from_user.id)
    if combat:
        if combat.get("is_pvp"):
            await m.answer("⚔️ Ты в дуэли!", reply_markup=pvp_kb(combat["my_turn"]))
        else:
            await send_combat_state(m.chat.id, user, combat, "Ты в бою!")
        return

    await show_main_menu(m, user)


async def show_main_menu(m, user):
    loc_code = user.get("location_code", "village")
    loc = W.get_location(loc_code) or {}
    event = await db.get_active_event(loc_code)
    owner = await db.get_location_owner(loc_code)
    is_admin = user["user_id"] in ADMIN_IDS
    admin_tag = " 🛠 <i>ADMIN</i>" if is_admin else ""

    header = f"🎮 <b>С возвращением, {user['char_name']}!</b>{admin_tag}\n\n"
    header += f"⭐ Ур. {user['level']} · XP: {user['xp']}\n"
    header += f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
    header += f"💰 Золото: {user['gold']}\n"
    header += f"📍 <b>{loc.get('name', '?')}</b>"
    if owner:
        header += f" 🏴 [{owner.get('guild_tag', '?')}]"
    header += "\n"
    if event:
        header += f"\n{event['event_name']}: <i>{event['event_desc']}</i>\n"
    header += "\nОпиши действие или жми кнопки 👇"
    await m.answer(header, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await db.give_consent(c.from_user.id)
    await c.message.edit_text("✅ Согласие получено. Создадим героя!",
                              parse_mode=ParseMode.HTML)
    await show_race_selection(c.message)


@dp.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс.")


async def show_race_selection(m):
    buttons = [[InlineKeyboardButton(text=f"{r['name']} — {r['desc']}",
                                     callback_data=f"race_{code}")]
               for code, r in RACES.items()]
    await bot.send_message(m.chat.id, "🧝 <b>Выбери расу:</b>",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                           parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("race_"))
async def on_race(c: CallbackQuery):
    code = c.data.replace("race_", "")
    if code not in RACES:
        await c.answer("Ошибка"); return
    await db.set_race(c.from_user.id, code)
    await c.message.edit_text(f"✅ Раса: <b>{RACES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_class_selection(c.message, code)


async def show_class_selection(m, race_code):
    buttons = [[InlineKeyboardButton(text=f"{cl['name']} — {cl['desc']}",
                                     callback_data=f"class_{code}")]
               for code, cl in CLASSES.items()]
    await bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                           parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("class_"))
async def on_class(c: CallbackQuery):
    code = c.data.replace("class_", "")
    if code not in CLASSES:
        await c.answer("Ошибка"); return
    await db.set_class(c.from_user.id, code)
    await c.message.edit_text(f"✅ Класс: <b>{CLASSES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_faction_selection(c.message)


async def show_faction_selection(m):
    buttons = [[InlineKeyboardButton(text=f"{f['name']} — {f['desc']}",
                                     callback_data=f"faction_{code}")]
               for code, f in FACTIONS.items()]
    await bot.send_message(m.chat.id, "🏛 <b>Выбери фракцию:</b>",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                           parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("faction_"))
async def on_faction(c: CallbackQuery):
    code = c.data.replace("faction_", "")
    if code not in FACTIONS:
        await c.answer("Ошибка"); return
    await db.set_faction(c.from_user.id, code)
    await c.message.edit_text(f"✅ Фракция: <b>{FACTIONS[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await bot.send_message(c.from_user.id,
                           "✏️ Напиши <b>имя героя</b> (2–20 символов).",
                           parse_mode=ParseMode.HTML)


# ================= ПРОФИЛЬ =================
@dp.message(Command("stats"))
@dp.message(F.text == "⭐ Профиль")
async def stats(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала /start"); return
    need = u["level"] * u["level"] * 100
    eff = effective_stats(u)
    equip_lines = []
    for slot, label in [("equipped_weapon", "🗡"), ("equipped_armor", "🛡"),
                        ("equipped_accessory", "💍")]:
        item = u.get(slot) or "—"
        equip_lines.append(f"{label} {item}")

    faction_name = FACTIONS.get(u["faction"], {}).get("name", "—")
    pet_line = ""
    if u.get("pet_type"):
        pet = PETS.get(u["pet_type"], {})
        pet_line = (f"\n🐾 Питомец: {u.get('pet_name')} "
                    f"({pet.get('name')}, ур. {u.get('pet_level', 1)})")

    guild = await db.get_user_guild(m.from_user.id)
    guild_line = ""
    if guild:
        guild_line = f"\n🏛 Гильдия: <b>{guild['name']}</b> [{guild['tag']}]"

    materials = (f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · "
                 f"✨ {u['mat_dust']} · 💎 {u['mat_crystal']}")

    loc_code = u.get("location_code", "village")
    loc_name = W.get_location(loc_code).get("name", "?")

    await m.answer(
        f"⭐ <b>{u['char_name']}</b>\n\n"
        f"Раса: {RACES.get(u['race'], {}).get('name', '?')}\n"
        f"Класс: {CLASSES.get(u['class'], {}).get('name', '?')}\n"
        f"Фракция: {faction_name}{guild_line}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']}\n"
        f"💰 Золото: {u['gold']}\n"
        f"🏅 Репутация: {u['reputation']}{pet_line}\n\n"
        f"<b>Статы:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Экипировка:</b>\n" + "\n".join(equip_lines) + f"\n\n"
        f"<b>Материалы:</b> {materials}\n\n"
        f"📍 {loc_name}\n"
        f"⚔️ Боссов: {u['bosses_defeated']} · 💀 Смертей: {u['deaths']}\n"
        f"🗡 PvP: {u['pvp_wins']}/{u['pvp_losses']}",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


# ================= МАГАЗИН =================
@dp.message(Command("shop"))
@dp.message(F.text == "🛒 Магазин")
async def shop(m: Message):
    u = await db.get_user(m.from_user.id)
    shop_mult = faction_mult(u, "shop_mult")
    text = f"🛒 <b>Магазин</b>\n\n💰 Золото: <b>{u['gold']}</b>"
    if shop_mult < 1:
        text += f" (−{int((1-shop_mult)*100)}% фракция)"
    text += "\n\n"
    for category, label in [("weapon", "🗡 Оружие"), ("armor", "🛡 Броня"),
                            ("accessory", "💍 Аксессуары")]:
        text += f"<b>{label}:</b>\n"
        for name, data in SHOP.items():
            if data["type"] == category:
                price = int(data["price"] * shop_mult)
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                text += f"• {name} ({price}💰) — {bonus_str}\n"
        text += "\n"
    buttons = [[InlineKeyboardButton(text=f"{name} — {int(data['price']*shop_mult)}💰",
                                     callback_data=f"shop_buy_{name}")]
               for name, data in SHOP.items()]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery):
    item_name = c.data.replace("shop_buy_", "")
    if item_name not in SHOP:
        await c.answer("Не найдено"); return
    data = SHOP[item_name]
    user = await db.get_user(c.from_user.id)
    price = int(data["price"] * faction_mult(user, "shop_mult"))
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin:
        ok = await db.spend_gold(c.from_user.id, price)
        if not ok:
            await c.answer(f"❌ Нужно {price}💰", show_alert=True); return
    await db.add_item(c.from_user.id, item_name)
    await c.answer(f"✅ Куплено: {item_name}")
    await c.message.answer(f"✅ <b>{item_name}</b> куплен!\n/equip {item_name}",
                           parse_mode=ParseMode.HTML)


@dp.message(Command("equip"))
async def equip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /equip Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя экипировать."); return
    inv = await db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    if item_name not in inv_names:
        await m.answer("❌ Нет в инвентаре."); return
    slot = SHOP[base_name]["type"]
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
    await db.update_hp_max(m.from_user.id, min(u["hp"], new_max), new_max)
    if await db.add_achievement(m.from_user.id, "equipped"):
        await m.answer("🏆 Достижение: ⚔️ Снаряжён", parse_mode=ParseMode.HTML)


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
    await db.update_hp_max(m.from_user.id, min(u["hp"], new_max), new_max)


# ================= РЕЙТИНГИ =================
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
        lines.append(f"{medal} <b>{name}</b> ({race} {cls}) — Ур.{p['level']}")
    await m.answer("🏅 <b>Топ-10</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.message(Command("pvptop"))
async def pvp_top_cmd(m: Message):
    top = await db.get_pvp_top(10)
    if not top:
        await m.answer("🏅 Нет победителей дуэлей.", reply_markup=MAIN_KB); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} <b>{p['char_name']}</b> — {p['pvp_wins']}🏆 / {p['pvp_losses']}💀")
    await m.answer("⚔️ <b>Топ дуэлянтов</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= ИНВЕНТАРЬ =================
@dp.message(Command("inventory"))
@dp.message(F.text == "🎒 Инвентарь")
async def inventory(m: Message):
    items = await db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=MAIN_KB); return
    lines = []
    for it in items:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP:
            bonus_str = ", ".join(f"+{v} {k.upper()}"
                                  for k, v in SHOP[name]["bonus"].items())
            suffix = f" (+{lvl})" if lvl else ""
            lines.append(f"• {name}{suffix} — {bonus_str}")
        else:
            lines.append(f"• {it['item_name']}")
    text = "🎒 <b>Инвентарь</b>\n\n" + "\n".join(lines) + "\n\n<i>/equip Название+N</i>"
    await m.answer(text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= КАРТА / ПУТЕШЕСТВИЯ =================
@dp.message(Command("map"))
@dp.message(F.text == "🗺 Карта")
async def map_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    loc_code = u.get("location_code", "village")
    visited = await db.get_all_location_codes_visited(m.from_user.id)
    visited_set = set(visited)

    lines = ["🗺 <b>Карта мира</b>\n"]
    for code, info in W.LOCATIONS.items():
        marker = "📍" if code == loc_code else ("✅" if info["name"] in visited_set else "❓")
        if code == loc_code or info["name"] in visited_set:
            lines.append(f"{marker} {info['name']}")
        else:
            lines.append(f"❓ Неизвестная локация")

    captured = await db.get_all_captured_locations()
    if captured:
        lines.append("\n<b>Захвачено гильдиями:</b>")
        for c in captured:
            loc_name = W.get_location(c["location_code"]).get("name", c["location_code"])
            lines.append(f"🏴 {loc_name} — [{c['tag']}] {c['name']}")

    lines.append(f"\n📍 Ты в: <b>{W.get_location(loc_code).get('name', '?')}</b>")
    lines.append(f"\nВсего открыто: {len(visited_set)}/{len(W.LOCATIONS)}")
    await m.answer("\n".join(lines), reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.message(Command("travel"))
@dp.message(F.text == "🚶 Идти")
async def travel_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return
    loc_code = u.get("location_code", "village")
    loc = W.get_location(loc_code)
    neighbors = W.get_neighbors(loc_code)
    if not neighbors:
        await m.answer(f"📍 Ты в <b>{loc['name']}</b>. Отсюда нет пути.",
                       reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
        return
    await m.answer(
        f"🚶 <b>Куда идёшь?</b>\n\n"
        f"📍 Сейчас ты в: <b>{loc['name']}</b>\n"
        f"<i>{loc['desc']}</i>",
        reply_markup=travel_kb(loc_code, u["level"]),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("travel_to_"))
async def travel_do(c: CallbackQuery):
    code = c.data.replace("travel_to_", "")
    if code not in W.LOCATIONS:
        await c.answer("Не найдено"); return
    u = await db.get_user(c.from_user.id)
    if await db.get_combat(c.from_user.id):
        await c.answer("⚔️ Ты в бою!"); return
    cur_code = u.get("location_code", "village")
    if code not in W.LOCATIONS[cur_code]["exits"]:
        await c.answer("Отсюда туда не попасть!", show_alert=True); return
    can, reason = W.can_enter(code, u["level"])
    if not can:
        await c.answer(reason, show_alert=True); return

    old_name = W.get_location(cur_code).get("name", "?")
    new_loc = W.get_location(code)
    await db.set_location_code(c.from_user.id, code)
    await db.add_location(c.from_user.id, new_loc["name"])
    await db.progress_quest(c.from_user.id, "visit_locations", 1)

    loc = W.get_location(code)
    event = await db.get_active_event(code)
    owner = await db.get_location_owner(code)

    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    text = f"🚶 <i>{old_name} → {loc['name']}</i>\n\n"
    text += f"📍 <b>{loc['name']}</b>\n<i>{loc['desc']}</i>\n"
    if owner:
        text += f"\n🏴 Владелец: <b>[{owner['guild_tag']}]</b> {owner['guild_name']}"
    if event:
        text += f"\n\n{event['event_name']}: <i>{event['event_desc']}</i>"
    npcs = W.get_npcs_in_location(code)
    if npcs:
        text += "\n\n👤 <b>Здесь есть:</b>"
        for c2, info in npcs:
            text += f"\n• {info['name']}"
    if loc.get("enemies"):
        text += f"\n\n⚔️ <i>Враги: {', '.join(loc['enemies'])}</i>"

    await bot.send_message(c.from_user.id, text, reply_markup=MAIN_KB,
                           parse_mode=ParseMode.HTML)
    await c.answer(f"→ {loc['name']}")

    await broadcast_to_location(
        code,
        f"👤 <b>{u['char_name']}</b> прибыл в локацию.",
        exclude_uid=c.from_user.id
    )


@dp.callback_query(F.data == "travel_locked")
async def travel_locked(c: CallbackQuery):
    await c.answer("Уровень слишком низкий для этой локации", show_alert=True)


@dp.callback_query(F.data == "travel_cancel")
async def travel_cancel(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer("Остаёшься здесь")


# ================= КТО ЗДЕСЬ =================
@dp.message(Command("who"))
@dp.message(F.text == "👥 Кто здесь")
async def who_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    code = u.get("location_code", "village")
    players = await db.get_players_at_location(code, u["user_id"])
    loc_name = W.get_location(code).get("name", "?")
    if not players:
        await m.answer(
            f"👥 В «{loc_name}» больше никого нет.\n\n"
            f"<i>Когда другие игроки зайдут сюда, ты их увидишь.</i>",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
        return
    lines = []
    for p in players:
        race = RACES.get(p["race"], {}).get("name", "?")
        cls = CLASSES.get(p["class"], {}).get("name", "?")
        gtag = ""
        if p.get("guild_id"):
            g = await db.get_guild(p["guild_id"])
            if g:
                gtag = f" [{g['tag']}]"
        lines.append(f"• <b>{p['char_name']}</b>{gtag} (Ур.{p['level']}, {race} {cls})")
    await m.answer(f"👥 <b>В «{loc_name}»:</b>\n\n" + "\n".join(lines) +
                   f"\n\n<i>/duel Имя — вызвать на дуэль</i>",
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= ГРАФФИТИ =================
@dp.message(Command("write"))
async def write_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await m.answer("Использование: /write текст"); return
    text = parts[1].strip()[:200]
    loc_name = W.get_location(u.get("location_code", "village")).get("name", "?")
    await db.add_graffiti(m.from_user.id, u["char_name"], loc_name, text)
    await m.answer(f"✍️ Запись оставлена в «{loc_name}».",
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    if await db.add_achievement(m.from_user.id, "graffiti"):
        await m.answer("🏆 Достижение: ✍️ Летописец", parse_mode=ParseMode.HTML)


@dp.message(Command("read"))
async def read_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    loc_name = W.get_location(u.get("location_code", "village")).get("name", "?")
    notes = await db.get_graffiti(loc_name, 15)
    if not notes:
        await m.answer(f"📜 В «{loc_name}» нет записей.",
                       reply_markup=MAIN_KB); return
    lines = [f"• <b>{n['username']}</b>: <i>{n['text']}</i>" for n in notes]
    await m.answer(f"📜 <b>Записи в «{loc_name}»:</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= ДОСТИЖЕНИЯ =================
@dp.message(Command("achievements"))
@dp.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    earned = await db.get_achievements(m.from_user.id)
    codes = {a["code"] for a in earned}
    lines = [f"{'✅' if c in codes else '🔒'} {t}" for c, t in ACHIEVEMENTS.items()]
    await m.answer(
        f"🏆 <b>Достижения ({len(codes)}/{len(ACHIEVEMENTS)})</b>\n\n" + "\n".join(lines),
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


# ================= МИР / СОБЫТИЯ =================
@dp.message(Command("world"))
@dp.message(F.text == "🌍 Мир")
async def world_cmd(m: Message):
    events = await db.get_all_active_events()
    captured = await db.get_all_captured_locations()
    text = "🌍 <b>Мир Lineage</b>\n\n"
    if events:
        text += "<b>🔥 Активные события:</b>\n"
        for e in events:
            loc_name = W.get_location(e["location_code"]).get("name", "?")
            text += f"• {e['event_name']} в <b>{loc_name}</b> — {e['event_desc']}\n"
        text += "\n"
    else:
        text += "<i>Сейчас в мире тихо.</i>\n\n"
    if captured:
        text += "<b>🏴 Захваченные локации:</b>\n"
        for c in captured:
            loc_name = W.get_location(c["location_code"]).get("name", "?")
            text += f"• {loc_name} — [{c['tag']}] {c['name']}\n"
        text += "\n"
    recent = await db.get_world_events(8)
    if recent:
        text += "<b>📰 Последние события:</b>\n"
        for e in recent:
            text += f"• <b>{e['username'] or '?'}</b>: {e['event_text']}\n"
    await m.answer(text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= NPC =================
@dp.message(Command("npc"))
async def npc_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты в бою!"); return
    code = u.get("location_code", "village")
    npcs = W.get_npcs_in_location(code)
    if not npcs:
        await m.answer("👤 В этой локации нет NPC.", reply_markup=MAIN_KB); return
    loc_name = W.get_location(code).get("name", "?")
    await m.answer(f"👤 <b>NPC в «{loc_name}»</b>\n\nВыбери, с кем поговорить:",
                   reply_markup=npc_list_kb(code), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "npc_close")
async def npc_close(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@dp.callback_query(F.data.startswith("npc_") & ~F.data.startswith("npcquest_") & ~F.data.startswith("npctalk_"))
async def npc_pick(c: CallbackQuery):
    if c.data == "npc_close":
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await c.answer(); return
    code = c.data.replace("npc_", "")
    npc = W.get_npc(code)
    if not npc:
        await c.answer("Не найдено"); return
    text = f"👤 <b>{npc['name']}</b>\n\n<i>{npc['greeting']}</i>"
    await c.message.edit_text(text, reply_markup=npc_menu_kb(code),
                              parse_mode=ParseMode.HTML)
    await c.answer()


@dp.callback_query(F.data.startswith("npctalk_"))
async def npc_talk(c: CallbackQuery):
    code = c.data.replace("npctalk_", "")
    npc = W.get_npc(code)
    if not npc:
        await c.answer("Не найдено"); return
    await c.answer()
    await c.message.answer(
        f"💬 <i>{npc['name']} смотрит на тебя, ожидая, что ты скажешь.</i>\n\n"
        f"Просто напиши, что говоришь — ИИ ответит от лица NPC.",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("npcquest_"))
async def npc_quest_open(c: CallbackQuery):
    if c.data.startswith("npcquest_accept_") or c.data.startswith("npcquest_done_"):
        return
    qcode = c.data.replace("npcquest_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    u = await db.get_user(c.from_user.id)
    if u["level"] < q.get("req_level", 1):
        await c.answer(f"Нужен уровень {q['req_level']}+", show_alert=True); return
    prog = await db.get_npc_quest(c.from_user.id, qcode)
    if prog and prog["completed"]:
        await c.answer("Этот квест уже выполнен", show_alert=True); return
    if prog:
        text = (f"📜 <b>{q['title']}</b>\n\n{q['desc']}\n\n"
                f"Прогресс: {prog['progress']}/{q['count']}\n"
                f"Награда: {q['reward_gold']}💰 + {q['reward_xp']} XP")
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сдать",
                                  callback_data=f"npcquest_done_{qcode}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"npc_{q['npc']}")],
        ]), parse_mode=ParseMode.HTML)
        return
    text = (f"📜 <b>{q['title']}</b>\n\n{q['desc']}\n\n"
            f"Награда: {q['reward_gold']}💰 + {q['reward_xp']} XP")
    if q.get("reward_item"):
        text += f"\n🎁 Предмет: {q['reward_item']}"
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять",
                              callback_data=f"npcquest_accept_{qcode}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"npc_{q['npc']}")],
    ]), parse_mode=ParseMode.HTML)
    await c.answer()


@dp.callback_query(F.data.startswith("npcquest_accept_"))
async def npc_quest_accept(c: CallbackQuery):
    qcode = c.data.replace("npcquest_accept_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    ok = await db.accept_npc_quest(c.from_user.id, qcode)
    if not ok:
        await c.answer("Квест уже активен", show_alert=True); return
    await c.answer("Квест принят!")
    await c.message.edit_text(
        f"📜 <b>{q['title']}</b> — принят!\n\n{q['desc']}",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("npcquest_done_"))
async def npc_quest_done(c: CallbackQuery):
    qcode = c.data.replace("npcquest_done_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    prog = await db.get_npc_quest(c.from_user.id, qcode)
    if not prog or prog["completed"]:
        await c.answer("Уже сдано", show_alert=True); return
    if prog["progress"] < q["count"]:
        await c.answer(f"Не готово: {prog['progress']}/{q['count']}", show_alert=True); return
    await db.complete_npc_quest(c.from_user.id, qcode)
    await db.add_gold(c.from_user.id, q["reward_gold"])
    await db.add_xp(c.from_user.id, q["reward_xp"])
    if q.get("reward_item"):
        await db.add_item(c.from_user.id, q["reward_item"])
    text = (f"✅ <b>Квест выполнен: {q['title']}</b>\n\n"
            f"+{q['reward_gold']}💰 · +{q['reward_xp']} XP")
    if q.get("reward_item"):
        text += f"\n🎁 Получен: {q['reward_item']}"
    all_q = await db.get_user_quests(c.from_user.id)
    done_count = sum(1 for x in all_q if x["completed"])
    if done_count >= 5:
        if await db.add_achievement(c.from_user.id, "quest_master"):
            text += "\n\n🏆 Достижение: 📜 Мастер квестов"
    await c.answer("Квест сдан!")
    await c.message.edit_text(text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= ГИЛЬДИИ =================
@dp.message(Command("guild"))
@dp.message(F.text == "🏛 Гильдия")
async def guild_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    g = await db.get_user_guild(m.from_user.id)
    if g:
        text = (f"🏛 <b>[{g['tag']}] {g['name']}</b>\n\n"
                f"Уровень: {g['level']}\nКазна: {g['treasury']}💰")
        await m.answer(text, reply_markup=guild_menu_kb(True), parse_mode=ParseMode.HTML)
    else:
        await m.answer(
            "🏛 <b>Гильдии</b>\n\nТы не в гильдии. Создай свою.\n\n"
            f"Стоимость: <b>{W.GUILD_CREATE_COST}💰</b>",
            reply_markup=guild_menu_kb(False), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "guild_top")
async def guild_top_cb(c: CallbackQuery):
    guilds = await db.get_guilds_top(10)
    if not guilds:
        await c.answer("Пока нет гильдий", show_alert=True); return
    lines = ["🏆 <b>Топ гильдий</b>\n"]
    for i, g in enumerate(guilds):
        medals = ["🥇", "🥈", "🥉"]
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} <b>[{g['tag']}] {g['name']}</b> — ур.{g['level']}, {g['members']} чел.")
    await c.message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    await c.answer()


@dp.callback_query(F.data == "guild_create_start")
async def guild_create_start(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if u["gold"] < W.GUILD_CREATE_COST:
        await c.answer(f"Нужно {W.GUILD_CREATE_COST}💰", show_alert=True); return
    if await db.get_user_guild(c.from_user.id):
        await c.answer("Ты уже в гильдии", show_alert=True); return
    await c.answer()
    await c.message.answer(
        f"🏛 Напиши название и тег:\nФормат: <code>Название | ТЕГ</code>\n"
        f"Пример: <code>Тёмный Легион | TL</code>\n\n"
        f"Тег до {W.GUILD_TAG_MAX}, название до {W.GUILD_NAME_MAX}.",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text.regexp(r"^[^|]+\|[^|]+$"))
async def guild_create_input(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        return
    if await db.get_user_guild(m.from_user.id):
        return
    parts = m.text.split("|", 1)
    name = parts[0].strip()[:W.GUILD_NAME_MAX]
    tag = parts[1].strip()[:W.GUILD_TAG_MAX].upper()
    if len(name) < 3 or len(tag) < 2:
        await m.answer("Слишком коротко. Название 3+, тег 2+."); return
    if u["gold"] < W.GUILD_CREATE_COST:
        await m.answer(f"Нужно {W.GUILD_CREATE_COST}💰"); return
    gid = await db.create_guild(name, tag, m.from_user.id)
    if not gid:
        await m.answer("Название уже занято."); return
    await db.spend_gold(m.from_user.id, W.GUILD_CREATE_COST)
    await db.add_achievement(m.from_user.id, "guild_founder")
    await m.answer(
        f"🏛 <b>Гильдия создана!</b>\n\n<b>[{tag}] {name}</b>\n\n"
        f"Приглашай через /guild_invite Ник",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


@dp.message(Command("guild_invite"))
async def guild_invite(m: Message):
    u = await db.get_user(m.from_user.id)
    g = await db.get_user_guild(m.from_user.id)
    if not g:
        await m.answer("Ты не в гильдии."); return
    if g["leader_id"] != m.from_user.id:
        await m.answer("Только лидер может приглашать."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /guild_invite Ник"); return
    target = await db.get_user_by_char_name(parts[1].strip())
    if not target:
        await m.answer("Игрок не найден."); return
    if await db.get_user_guild(target["user_id"]):
        await m.answer("Он уже в гильдии."); return
    await db.add_guild_member(target["user_id"], g["id"])
    await db.add_achievement(target["user_id"], "guild_member")
    try:
        await bot.send_message(target["user_id"],
            f"🏛 Ты принят в гильдию <b>[{g['tag']}] {g['name']}</b>!",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await m.answer(f"✅ {target['char_name']} принят в гильдию.")


@dp.callback_query(F.data == "guild_info")
async def guild_info_cb(c: CallbackQuery):
    g = await db.get_user_guild(c.from_user.id)
    if not g:
        await c.answer("Не в гильдии"); return
    members = await db.get_guild_members(g["id"])
    owned = [x for x in await db.get_all_captured_locations() if x["guild_id"] == g["id"]]
    text = (f"🏛 <b>[{g['tag']}] {g['name']}</b>\n\n"
            f"Уровень: {g['level']}\n"
            f"Участников: {len(members)}\n"
            f"Захвачено: {len(owned)}")
    await c.message.answer(text, parse_mode=ParseMode.HTML)
    await c.answer()


@dp.callback_query(F.data == "guild_members")
async def guild_members_cb(c: CallbackQuery):
    g = await db.get_user_guild(c.from_user.id)
    if not g:
        await c.answer("Не в гильдии"); return
    members = await db.get_guild_members(g["id"])
    lines = [f"👥 <b>Участники [{g['tag']}] {g['name']}</b>\n"]
    for mm in members:
        rank_icon = "👑" if mm["rank"] == "leader" else "•"
        lines.append(f"{rank_icon} <b>{mm['char_name']}</b> — ур.{mm['level']}")
    await c.message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    await c.answer()


@dp.callback_query(F.data == "guild_leave")
async def guild_leave_cb(c: CallbackQuery):
    g = await db.get_user_guild(c.from_user.id)
    if not g:
        await c.answer("Не в гильдии"); return
    if g["leader_id"] == c.from_user.id:
        await c.answer("Лидер не может выйти.", show_alert=True); return
    await db.remove_guild_member(c.from_user.id)
    await c.answer("Ты вышел из гильдии")
    try:
        await c.message.edit_text("🚪 Ты покинул гильдию.")
    except Exception:
        pass


@dp.callback_query(F.data == "guild_capture")
async def guild_capture_cb(c: CallbackQuery):
    g = await db.get_user_guild(c.from_user.id)
    if not g:
        await c.answer("Не в гильдии"); return
    u = await db.get_user(c.from_user.id)
    code = u.get("location_code", "village")
    loc = W.get_location(code)
    if loc.get("type") == "safe":
        await c.answer("Мирные локации нельзя захватывать", show_alert=True); return
    players = await db.get_players_at_location(code, 0)
    my_count = len([p for p in players if p.get("guild_id") == g["id"]]) + 1
    if my_count < 3:
        await c.answer(f"Нужно 3+ членов гильдии здесь (сейчас {my_count})", show_alert=True)
        return
    owner = await db.get_location_owner(code)
    if owner and owner["guild_id"] == g["id"]:
        await c.answer("Локация уже твоя", show_alert=True); return
    await db.capture_location(code, g["id"])
    await db.add_achievement(c.from_user.id, "conqueror")
    await db.add_world_event(c.from_user.id, u["username"],
                             f"гильдия [{g['tag']}] захватила «{loc['name']}»")
    await broadcast_to_location(
        code,
        f"🏴 <b>Гильдия [{g['tag']}] {g['name']}</b> захватила «{loc['name']}»!",
        0
    )
    await c.answer("Захвачено!")
    await c.message.answer(
        f"🏴 <b>Локация «{loc['name']}» захвачена!</b>\n\n"
        f"Члены гильдии получают +15% золота и +10% XP здесь.",
        reply_markup=MAIN_KB, parse_mode=ParseMode.HTML
    )


# ================= ДУЭЛИ =================
@dp.message(Command("duel"))
async def duel_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты уже в бою!"); return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("/duel Имя — ставка 10%\n/duel Имя 100 — своя"); return
    target = await db.get_user_by_char_name(parts[1])
    if not target:
        await m.answer(f"❌ «{parts[1]}» не найден."); return
    if target["user_id"] == u["user_id"]:
        await m.answer("❌ Нельзя себя."); return
    if target.get("location_code") != u.get("location_code"):
        await m.answer(f"❌ {target['char_name']} в другой локации."); return
    if await db.get_combat(target["user_id"]):
        await m.answer(f"❌ {target['char_name']} уже в бою."); return
    if len(parts) >= 3:
        try:
            stake = int(parts[2])
        except ValueError:
            await m.answer("Ставка числом."); return
        if stake < 10:
            await m.answer("Минимум 10💰"); return
    else:
        stake = max(10, int(u["gold"] * 0.10))
    if u["gold"] < stake:
        await m.answer(f"❌ У тебя нет {stake}💰"); return
    if target["gold"] < stake:
        await m.answer(f"❌ У {target['char_name']} нет {stake}💰"); return
    oid = await db.create_duel_offer(u["user_id"], u["char_name"],
                                     target["user_id"], target["char_name"], stake)
    try:
        await bot.send_message(target["user_id"],
            f"⚔️ <b>Тебя вызывает {u['char_name']}!</b>\n\nСтавка: <b>{stake}💰</b>",
            reply_markup=duel_offer_kb(oid, is_caller=False), parse_mode=ParseMode.HTML)
    except Exception:
        await m.answer("❌ Не удалось отправить вызов."); return
    await m.answer(f"⚔️ Вызов отправлен <b>{target['char_name']}</b>!",
                   reply_markup=duel_offer_kb(oid, is_caller=True),
                   parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("duel_accept_"))
async def duel_accept(c: CallbackQuery):
    oid = int(c.data.replace("duel_accept_", ""))
    offer = await db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Уже неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой вызов"); return
    a = await db.get_user(offer["challenger_id"])
    b = await db.get_user(offer["opponent_id"])
    stake = offer["stake"]
    if a["gold"] < stake or b["gold"] < stake:
        await c.answer("Не хватает золота", show_alert=True)
        await db.set_duel_status(oid, "cancelled"); return
    await db.set_duel_status(oid, "accepted")
    for p in (a, b):
        nm = calc_max_hp(p)
        await db.update_hp_max(p["user_id"], nm, nm)
        p["hp"] = nm; p["max_hp"] = nm
    await db.start_pvp_combat(a, b, stake)
    try:
        await c.message.edit_text("✅ Дуэль началась!")
    except Exception:
        pass
    await send_pvp_state(a["user_id"], a, await db.get_combat(a["user_id"]))
    await send_pvp_state(b["user_id"], b, await db.get_combat(b["user_id"]))
    await c.answer("Начали!")


@dp.callback_query(F.data.startswith("duel_decline_"))
async def duel_decline(c: CallbackQuery):
    oid = int(c.data.replace("duel_decline_", ""))
    offer = await db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Уже неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой"); return
    await db.set_duel_status(oid, "declined")
    await db.add_reputation(c.from_user.id, -1)
    try:
        await c.message.edit_text("🏳️ Отказ. Репутация: −1")
    except Exception:
        pass
    try:
        await bot.send_message(offer["challenger_id"],
                               f"🏳️ {offer['opponent_name']} отказался.")
    except Exception:
        pass
    if await db.add_achievement(c.from_user.id, "coward"):
        await c.message.answer("🏆 Достижение: 🏳️ Трус")
    await c.answer()


@dp.callback_query(F.data.startswith("duel_cancel_"))
async def duel_cancel(c: CallbackQuery):
    oid = int(c.data.replace("duel_cancel_", ""))
    offer = await db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Неактивно"); return
    if c.from_user.id != offer["challenger_id"]:
        await c.answer("Не твой"); return
    await db.set_duel_status(oid, "cancelled")
    try:
        await c.message.edit_text("❌ Отменено.")
    except Exception:
        pass
    try:
        await bot.send_message(offer["opponent_id"], "❌ Вызов отменён.")
    except Exception:
        pass
    await c.answer()


PENDING_COUNTER = {}


@dp.callback_query(F.data.startswith("duel_counter_"))
async def duel_counter(c: CallbackQuery):
    oid = int(c.data.replace("duel_counter_", ""))
    offer = await db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой"); return
    PENDING_COUNTER[c.from_user.id] = oid
    await c.answer()
    await c.message.answer("💰 Введи свою ставку числом.")


@dp.message(F.text.regexp(r"^\d+$"))
async def counter_stake_handler(m: Message):
    uid = m.from_user.id
    if uid not in PENDING_COUNTER:
        return
    oid = PENDING_COUNTER.pop(uid)
    try:
        new_stake = int(m.text.strip())
    except ValueError:
        return
    if new_stake < 10:
        await m.answer("Минимум 10💰"); return
    offer = await db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await m.answer("Неактивно"); return
    ch = await db.get_user(offer["challenger_id"])
    me = await db.get_user(offer["opponent_id"])
    if ch["gold"] < new_stake or me["gold"] < new_stake:
        await m.answer("У кого-то не хватает золота"); return
    await db.set_duel_status(oid, "cancelled")
    new_oid = await db.create_duel_offer(offer["opponent_id"], offer["opponent_name"],
                                         offer["challenger_id"], offer["challenger_name"],
                                         new_stake)
    await m.answer(f"💰 Встречная ставка: {new_stake}💰")
    try:
        await bot.send_message(offer["challenger_id"],
            f"💰 <b>{offer['opponent_name']}</b> предлагает {new_stake}💰",
            reply_markup=duel_offer_kb(new_oid, is_caller=False), parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= PVP =================
@dp.callback_query(F.data == "pvp_attack")
async def pvp_attack_cb(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or not combat.get("is_pvp"):
        await c.answer("Неактивно"); return
    if not combat["my_turn"]:
        await c.answer("Не твой ход!", show_alert=True); return
    eff = effective_stats(user)
    dmg = int((eff["str"] * 2 + eff["dex"] + random.randint(0, 5)) * faction_mult(user, "dmg_mult"))
    is_crit = random.randint(1, 100) <= eff["dex"]
    if is_crit:
        dmg = int(dmg * 2)
    res = await db.pvp_damage(c.from_user.id, dmg)
    if not res:
        await c.answer("Ошибка"); return
    opp_hp, opp_id = res
    await c.answer(f"Нанесено {dmg}{' КРИТ' if is_crit else ''}")
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if opp_hp <= 0:
        await pvp_end(winner_id=c.from_user.id, loser_id=opp_id, stake=combat["stake"])
        return
    await db.pvp_switch_turn(c.from_user.id)
    try:
        opp_user = await db.get_user(opp_id)
        opp_combat = await db.get_combat(opp_id)
        await bot.send_message(opp_id,
            f"💔 <b>{user['char_name']}</b> бьёт на {dmg}!" + (" 💥 КРИТ" if is_crit else ""),
            parse_mode=ParseMode.HTML)
        await send_pvp_state(opp_id, opp_user, opp_combat)
    except Exception:
        pass
    new_combat = await db.get_combat(c.from_user.id)
    await send_pvp_state(c.from_user.id, await db.get_user(c.from_user.id), new_combat)


@dp.callback_query(F.data == "pvp_surrender")
async def pvp_surrender_cb(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or not combat.get("is_pvp"):
        await c.answer("Неактивно"); return
    opp_id = combat["opponent_id"]
    stake = combat["stake"]
    await db.end_combat(c.from_user.id)
    await db.end_combat(opp_id)
    await db.spend_gold(c.from_user.id, min(stake, user["gold"]))
    await db.add_gold(opp_id, stake)
    await db.add_reputation(c.from_user.id, -1)
    await db.incr_pvp_losses(c.from_user.id)
    await db.incr_pvp_wins(opp_id)
    await db.add_reputation(opp_id, 1)
    ou = await db.get_user(opp_id)
    nm = calc_max_hp(ou)
    await db.update_hp_max(opp_id, nm, nm)
    await c.message.edit_text(f"🏳️ Сдался. {stake}💰 ушло {combat['enemy_name']}.")
    try:
        await bot.send_message(opp_id,
            f"🏆 Победа! {user['char_name']} сдался. +{stake}💰",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer()


async def pvp_end(winner_id, loser_id, stake):
    await db.end_combat(winner_id)
    await db.end_combat(loser_id)
    w = await db.get_user(winner_id)
    l = await db.get_user(loser_id)
    real = min(stake, l["gold"])
    await db.spend_gold(loser_id, real)
    await db.add_gold(winner_id, real)
    await db.incr_pvp_wins(winner_id)
    await db.incr_pvp_losses(loser_id)
    await db.add_reputation(winner_id, 1)
    await db.add_reputation(loser_id, -1)
    for p in (w, l):
        nm = calc_max_hp(p)
        await db.update_hp_max(p["user_id"], nm, nm)
    await db.add_world_event(winner_id, w["username"],
                             f"победил {l['char_name']} в дуэли ({real}💰)")
    await db.add_achievement(winner_id, "duelist")
    wu = await db.get_user(winner_id)
    if wu["pvp_wins"] >= 5:
        if await db.add_achievement(winner_id, "arena_king"):
            try:
                await bot.send_message(winner_id, "🏆 ⚜️ Гроза арены",
                                       parse_mode=ParseMode.HTML)
            except Exception:
                pass
    await db.progress_quest(winner_id, "win_duels", 1)
    try:
        await bot.send_message(winner_id,
            f"🏆 <b>ПОБЕДА!</b> над {l['char_name']}\n+{real}💰 · Репутация +1",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        await bot.send_message(loser_id,
            f"💀 <b>Поражение</b> от {w['char_name']}\n−{real}💰 · Репутация −1",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= ПИТОМЕЦ =================
@dp.message(Command("pet"))
@dp.message(F.text == "🐾 Питомец")
async def pet_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    pet = await db.get_pet(m.from_user.id)
    if pet:
        pet_info = PETS.get(pet["pet_type"], {})
        await m.answer(
            f"🐾 <b>{pet['name']}</b> ({pet_info.get('name', '?')})\n"
            f"Уровень: {pet['level']}\nXP: {pet['xp']}/{pet['level'] * 100}\n\n"
            f"<b>Эффект:</b> {pet_info.get('desc', '—')}\n"
            f"<b>Пассивно:</b> " + ", ".join(f"+{v} {k.upper()}"
                                              for k, v in pet_info.get("bonus", {}).items()) +
            f"\n\n<i>Переименовать: /pet_name НовоеИмя</i>",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
        return
    text = "🐾 <b>Питомцы</b>\n\nВыбери верного спутника:\n\n"
    buttons = []
    for code, p in PETS.items():
        text += f"• <b>{p['name']}</b> ({p['price']}💰) — {p['desc']}\n"
        buttons.append([InlineKeyboardButton(text=f"{p['name']} — {p['price']}💰",
                                             callback_data=f"pet_buy_{code}")])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("pet_buy_"))
async def pet_buy(c: CallbackQuery):
    code = c.data.replace("pet_buy_", "")
    if code not in PETS:
        await c.answer("Нет"); return
    p = PETS[code]
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin:
        ok = await db.spend_gold(c.from_user.id, p["price"])
        if not ok:
            await c.answer(f"❌ Нужно {p['price']}💰", show_alert=True); return
    await db.add_pet(c.from_user.id, code, p["name"])
    await c.answer(f"✅ {p['name']} теперь с тобой!")
    await c.message.answer(f"🐾 <b>{p['name']}</b> присоединился!\n\nЭффект: {p['desc']}",
                           reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    if await db.add_achievement(c.from_user.id, "pet_owner"):
        await c.message.answer("🏆 Достижение: 🐾 Хозяин", parse_mode=ParseMode.HTML)


@dp.message(Command("pet_name"))
async def pet_name_cmd(m: Message):
    pet = await db.get_pet(m.from_user.id)
    if not pet:
        await m.answer("У тебя нет питомца."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or len(parts[1].strip()) < 2:
        await m.answer("Использование: /pet_name Имя (2–20)"); return
    name = parts[1].strip()[:20]
    await db.set_pet_name(m.from_user.id, name)
    await m.answer(f"🐾 Питомец теперь зовётся <b>{name}</b>!", parse_mode=ParseMode.HTML)


# ================= ПОДЗЕМЕЛЬЯ =================
@dp.message(Command("dungeon"))
@dp.message(F.text == "🏰 Подземелья")
async def dungeon_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты в бою!"); return
    if u.get("dungeon_id"):
        d = DUNGEONS.get(u["dungeon_id"], {})
        await m.answer(
            f"🏰 Ты уже в подземелье: <b>{d.get('name', '?')}</b>\n"
            f"Комната {u['dungeon_room']}/{d.get('rooms', '?')}\n"
            f"💰 Добыча: {u['dungeon_loot_gold']}\n\n"
            f"/dungeon_continue — продолжить\n/dungeon_exit — выйти",
            parse_mode=ParseMode.HTML)
        return
    text = "🏰 <b>Подземелья</b>\n\n"
    buttons = []
    for code, d in DUNGEONS.items():
        can = u["level"] >= d["level_req"] and u["gold"] >= d["entry"]
        mark = "✅" if can else "🔒"
        text += (f"{mark} <b>{d['name']}</b>\n"
                 f"  Ур.{d['level_req']}+ · вход {d['entry']}💰 · комнат {d['rooms']}\n")
        if can:
            buttons.append([InlineKeyboardButton(text=f"{d['name']} — {d['entry']}💰",
                                                 callback_data=f"dungeon_enter_{code}")])
    text += "\n<i>Цепочка боёв, в конце босс. Смерть = потеря добычи.</i>"
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("dungeon_enter_"))
async def dungeon_enter(c: CallbackQuery):
    code = c.data.replace("dungeon_enter_", "")
    if code not in DUNGEONS:
        await c.answer("Нет"); return
    d = DUNGEONS[code]
    u = await db.get_user(c.from_user.id)
    is_admin = c.from_user.id in ADMIN_IDS
    if u["level"] < d["level_req"]:
        await c.answer(f"Нужен {d['level_req']} уровень", show_alert=True); return
    if not is_admin:
        if not await db.spend_gold(c.from_user.id, d["entry"]):
            await c.answer(f"Нужно {d['entry']}💰", show_alert=True); return
    await db.start_dungeon(c.from_user.id, code)
    await c.answer("Вход!")
    await c.message.answer(f"🏰 Входишь в <b>{d['name']}</b>...", parse_mode=ParseMode.HTML)
    await spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, code, 1)


async def spawn_dungeon_enemy(chat_id, uid, dungeon_id, room):
    d = DUNGEONS[dungeon_id]
    enemy_name = d["enemies"][min(room - 1, len(d["enemies"]) - 1)]
    is_boss = 1 if room == d["rooms"] else 0
    base_level = d["level_req"] + room - 1
    enemy_level = base_level + (2 if is_boss else 0)
    enemy_hp = enemy_level * (30 if is_boss else 20)
    await db.start_combat(uid, enemy_name, enemy_level, enemy_hp, boss=is_boss, dungeon=1)
    u = await db.get_user(uid)
    combat = await db.get_combat(uid)
    label = "🐉 БОСС" if is_boss else f"Комната {room}/{d['rooms']}"
    await send_combat_state(chat_id, u, combat, f"🏰 <b>{label}</b>")


@dp.message(Command("dungeon_continue"))
async def dungeon_continue_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u.get("dungeon_id"):
        await m.answer("Ты не в подземелье."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return
    d = DUNGEONS.get(u["dungeon_id"])
    next_room = u["dungeon_room"] + 1
    if next_room > d["rooms"]:
        await dungeon_finish(m.chat.id, m.from_user.id, "Ты прошёл все комнаты!")
        return
    await db.advance_dungeon(m.from_user.id, 0, u["dungeon_loot_items"])
    await spawn_dungeon_enemy(m.chat.id, m.from_user.id, u["dungeon_id"], next_room)


@dp.message(Command("dungeon_exit"))
async def dungeon_exit_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u.get("dungeon_id"):
        await m.answer("Ты не в подземелье."); return
    if await db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return
    await dungeon_finish(m.chat.id, m.from_user.id, "Ты покидаешь подземелье с добычей.")


@dp.callback_query(F.data == "dungeon_next")
async def dungeon_next_cb(c: CallbackQuery):
    u = await db.get_user(c.from_user.id)
    if not u.get("dungeon_id"):
        await c.answer("Не в подземелье"); return
    if await db.get_combat(c.from_user.id):
        await c.answer("Бой!"); return
    d = DUNGEONS.get(u["dungeon_id"])
    next_room = u["dungeon_room"] + 1
    if next_room > d["rooms"]:
        await c.message.edit_reply_markup(reply_markup=None)
        await dungeon_finish(c.message.chat.id, c.from_user.id, "Подземелье пройдено!")
        return
    await db.advance_dungeon(c.from_user.id, 0, u["dungeon_loot_items"])
    await c.message.edit_reply_markup(reply_markup=None)
    await spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, u["dungeon_id"], next_room)


@dp.callback_query(F.data == "dungeon_leave")
async def dungeon_leave_cb(c: CallbackQuery):
    await c.message.edit_reply_markup(reply_markup=None)
    await dungeon_finish(c.message.chat.id, c.from_user.id, "Ты выходишь с добычей.")


async def dungeon_finish(chat_id, uid, msg):
    u = await db.get_user(uid)
    loot_gold = u.get("dungeon_loot_gold", 0)
    try:
        loot_items = json.loads(u.get("dungeon_loot_items") or "[]")
    except Exception:
        loot_items = []
    if loot_gold:
        await db.add_gold(uid, loot_gold)
    for it in loot_items:
        await db.add_item(uid, it)
    await db.exit_dungeon(uid)
    text = f"🏁 <b>{msg}</b>\n\n💰 Золото: +{loot_gold}"
    if loot_items:
        text += f"\n🎒 Предметы: {', '.join(loot_items)}"
    await bot.send_message(chat_id, text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    await db.add_achievement(uid, "dungeon_1")


# ================= КУЗНИЦА =================
@dp.message(Command("craft"))
@dp.message(F.text == "⚒️ Кузница")
async def craft_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text = (f"⚒️ <b>Кузница</b>\n\n"
            f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · ✨ {u['mat_dust']} · 💎 {u['mat_crystal']}\n\n"
            f"<b>Действия:</b>\n"
            f"/dismantle Название — разобрать\n"
            f"/upgrade Название — улучшить (+1..+3)\n\n"
            f"<b>Рецепты:</b>\n")
    for result, r in CRAFT_RECIPES.items():
        text += (f"• <b>{result}</b> ← {r['count']}× {r['base']} + "
                 f"{r['mat_count']}× {MATERIAL_NAMES[r['mat']]}\n")
    buttons = [[InlineKeyboardButton(text=f"Создать {result}", callback_data=f"craft_{result}")]
               for result in CRAFT_RECIPES.keys()]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@dp.message(Command("dismantle"))
async def dismantle_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /dismantle Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя разобрать."); return
    inv = await db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    await db.remove_item(m.from_user.id, item_name)
    itype = SHOP[base_name]["type"]
    yields = {"weapon": [("iron", 2), ("crystal", 1)],
              "armor": [("leather", 2), ("iron", 1)],
              "accessory": [("dust", 2), ("crystal", 1)]}[itype]
    lines = []
    for mat, amt in yields:
        amt += lvl
        await db.add_material(m.from_user.id, mat, amt)
        lines.append(f"• {MATERIAL_NAMES[mat]}: +{amt}")
    await m.answer(f"⚒️ Разобрано: <b>{item_name}</b>\n\n" + "\n".join(lines),
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.message(Command("upgrade"))
async def upgrade_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /upgrade Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя улучшить."); return
    if lvl >= 3:
        await m.answer("❌ Максимум +3."); return
    inv = await db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    mat_needed = (lvl + 1) * 3
    gold_needed = (lvl + 1) * 100
    itype = SHOP[base_name]["type"]
    mat = {"weapon": "iron", "armor": "leather", "accessory": "crystal"}[itype]
    u = await db.get_user(m.from_user.id)
    if u[f"mat_{mat}"] < mat_needed:
        await m.answer(f"❌ Нужно {mat_needed}× {MATERIAL_NAMES[mat]}"); return
    if u["gold"] < gold_needed:
        await m.answer(f"❌ Нужно {gold_needed}💰"); return
    await db.spend_material(m.from_user.id, mat, mat_needed)
    await db.spend_gold(m.from_user.id, gold_needed)
    await db.remove_item(m.from_user.id, item_name)
    new_name = f"{base_name}+{lvl + 1}"
    await db.add_item(m.from_user.id, new_name)
    await m.answer(f"🔨 <b>{item_name}</b> → <b>{new_name}</b>",
                   reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
    if await db.add_achievement(m.from_user.id, "upgrader"):
        await m.answer("🏆 Достижение: 🔨 Улучшатель", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("craft_"))
async def craft_cb(c: CallbackQuery):
    result = c.data.replace("craft_", "")
    if result not in CRAFT_RECIPES:
        await c.answer("Нет"); return
    r = CRAFT_RECIPES[result]
    u = await db.get_user(c.from_user.id)
    inv = await db.get_inventory(c.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    have_base = inv_names.count(r["base"])
    have_mat = u[f"mat_{r['mat']}"]
    if have_base < r["count"]:
        await c.answer(f"Нужно {r['count']}× {r['base']} (есть {have_base})",
                       show_alert=True); return
    if have_mat < r["mat_count"]:
        await c.answer(f"Нужно {r['mat_count']}× {MATERIAL_NAMES[r['mat']]}",
                       show_alert=True); return
    for _ in range(r["count"]):
        await db.remove_item(c.from_user.id, r["base"])
    await db.spend_material(c.from_user.id, r["mat"], r["mat_count"])
    await db.add_item(c.from_user.id, result)
    await c.answer(f"✅ Создано: {result}")
    await c.message.answer(f"⚒️ Ты создал <b>{result}</b>!", parse_mode=ParseMode.HTML)
    if await db.add_achievement(c.from_user.id, "crafter"):
        await c.message.answer("🏆 Достижение: ⚒️ Кузнец", parse_mode=ParseMode.HTML)
    await db.progress_quest(c.from_user.id, "craft_items", 1)


# ================= ОНБОРДИНГ =================
async def run_tutorial(uid, chat_id):
    step, finished = await db.get_tutorial_step(uid)
    if finished:
        return
    if step == 0:
        await bot.send_message(chat_id,
            "👋 <b>Добро пожаловать в мир!</b>\n\n"
            "Ты — герой в мире Lineage. Мир состоит из 12 локаций, "
            "соединённых дорогами. Исследуй, сражайся, становись сильнее.",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 1)
    elif step == 1:
        await bot.send_message(chat_id,
            "🚶 <b>Путешествия</b>\n\n"
            "Кнопка <b>🚶 Идти</b> — перемещает между локациями.\n"
            "Стартовая — Начальная деревня.",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 2)
    elif step == 2:
        await bot.send_message(chat_id,
            "📜 <b>NPC и квесты</b>\n\n"
            "В локациях живут NPC — Кузнец, Старейшина, Лесник. "
            "Команда /npc — открыть список NPC и взять квест.",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 3)
    elif step == 3:
        await bot.send_message(chat_id,
            "🏛 <b>Гильдии</b>\n\n"
            "Собери 1000💰 и создай гильдию. Гильдия может захватывать локации.",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 4)
    elif step == 4:
        await bot.send_message(chat_id,
            "🌍 <b>События</b>\n\n"
            "В локациях случаются нашествия, клады и мор. "
            "Проверяй /world — там видно, где сейчас жарко.",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 5)
    elif step == 5:
        await bot.send_message(chat_id,
            "💡 <b>Советы</b>\n\n"
            "• Заходи каждый день → 🎁 Награда\n"
            "• ⚒️ Кузница — крафт и улучшение предметов\n"
            "• 🐾 Питомец помогает в бою\n"
            "• /duel — сражайся с другими игроками\n"
            "• /quests — ежедневные квесты\n\n"
            "Удачи, герой! 🎮",
            parse_mode=ParseMode.HTML)
        await db.set_tutorial_step(uid, 99, finished=True)


@dp.message(Command("quests"))
@dp.message(F.text == "📋 Квесты")
async def quests_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя: /start"); return
    daily = await db.get_daily_quests(m.from_user.id)
    npc_active = await db.get_user_quests(m.from_user.id)
    quest_names = {
        "kill_enemies": "⚔️ Убить врагов",
        "visit_locations": "🗺 Посетить локации",
        "win_duels": "🗡 Победить в дуэлях",
        "craft_items": "⚒️ Создать предметы",
        "earn_gold": "💰 Заработать золото",
    }
    text = "📋 <b>Ежедневные квесты</b>\n\n"
    for q in daily:
        name = quest_names.get(q["quest_type"], q["quest_type"])
        done = "✅" if q["completed"] else "⏳"
        text += (f"{done} <b>{name}</b>\n"
                 f"   {q['progress']}/{q['target']} · {q['reward_gold']}💰 +{q['reward_xp']} XP\n\n")
    active_npc = [x for x in npc_active if not x["completed"]]
    done_npc = [x for x in npc_active if x["completed"]]
    if active_npc:
        text += "\n📜 <b>Активные NPC-квесты:</b>\n"
        for x in active_npc:
            q = W.get_quest(x["quest_code"])
            if q:
                text += f"• {q['title']} — {x['progress']}/{q['count']}\n"
    if done_npc:
        text += f"\n✅ Выполнено NPC-квестов: {len(done_npc)}"
    await m.answer(text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


# ================= НАГРАДА / ПРЕМИУМ / ПОМОЩЬ =================
@dp.message(Command("daily"))
@dp.message(F.text == "🎁 Награда")
async def daily(m: Message):
    streak = await db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer("🎁 Уже получал сегодня.", reply_markup=MAIN_KB); return
    bonus = {1: 5, 2: 5, 3: 10, 4: 10, 5: 15, 6: 15, 7: 30}.get(streak, 10)
    gold_bonus = streak * 20
    await db.add_gold(m.from_user.id, gold_bonus)
    await db.add_material(m.from_user.id, "iron", 1)
    msg = f"🎁 <b>Награда!</b>\n\nДень {streak}\n+{bonus} действий · +{gold_bonus}💰 · +1 🔩"
    if streak == 7:
        await db.add_item(m.from_user.id, "Амулет мудреца")
        msg += "\n\n🏆 <b>Амулет мудреца!</b>"
    await m.answer(msg, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.message(Command("premium"))
@dp.message(F.text == "💎 Премиум")
async def premium(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Купить за {PREMIUM_PRICE_STARS} ⭐",
                             callback_data="buy_premium")
    ]])
    await m.answer(
        f"💎 <b>Премиум</b>\n\n• Безлимит действий\n• Приоритет\n\n"
        f"Цена: {PREMIUM_PRICE_STARS} ⭐ / 30 дней",
        reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.message(Command("buy"))
async def buy(m: Message):
    await bot.send_invoice(
        chat_id=m.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium")


@dp.callback_query(F.data == "buy_premium")
async def buy_premium_cb(c: CallbackQuery):
    await bot.send_invoice(
        chat_id=c.message.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium")
    await c.answer()


@dp.pre_checkout_query()
async def pre_checkout(q):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(m: Message):
    await db.set_premium(m.from_user.id, 1)
    await m.answer("💎 <b>Оплата получена!</b>", reply_markup=MAIN_KB,
                   parse_mode=ParseMode.HTML)


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


# ================= АДМИН =================
@dp.message(Command("admin_help"))
async def admin_help(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    await m.answer(
        "🛠 <b>Админ-команды</b>\n\n"
        "/admin_reset — сброс лимита + HP\n"
        "/admin_gold N — золото\n"
        "/admin_hp — HP\n"
        "/admin_levelup — +1 уровень\n"
        "/admin_endcombat — завершить бой\n"
        "/admin_stats — строка БД\n"
        "/admin_give_item Название — предмет\n"
        "/admin_mats — +10 материалов\n"
        "/admin_resetquests — сбросить квесты\n"
        "/admin_resettutorial — сброс туториала\n"
        "/admin_teleport Код — телепорт\n"
        "/admin_event Код — событие\n"
        "/admin_spawn_event — случайное событие",
        parse_mode=ParseMode.HTML)


@dp.message(Command("admin_reset"))
async def admin_reset(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    u = await db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, nm, nm)
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE users SET requests_today=0 WHERE user_id=$1", m.from_user.id)
    await m.answer(f"🛠 HP: {nm}/{nm}", parse_mode=ParseMode.HTML)


@dp.message(Command("admin_gold"))
async def admin_gold(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("Использование: /admin_gold 5000"); return
    try:
        amount = int(parts[1])
    except ValueError:
        await m.answer("Число."); return
    await db.add_gold(m.from_user.id, amount)
    u = await db.get_user(m.from_user.id)
    await m.answer(f"🛠 {amount:+d}. Теперь: {u['gold']}💰")


@dp.message(Command("admin_hp"))
async def admin_hp(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    u = await db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, nm, nm)
    await m.answer(f"🛠 HP: {nm}/{nm}")


@dp.message(Command("admin_levelup"))
async def admin_levelup(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    await db.add_xp(m.from_user.id, 999999)
    u = await db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await db.update_hp_max(m.from_user.id, nm, nm)
    await m.answer(f"🛠 Ур.: {u['level']}. HP: {nm}/{nm}")


@dp.message(Command("admin_endcombat"))
async def admin_endcombat(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    combat = await db.get_combat(m.from_user.id)
    if combat and combat.get("is_pvp"):
        opp = combat["opponent_id"]
        await db.end_combat(opp)
        try:
            await bot.send_message(opp, "⚔️ Дуэль отменена.", reply_markup=MAIN_KB)
        except Exception:
            pass
    await db.end_combat(m.from_user.id)
    u = await db.get_user(m.from_user.id)
    if u.get("dungeon_id"):
        await db.exit_dungeon(m.from_user.id)
    await m.answer("🛠 Бой завершён.", reply_markup=MAIN_KB)


@dp.message(Command("admin_stats"))
async def admin_stats(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    u = await db.get_user(m.from_user.id)
    text = "\n".join(f"<code>{k}</code> = {v}" for k, v in u.items())
    await m.answer(f"🛠 <b>Строка БД</b>\n\n{text}", parse_mode=ParseMode.HTML)


@dp.message(Command("admin_give_item"))
async def admin_give_item(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /admin_give_item Железный меч"); return
    await db.add_item(m.from_user.id, parts[1].strip())
    await m.answer(f"🛠 Выдано: {parts[1].strip()}")


@dp.message(Command("admin_mats"))
async def admin_mats(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    for mat in ("iron", "leather", "dust", "crystal"):
        await db.add_material(m.from_user.id, mat, 10)
    await m.answer("🛠 +10 всех материалов.")


@dp.message(Command("admin_resetquests"))
async def admin_resetquests(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM daily_quests WHERE user_id=$1", m.from_user.id)
    await m.answer("🛠 Квесты сброшены.")


@dp.message(Command("admin_resettutorial"))
async def admin_resettutorial(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM tutorial_progress WHERE user_id=$1", m.from_user.id)
    await m.answer("🛠 Туториал сброшен.")


@dp.message(Command("admin_teleport"))
async def admin_teleport(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        codes = ", ".join(W.LOCATIONS.keys())
        await m.answer(f"Коды: {codes}"); return
    code = parts[1].strip().lower()
    if code not in W.LOCATIONS:
        await m.answer("Неизвестный код."); return
    loc = W.get_location(code)
    await db.set_location_code(m.from_user.id, code)
    await db.add_location(m.from_user.id, loc["name"])
    await m.answer(f"🛠 Перемещён в: {loc['name']}")


@dp.message(Command("admin_event"))
async def admin_event(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    parts = m.text.split()
    if len(parts) < 2:
        codes = ", ".join(W.LOCATIONS.keys())
        await m.answer(f"Использование: /admin_event <code>\nКоды: {codes}")
        return
    loc_code = parts[1].strip().lower()
    if loc_code not in W.LOCATIONS:
        await m.answer("Неизвестная локация."); return
    tpl = random.choice(W.EVENT_TEMPLATES)
    await db.create_world_event(
        loc_code, tpl["code"], tpl["name"], tpl["desc"],
        tpl["duration_min"], tpl["xp_mult"], tpl["gold_mult"],
        tpl["spawn_mult"], tpl.get("enemy_dmg_mult", 1.0)
    )
    loc_name = W.get_location(loc_code)["name"]
    await broadcast_to_location(
        loc_code,
        f"🌍 <b>Событие в {loc_name}</b>\n{tpl['name']}: <i>{tpl['desc']}</i>",
        0
    )
    await m.answer(f"🛠 Событие {tpl['name']} в {loc_name}.")


@dp.message(Command("admin_spawn_event"))
async def admin_spawn_event(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("❌"); return
    loc_code = random.choice(list(W.LOCATIONS.keys()))
    tpl = random.choice(W.EVENT_TEMPLATES)
    await db.create_world_event(
        loc_code, tpl["code"], tpl["name"], tpl["desc"],
        tpl["duration_min"], tpl["xp_mult"], tpl["gold_mult"],
        tpl["spawn_mult"], tpl.get("enemy_dmg_mult", 1.0)
    )
    loc_name = W.get_location(loc_code)["name"]
    await broadcast_to_location(
        loc_code,
        f"🌍 <b>Событие в {loc_name}</b>\n{tpl['name']}: <i>{tpl['desc']}</i>",
        0
    )
    await m.answer(f"🛠 Событие {tpl['name']} в {loc_name}.")


# ================= БОЙ С МОБАМИ =================
async def start_combat_from_ai(chat_id, user, enemy):
    await db.start_combat(user["user_id"], enemy["name"], enemy["level"],
                          enemy["hp"], 1 if enemy["is_boss"] else 0)
    combat = await db.get_combat(user["user_id"])
    intro = "🐉 <b>БОСС!</b>" if enemy["is_boss"] else "Бой начался!"
    event = await db.get_active_event(user.get("location_code", "village"))
    await send_combat_state(chat_id, user, combat, intro, event)


def pet_attack_damage(user, round_num):
    if not user.get("pet_type"):
        return 0, ""
    ptype = user["pet_type"]
    plvl = user.get("pet_level", 1)
    if ptype == "wolf":
        return 5 + plvl * 2, "🐺 Волк кусает"
    if ptype == "dragon":
        if round_num % 2 == 0:
            return 10 + plvl * 3, "🐉 Дракон дышит огнём"
        return 0, ""
    if ptype == "phoenix":
        return 0, ""
    if ptype == "owl":
        return 0, ""
    return 0, ""


async def process_combat_round(chat_id, user, combat, action_type, extra_text=""):
    event = await db.get_active_event(user.get("location_code", "village"))
    enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0

    if action_type == "attack":
        eff = effective_stats(user)
        dmg = int((eff["str"] * 2 + eff["dex"] + random.randint(0, 5)) * faction_mult(user, "dmg_mult"))
        crit_chance = eff["dex"]
        if user.get("pet_type") == "owl":
            crit_chance += 15
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit:
            dmg = int(dmg * 2)
        pet_dmg, pet_text = pet_attack_damage(user, combat["round_num"])
        total_dmg = dmg + pet_dmg
        new_enemy_hp = combat["enemy_hp"] - total_dmg
        await db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
        parts = []
        if is_crit:
            parts.append(f"💥 <b>КРИТ!</b> {dmg}")
        else:
            parts.append(f"⚔️ {dmg} урона.")
        if pet_dmg > 0:
            parts.append(f"{pet_text} — {pet_dmg}!")
        extra_text = "\n".join(parts)
        await db.set_combat_defending(user["user_id"], 0)

    elif action_type == "defend":
        await db.set_combat_defending(user["user_id"], 1)
        heal = int(user["max_hp"] * 0.05)
        new_hp = min(user["max_hp"], user["hp"] + heal)
        await db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text = f"🛡 +{heal} HP."
        enemy_dmg = max(1, int((combat["enemy_level"] * 5 + random.randint(0, 5)) * 0.5 * enemy_dmg_mult))
        new_hp = max(0, user["hp"] - enemy_dmg)
        await db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text += f"\n💔 {combat['enemy_name']} бьёт на {enemy_dmg}."
        if user["hp"] <= 0:
            await handle_death(chat_id, user, combat); return False
        await db.incr_combat_round(user["user_id"])
        await send_combat_state(chat_id, user,
                                await db.get_combat(user["user_id"]), extra_text, event)
        return True

    if new_enemy_hp <= 0:
        await handle_victory(chat_id, user, combat, extra_text)
        return False

    if user.get("pet_type") == "phoenix":
        plvl = user.get("pet_level", 1)
        heal = int(user["max_hp"] * 0.05) + plvl
        new_hp = min(user["max_hp"], user["hp"] + heal)
        if new_hp > user["hp"]:
            await db.update_hp(user["user_id"], new_hp)
            user["hp"] = new_hp
            extra_text += f"\n🔥 Феникс лечит +{heal} HP."

    enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) * enemy_dmg_mult)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await db.update_hp(user["user_id"], new_hp)
    user["hp"] = new_hp
    extra_text += f"\n💔 {combat['enemy_name']} наносит {enemy_dmg}."

    if user["hp"] <= 0:
        await handle_death(chat_id, user, combat); return False

    await db.incr_combat_round(user["user_id"])
    await send_combat_state(chat_id, user,
                            await db.get_combat(user["user_id"]), extra_text, event)
    return True


async def handle_victory(chat_id, user, combat, prefix_text):
    await db.end_combat(user["user_id"])

    # Прогресс NPC-квестов
    enemy_name = combat["enemy_name"]
    all_q = await db.get_user_quests(user["user_id"])
    for qrow in all_q:
        if qrow["completed"]:
            continue
        q = W.get_quest(qrow["quest_code"])
        if not q:
            continue
        if q["target"].lower() in enemy_name.lower():
            await db.incr_npc_quest(user["user_id"], qrow["quest_code"], 1)

    # Прогресс ежедневного "убить врагов"
    q = await db.progress_quest(user["user_id"], "kill_enemies", 1)
    if q and q.get("completed"):
        try:
            await bot.send_message(user["user_id"],
                f"✅ <b>Квест выполнен:</b> Убить врагов\n+{q['gold']}💰 · +{q['xp']} XP",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass

    exp = combat["enemy_level"] * 15
    gold = combat["enemy_level"] * 10
    is_dungeon = combat.get("is_dungeon", 0)
    if combat["is_boss"]:
        exp *= 3
        gold *= 3
    gold = int(gold * faction_mult(user, "gold_mult"))

    event = await db.get_active_event(user.get("location_code", "village"))
    xp_mult = event.get("xp_mult", 1.0) if event else 1.0
    gold_mult_ev = event.get("gold_mult", 1.0) if event else 1.0
    exp = int(exp * xp_mult)
    gold = int(gold * gold_mult_ev)

    if user.get("pet_type"):
        await db.add_pet_xp(user["user_id"], combat["enemy_level"] * 5)

    if is_dungeon:
        d = DUNGEONS.get(user.get("dungeon_id", ""), {})
        mult = d.get("reward_mult", 1.0)
        gold = int(gold * mult)
        try:
            items = json.loads(user.get("dungeon_loot_items") or "[]")
        except Exception:
            items = []
        if random.randint(1, 100) <= 40:
            items.append(random.choice(DROP_TABLE))
        await db.advance_dungeon(user["user_id"], gold, json.dumps(items))
        text = (f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
                f"<b>{combat['enemy_name']}</b> повержен!\n"
                f"💰 Добыча: +{gold}")
        u = await db.get_user(user["user_id"])
        d = DUNGEONS.get(u.get("dungeon_id", ""))
        if combat["is_boss"]:
            text += f"\n\n🐉 <b>БОСС ПОВЕРЖЕН!</b>"
        text += f"\n\n<b>Комната {u['dungeon_room']}/{d.get('rooms', '?')}</b>"
        if u["dungeon_room"] >= d.get("rooms", 1):
            await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            await dungeon_finish(chat_id, user["user_id"], "Подземелье пройдено!")
            return
            await bot.send_message(chat_id, text, reply_markup=dungeon_continue_kb(),
                               parse_mode=ParseMode.HTML)
        if combat["is_boss"]:
            await db.incr_bosses(user["user_id"])
        return

    # Не подземелье
    await db.add_gold(user["user_id"], gold)
    level, xp, leveled_up = await db.add_xp(user["user_id"], exp)
    text = (f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
            f"<b>{combat['enemy_name']}</b> повержен!\n"
            f"+{exp} XP · +{gold}💰")

    if event:
        text += f"\n<i>{event['event_name']} усиливает награду</i>"

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

    if user.get("pet_type") == "owl" and random.randint(1, 100) <= 20:
        mat = random.choice(["iron", "leather", "dust", "crystal"])
        await db.add_material(user["user_id"], mat, 1)
        text += f"\n🔨 Сова нашла: {MATERIAL_NAMES[mat]}"

    if leveled_up:
        u = await db.get_user(user["user_id"])
        nm = calc_max_hp(u)
        await db.update_hp_max(user["user_id"], nm, nm)
        text += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm}."
        if level in (5, 10):
            await db.add_world_event(user["user_id"], user["username"],
                                     f"достиг {level} уровня!")

    if await db.add_achievement(user["user_id"], "first_blood"):
        text += "\n🏆 Достижение: 🩸 Первая кровь"
    u = await db.get_user(user["user_id"])
    if u["bosses_defeated"] >= 5:
        if await db.add_achievement(user["user_id"], "boss_5"):
            text += "\n🏆 Достижение: 🐉 Легенда"

    await bot.send_message(chat_id, text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


async def handle_death(chat_id, user, combat):
    was_dungeon = combat.get("is_dungeon", 0)
    await db.end_combat(user["user_id"])
    if was_dungeon:
        await db.exit_dungeon(user["user_id"])
    lost = int(user["gold"] * 0.30)
    await db.set_gold(user["user_id"], user["gold"] - lost)
    u = await db.get_user(user["user_id"])
    nm = calc_max_hp(u)
    await db.update_hp_max(user["user_id"], nm, nm)
    await db.update_story(user["user_id"], "")
    await db.incr_deaths(user["user_id"])
    await db.add_achievement(user["user_id"], "survivor")
    await db.add_world_event(user["user_id"], user["username"],
                             f"пал в бою с «{combat['enemy_name']}»")
    text = (f"💀 <b>ТЫ ПАЛ В БОЮ</b>\n\n"
            f"<b>{combat['enemy_name']}</b> оказался сильнее.\n\n"
            f"Ты очнулся в Начальной деревне.\n"
            f"Жрецы забрали <b>{lost}💰</b> (30%).")
    if was_dungeon:
        text += "\n\n⚠️ <b>Вся добыча из подземелья потеряна!</b>"
    text += f"\n\n❤️ HP: {nm}/{nm}\n💰 Золото: {u['gold'] - lost}\n\n<i>Уровень и опыт сохранены.</i>"
    # Возвращаем в стартовую локацию
    await db.set_location_code(user["user_id"], "village")
    await bot.send_message(chat_id, text, reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "combat_attack")
async def cb_attack(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен."); return
    await c.answer("⚔️ Атака!")
    await process_combat_round(c.message.chat.id, user, combat, "attack")


@dp.callback_query(F.data == "combat_defend")
async def cb_defend(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен."); return
    await c.answer("🛡 Защита")
    await process_combat_round(c.message.chat.id, user, combat, "defend")


@dp.callback_query(F.data == "combat_potion")
async def cb_potion(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен."); return
    if user["hp"] >= user["max_hp"]:
        await c.answer("❤️ HP полное!", show_alert=True); return
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin and user["gold"] < POTION_PRICE:
        await c.answer(f"❌ Нужно {POTION_PRICE}💰", show_alert=True); return
    if not is_admin:
        await db.spend_gold(c.from_user.id, POTION_PRICE)
    new_hp = min(user["max_hp"], user["hp"] + POTION_HEAL)
    await db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    await c.answer(f"💚 +{POTION_HEAL} HP")
    event = await db.get_active_event(user.get("location_code", "village"))
    enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
    enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) * enemy_dmg_mult)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    if user["hp"] <= 0:
        await handle_death(c.message.chat.id, user, combat); return
    await db.incr_combat_round(c.from_user.id)
    await send_combat_state(c.message.chat.id, user,
                            await db.get_combat(c.from_user.id),
                            f"💚 Зелье +{POTION_HEAL}. 💔 Враг бьёт на {enemy_dmg}.",
                            event)


@dp.callback_query(F.data == "combat_flee")
async def cb_flee(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    combat = await db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен."); return
    if combat["is_boss"]:
        await c.answer("🐉 От босса не убежать!", show_alert=True); return
    if combat.get("is_dungeon"):
        await c.answer("🏰 Из подземелья не сбежать!", show_alert=True); return
    if random.randint(1, 100) <= 50:
        await db.end_combat(c.from_user.id)
        await c.answer("🏃 Побег!")
        await c.message.answer("🏃 Ты сбежал.", reply_markup=MAIN_KB)
    else:
        await c.answer("❌ Не удалось!")
        event = await db.get_active_event(user.get("location_code", "village"))
        enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
        enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) // 2 * enemy_dmg_mult)
        new_hp = max(0, user["hp"] - enemy_dmg)
        await db.update_hp(c.from_user.id, new_hp)
        user["hp"] = new_hp
        if user["hp"] <= 0:
            await handle_death(c.message.chat.id, user, combat); return
        await db.incr_combat_round(c.from_user.id)
        await send_combat_state(c.message.chat.id, user,
                                await db.get_combat(c.from_user.id),
                                f"❌ Побег не удался! -{enemy_dmg}.", event)


# ================= ДОСТИЖЕНИЯ =================
async def check_achievements(uid, user):
    new = []
    if user["action_count"] >= 1:
        if await db.add_achievement(uid, "first_step"): new.append("first_step")
    locs = await db.get_locations(uid)
    if len(locs) >= 5:
        if await db.add_achievement(uid, "explorer_5"): new.append("explorer_5")
    if len(locs) >= 10:
        if await db.add_achievement(uid, "explorer_10"): new.append("explorer_10")
    if len(locs) >= len(W.LOCATIONS):
        if await db.add_achievement(uid, "explorer_all"): new.append("explorer_all")
    items = await db.get_inventory(uid)
    if len(items) >= 5:
        if await db.add_achievement(uid, "collector_5"): new.append("collector_5")
    if user["level"] >= 5:
        if await db.add_achievement(uid, "level_5"): new.append("level_5")
    if user["level"] >= 10:
        if await db.add_achievement(uid, "level_10"): new.append("level_10")
    if user["level"] >= 20:
        if await db.add_achievement(uid, "level_20"): new.append("level_20")
    if user["referral_count"] >= 3:
        if await db.add_achievement(uid, "referral_3"): new.append("referral_3")
    if user["daily_streak"] >= 7:
        if await db.add_achievement(uid, "daily_7"): new.append("daily_7")
    if user["gold"] >= 1000:
        if await db.add_achievement(uid, "rich"): new.append("rich")
    return new


# ================= ОСНОВНОЙ ОБРАБОТЧИК =================
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
    if not user["faction"]:
        await show_faction_selection(m); return
    if not user["char_name"]:
        name = m.text.strip()[:20]
        if len(name) < 2:
            await m.answer("✏️ Имя 2–20 символов:"); return
        stats = calc_stats(user["race"], user["class"])
        hp_base = stats["con"] * 20 + 15
        user_tmp = {"faction": user["faction"], "level": 1, "stat_con": stats["con"],
                    "stat_str": stats["str"], "stat_dex": stats["dex"],
                    "stat_int": stats["int"], "stat_wit": stats["wit"],
                    "stat_men": stats["men"], "pet_type": None}
        hp = int(hp_base * faction_mult(user_tmp, "hp_mult"))
        await db.set_char(uid, name, stats, hp)
        await m.answer(
            f"🎉 <b>Герой создан!</b>\n\n"
            f"<b>{name}</b>\n"
            f"{RACES[user['race']]['name']} · {CLASSES[user['class']]['name']}\n"
            f"{FACTIONS[user['faction']]['name']}\n\n"
            f"STR {stats['str']} · DEX {stats['dex']} · CON {stats['con']}\n"
            f"INT {stats['int']} · WIT {stats['wit']} · MEN {stats['men']}\n"
            f"❤️ HP: {hp} · 💰 100\n\n"
            f"📍 Начальная деревня.",
            reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
        await run_tutorial(uid, m.chat.id)
        return

    combat = await db.get_combat(uid)
    if combat:
        if combat.get("is_pvp"):
            await m.answer("⚔️ Ты в дуэли!", reply_markup=pvp_kb(combat["my_turn"]))
        else:
            await m.answer("⚔️ Ты в бою! Жми кнопки.", reply_markup=combat_kb())
        return

    is_admin = uid in ADMIN_IDS
    if not is_admin and not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит исчерпан ({FREE_DAILY_LIMIT}).\n\n"
            "💎 Премиум · 👥 Друг · 🎁 Награда",
            reply_markup=MAIN_KB)
        return

    await bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]

    user_for_ai = dict(user)
    eff = effective_stats(user)
    for k in ["str", "dex", "con", "int", "wit", "men"]:
        user_for_ai[f"stat_{k}"] = eff[k]
    pet = await db.get_pet(uid)
    if pet:
        user_for_ai["pet_name"] = pet["name"]
        user_for_ai["pet_type"] = pet["pet_type"]
        user_for_ai["pet_level"] = pet["level"]

    loc_code = user.get("location_code", "village")
    event = await db.get_active_event(loc_code)
    owner = await db.get_location_owner(loc_code)

    result = await ai.generate(user["story"], action, user["arc"],
                                user_for_ai, event, owner)
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
        response += f"\n\n🎒 <i>+{result['item']}</i>"
    if result["location"]:
        # В новой системе ИИ не двигает игрока — только мы через кнопки
        # Но если ИИ вернул LOCATION, проверим — может это соседняя
        loc_name = result["location"]
        # Ищем совпадение с соседями
        for ncode, ninfo in W.get_neighbors(loc_code):
            if ninfo["name"].lower() == loc_name.lower() or loc_name.lower() in ninfo["name"].lower():
                can, reason = W.can_enter(ncode, user["level"])
                if can:
                    await db.set_location_code(uid, ncode)
                    await db.add_location(uid, ninfo["name"])
                    await db.progress_quest(uid, "visit_locations", 1)
                    response += f"\n\n📍 <i>Переход: {W.get_location(loc_code)['name']} → {ninfo['name']}</i>"
                else:
                    response += f"\n\n🚫 <i>{reason}</i>"
                break
        else:
            response += f"\n\n<i>📍 {loc_name}</i>"

    if result.get("material"):
        await db.add_material(uid, result["material"], 1)
        response += f"\n\n🔨 <i>+{MATERIAL_NAMES[result['material']]}</i>"
    if result["damage"] > 0:
        nhp = user["hp"] - result["damage"]
        await db.update_hp(uid, nhp)
        response += f"\n\n💔 <i>-{result['damage']} HP</i>"
        if nhp <= 0:
            await db.update_hp_max(uid, user["max_hp"], user["max_hp"])
            response += "\n\n💀 <i>Ты очнулся в деревне.</i>"
    if result["heal"] > 0:
        nhp = min(user["max_hp"], user["hp"] + result["heal"])
        await db.update_hp(uid, nhp)
        response += f"\n\n💚 <i>+{result['heal']} HP</i>"

    # Бонус гильдии за владение локацией
    gold_gain = int((5 + result["gold"]) * faction_mult(user, "gold_mult"))
    if owner and user.get("guild_id") and owner.get("guild_id") == user["guild_id"]:
        gold_gain = int(gold_gain * W.LOCATION_OWNER_BONUS["gold_mult"])
    if event:
        gold_gain = int(gold_gain * event.get("gold_mult", 1.0))
    await db.add_gold(uid, gold_gain)
    if gold_gain > 0:
        await db.progress_quest(uid, "earn_gold", gold_gain)

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    await db.update_story(uid, new_story)
    await db.increment(uid)
    await db.incr_action_count(uid)

    level, xp, leveled_up = await db.add_xp(uid, 10)
    if leveled_up:
        u = await db.get_user(uid)
        nm = calc_max_hp(u)
        await db.update_hp_max(uid, nm, nm)
        response += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm}/{nm}"
        if level in (5, 10):
            await db.add_world_event(uid, user["username"], f"достиг {level} уровня!")

    updated = await db.get_user(uid)
    new_ach = await check_achievements(uid, updated)
    if new_ach:
        ach_lines = "\n".join(f"• {ACHIEVEMENTS[c]}" for c in new_ach)
        response += f"\n\n🏆 <b>Достижение!</b>\n{ach_lines}"

    left = ("∞ (admin)" if is_admin
            else "∞" if user["is_premium"]
            else FREE_DAILY_LIMIT - user["requests_today"] - 1)
    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · 💰 {updated['gold']} · "
        f"❤️ {updated['hp']}/{updated['max_hp']} · Осталось: {left}</i>",
        parse_mode=ParseMode.HTML)


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


async def main():
    await db.connect()
    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
