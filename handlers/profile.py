"""Профиль, рейтинги, достижения."""
import logging
import traceback

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

from core import globals as g

router = Router()


# ================= СПРАВОЧНИКИ =================
RACES = {
    "human": "Человек", "elf": "Эльф", "dark_elf": "Тёмный эльф",
    "orc": "Орк", "dwarf": "Гном", "prit": "Плут",
    "demon": "Демон", "angel": "Ангел",
}

CLASSES = {
    "warrior": "Воин", "knight": "Рыцарь", "mage": "Маг",
    "archer": "Лучник", "assassin": "Убийца", "necro": "Некромант",
    "dancer": "Танцор", "destroyer": "Разрушитель", "tyrant": "Тиранин",
    "overlord": "Владыка", "priest": "Жрец", "bard": "Певчий",
    "guardian": "Страж", "hunter": "Охотник", "defender": "Защитник",
    "keeper": "Хранитель",
}

FACTIONS = {
    "light": "Орден Света",
    "dark":  "Тёмное Братство",
}

ACHIEVEMENTS = {
    "first_step": "🌟 Первый шаг", "explorer_5": "🗺 Исследователь — 5 локаций",
    "explorer_10": "🗺 Странник — 10 локаций", "explorer_all": "🌍 Покоритель мира",
    "collector_5": "🎒 Коллекционер", "level_5": "⭐ Опытный — 5 уровень",
    "level_10": "👑 Ветеран — 10 уровень", "level_20": "🔥 Легенда — 20 уровень",
    "first_boss": "⚔️ Убийца боссов", "boss_5": "🐉 Легенда — 5 боссов",
    "referral_3": "👥 Друг друзей", "daily_7": "🎁 Верный игрок",
    "rich": "💰 Богач", "equipped": "⚔️ Снаряжён",
    "survivor": "💀 Выживший", "first_blood": "🩸 Первая кровь",
    "duelist": "🗡 Дуэлянт", "arena_king": "⚜️ Гроза арены",
    "coward": "🏳️ Трус", "graffiti": "✍️ Летописец",
    "social": "👥 Общительный", "pet_owner": "🐾 Хозяин",
    "pet_10": "🐕 Друг навек", "dungeon_1": "🏰 Пещерный ход",
    "dungeon_5": "🏰 Покоритель подземелий", "crafter": "⚒️ Кузнец",
    "upgrader": "🔨 Улучшатель", "guild_founder": "🏛 Основатель гильдии",
    "guild_member": "🏛 Член гильдии", "conqueror": "⚔️ Захватчик",
    "event_hunter": "🎯 Охотник за событиями", "quest_master": "📜 Мастер квестов",
}


# ================= КЛАВИАТУРА =================
def _kb():
    return ReplyKeyboardMarkup(
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


def _effective_stats(user):
    """Базовые статы из БД (без экипировки — упрощённая версия)."""
    return {
        "str": user.get("stat_str", 5), "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5), "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5), "men": user.get("stat_men", 5),
    }


# ================= ПРОФИЛЬ =================
@router.message(Command("stats"))
@router.message(F.text == "⭐ Профиль")
async def stats_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала /start")
        return
    need = u["level"] * u["level"] * 100
    eff = _effective_stats(u)

    faction_name = FACTIONS.get(u["faction"], "—")

    guild = await g.db.get_user_guild(m.from_user.id)
    guild_line = ""
    if guild:
        guild_line = f"\n🏛 Гильдия: <b>{guild['name']}</b> [{guild['tag']}]"

    pet_line = ""
    if u.get("pet_type"):
        pet_line = f"\n🐾 Питомец: {u.get('pet_name', '?')} (ур. {u.get('pet_level', 1)})"

    materials = (f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · "
                 f"✨ {u['mat_dust']} · 💎 {u['mat_crystal']}")

    await m.answer(
        f"⭐ <b>{u['char_name']}</b>\n\n"
        f"Раса: {RACES.get(u['race'], '?')}\n"
        f"Класс: {CLASSES.get(u['class'], '?')}\n"
        f"Фракция: {faction_name}{guild_line}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']}\n"
        f"💰 Золото: {u['gold']}\n"
        f"🏅 Репутация: {u['reputation']}{pet_line}\n\n"
        f"<b>Статы:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Материалы:</b> {materials}\n\n"
        f"⚔️ Боссов: {u['bosses_defeated']} · 💀 Смертей: {u['deaths']}\n"
        f"🗡 PvP: {u['pvp_wins']}/{u['pvp_losses']}",
        reply_markup=_kb(), parse_mode=ParseMode.HTML,
    )


@router.message(Command("top"))
@router.message(F.text == "🏅 Рейтинг")
async def top_cmd(m: Message):
    top = await g.db.get_top_players(10)
    if not top:
        await m.answer("🏅 Пока нет игроков.", reply_markup=_kb())
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["char_name"] or "Аноним"
        race = RACES.get(p["race"], "?")
        cls = CLASSES.get(p["class"], "?")
        lines.append(f"{medal} <b>{name}</b> ({race} {cls}) — Ур.{p['level']}")
    await m.answer("🏅 <b>Топ-10</b>\n\n" + "\n".join(lines),
                   reply_markup=_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("pvptop"))
async def pvp_top_cmd(m: Message):
    top = await g.db.get_pvp_top(10)
    if not top:
        await m.answer("🏅 Нет победителей дуэлей.", reply_markup=_kb())
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} <b>{p['char_name']}</b> — "
                     f"{p['pvp_wins']}🏆 / {p['pvp_losses']}💀")
    await m.answer("⚔️ <b>Топ дуэлянтов</b>\n\n" + "\n".join(lines),
                   reply_markup=_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("achievements"))
@router.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    earned = await g.db.get_achievements(m.from_user.id)
    codes = {a["code"] for a in earned}
    lines = [f"{'✅' if c in codes else '🔒'} {t}" for c, t in ACHIEVEMENTS.items()]
    await m.answer(
        f"🏆 <b>Достижения ({len(codes)}/{len(ACHIEVEMENTS)})</b>\n\n" + "\n".join(lines),
        reply_markup=_kb(), parse_mode=ParseMode.HTML,
    )


# ================= MIDDLEWARE ОШИБОК ДЛЯ РОУТЕРА =================
class ProfileErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Profile handler error: {e}\n{tb}")
            try:
                if hasattr(event, "message") and event.message:
                    await event.message.answer("⚠️ Произошла ошибка. Уже чиним!")
                elif hasattr(event, "answer"):
                    await event.answer("⚠️ Ошибка. Уже чиним!", show_alert=True)
            except Exception:
                pass


router.message.middleware(ProfileErrorMiddleware())
router.callback_query.middleware(ProfileErrorMiddleware())
