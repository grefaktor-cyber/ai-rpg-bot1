"""Профиль игрока, рейтинги и достижения."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

from core.globals import bot, db
from core.utils import calc_stats, faction_mult

router = Router()


# ================= СПРАВОЧНИКИ =================
RACES = {
    "human":    "Человек",
    "elf":      "Эльф",
    "dark_elf": "Тёмный эльф",
    "orc":      "Орк",
    "prit":     "Плут",
    "demon":    "Демон",
    "angel":    "Ангел",
}

CLASSES = {
    "warrior":   "Воин",
    "knight":    "Рыцарь",
    "mage":      "Маг",
    "archer":    "Лучник",
    "assassin":  "Убийца",
    "necro":     "Некромант",
    "dancer":    "Танцор",
    "destroyer": "Разрушитель",
    "tyrant":    "Тиранин",
    "overlord":  "Владыка",
    "priest":    "Жрец",
    "bard":      "Певчий",
    "guardian":  "Страж",
    "hunter":    "Охотник",
    "defender":  "Защитник",
    "keeper":    "Хранитель",
}

FACTIONS = {
    "light": "Орден Света",
    "dark":  "Тёмное Братство",
}

ACHIEVEMENTS = {
    "first_step":   "🌟 Первый шаг",
    "explorer_5":   "🗺 Исследователь — 5 локаций",
    "explorer_10":  "🗺 Странник — 10 локаций",
    "explorer_all": "🌍 Покоритель мира",
    "collector_5":  "🎒 Коллекционер",
    "level_5":      "⭐ Опытный — 5 уровень",
    "level_10":     "👑 Ветеран — 10 уровень",
    "level_20":     "🔥 Легенда — 20 уровень",
    "first_boss":   "⚔️ Убийца боссов",
    "boss_5":       "🐉 Легенда — 5 боссов",
    "referral_3":   "👥 Друг друзей",
    "daily_7":      "🎁 Верный игрок",
    "rich":         "💰 Богач",
    "equipped":     "⚔️ Снаряжён",
    "survivor":     "💀 Выживший",
    "first_blood":  "🩸 Первая кровь",
    "duelist":      "🗡 Дуэлянт",
    "arena_king":   "⚜️ Гроза арены",
    "coward":       "🏳️ Трус",
    "social":       "👥 Общительный",
    "pet_owner":    "🐾 Хозяин",
    "pet_10":       "🐕 Друг навек",
    "dungeon_1":    "🏰 Пещерный ход",
    "crafter":      "⚒️ Кузнец",
    "upgrader":     "🔨 Улучшатель",
    "guild_founder":"🏛 Основатель гильдии",
    "guild_member": "🏛 Член гильдии",
    "conqueror":    "⚔️ Захватчик",
    "quest_master": "📜 Мастер квестов",
}


def _profile_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
            [KeyboardButton(text="📋 Квесты"),    KeyboardButton(text="🗺 Карта")],
            [KeyboardButton(text="🚶 Идти"),      KeyboardButton(text="🌍 Мир")],
            [KeyboardButton(text="👥 Кто здесь"), KeyboardButton(text="🐾 Питомец")],
            [KeyboardButton(text="🏰 Подземелья"),KeyboardButton(text="⚒️ Кузница")],
            [KeyboardButton(text="🏛 Гильдия"),   KeyboardButton(text="🎁 Награда")],
            [KeyboardButton(text="🔗 Реферал"),   KeyboardButton(text="🏅 Рейтинг")],
            [KeyboardButton(text="💎 Премиум"),   KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что делает герой?"
    )


# ================= /stats =================
@router.message(Command("stats"))
@router.message(F.text == "⭐ Профиль")
async def stats_cmd(m: Message):
    u = await db.get_user(m.from_user.id)
    if not u.get("race"):
        await m.answer("Сначала /start")
        return

    # Статы с экипировкой
    eff = calc_stats(u["race"], u["class"])
    for slot in ["equipped_weapon", "equipped_armor", "equipped_accessory"]:
        item_name = u.get(slot, "")
        if item_name:
            # Бонусы от предмета — заглушка, детали на Этапе 7
            pass

    need = u["level"] * u["level"] * 100
    faction_name = FACTIONS.get(u.get("faction", ""), "—")

    # Гильдия
    guild = await db.get_user_guild(m.from_user.id)
    guild_line = ""
    if guild:
        guild_line = f"\n🏛 Гильдия: <b>{guild['name']}</b> [{guild['tag']}]"

    # Питомец
    pet_line = ""
    if u.get("pet_type"):
        pet_line = f"\n🐾 Питомец: {u.get('pet_name', '?')} (ур. {u.get('pet_level', 1)})"

    materials = (
        f"🔩 {u.get('mat_iron', 0)} · 🧵 {u.get('mat_leather', 0)} · "
        f"✨ {u.get('mat_dust', 0)} · 💎 {u.get('mat_crystal', 0)}"
    )

    # Реферальная ссылка
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"

    await m.answer(
        f"⭐ <b>{u['char_name']}</b>\n\n"
        f"Раса: {RACES.get(u['race'], '?')}\n"
        f"Класс: {CLASSES.get(u['class'], '?')}\n"
        f"Фракция: {faction_name}{guild_line}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']}\n"
        f"💰 Золото: {u['gold']}\n"
        f"🏅 Репутация: {u.get('reputation', 0)}{pet_line}\n\n"
        f"<b>Статы:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Материалы:</b> {materials}\n\n"
        f"📍 {u.get('location', '?')}\n"
        f"⚔️ Боссов: {u.get('bosses_defeated', 0)} · 💀 Смертей: {u.get('deaths', 0)}\n"
        f"🗡 PvP: {u.get('pvp_wins', 0)}/{u.get('pvp_losses', 0)}\n\n"
        f"🔗 <b>Реферальная ссылка:</b>\n<code>{ref_link}</code>\n"
        f"👥 Приглашено: {u.get('referral_count', 0)}",
        reply_markup=_profile_kb(),
        parse_mode=ParseMode.HTML,
    )


# ================= /top =================
@router.message(Command("top"))
@router.message(F.text == "🏅 Рейтинг")
async def top_cmd(m: Message):
    top = await db.get_top_players(10)
    if not top:
        await m.answer("🏅 Пока нет игроков.", reply_markup=_profile_kb())
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = p["char_name"] or "Аноним"
        race = RACES.get(p["race"], "?")
        cls = CLASSES.get(p["class"], "?")
        lines.append(f"{medal} <b>{name}</b> ({race} {cls}) — Ур.{p['level']}")

    await m.answer(
        "🏅 <b>Топ-10</b>\n\n" + "\n".join(lines),
        reply_markup=_profile_kb(),
        parse_mode=ParseMode.HTML,
    )


# ================= /pvptop =================
@router.message(Command("pvptop"))
async def pvp_top_cmd(m: Message):
    top = await db.get_pvp_top(10)
    if not top:
        await m.answer("🏅 Нет победителей дуэлей.", reply_markup=_profile_kb())
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{medal} <b>{p['char_name']}</b> — "
            f"{p['pvp_wins']}🏆 / {p['pvp_losses']}💀"
        )

    await m.answer(
        "⚔️ <b>Топ дуэлянтов</b>\n\n" + "\n".join(lines),
        reply_markup=_profile_kb(),
        parse_mode=ParseMode.HTML,
    )


# ================= /achievements =================
@router.message(Command("achievements"))
@router.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    earned = await db.get_achievements(m.from_user.id)
    codes = {a["code"] for a in earned}
    lines = [f"{'✅' if c in codes else '🔒'} {t}" for c, t in ACHIEVEMENTS.items()]

    await m.answer(
        f"🏆 <b>Достижения ({len(codes)}/{len(ACHIEVEMENTS)})</b>\n\n" + "\n".join(lines),
        reply_markup=_profile_kb(),
        parse_mode=ParseMode.HTML,
    )
