"""Профиль, рейтинги, достижения."""
import logging
import traceback

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS, ACHIEVEMENTS
from core.equipment import SLOTS, SLOT_NAMES, get_set_bonus
from core.formulas import calc_p_def, calc_m_def, get_role, get_dmg_type
from core.keyboards import main_kb

router = Router()

ROLE_NAMES = {"tank": "🛡 Танк", "fighter": "⚔️ Боец", "agile": "🏃 Ловкий",
              "mage": "🔮 Маг", "universal": "⚖️ Универсал"}
DMG_NAMES = {"phys": "Физический", "agile": "Ловкий", "magic": "Магический"}


@router.message(Command("stats"))
@router.message(F.text == "⭐ Профиль")
async def stats_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала /start"); return
    need = u["level"] * u["level"] * 100
    eff = {
        "str": u.get("stat_str", 5), "dex": u.get("stat_dex", 5),
        "con": u.get("stat_con", 5), "int": u.get("stat_int", 5),
        "wit": u.get("stat_wit", 5), "men": u.get("stat_men", 5),
    }
    faction_name = FACTIONS.get(u["faction"], {}).get("name", "—")
    race_name = RACES.get(u["race"], {}).get("name", "?")
    class_name = CLASSES.get(u["class"], {}).get("name", "?")
    role = ROLE_NAMES.get(get_role(u), "—")
    dmg_t = DMG_NAMES.get(get_dmg_type(u), "—")
    pdef = calc_p_def(u)
    mdef = calc_m_def(u)

    guild = await g.db.get_user_guild(m.from_user.id)
    guild_line = f"\n🏛 Гильдия: <b>{guild['name']}</b> [{guild['tag']}]" if guild else ""
    pet_line = ""
    if u.get("pet_type"):
        pet_line = f"\n🐾 Питомец: {u.get('pet_name', '?')} (ур. {u.get('pet_level', 1)})"
    materials = (f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · "
                 f"✨ {u['mat_dust']} · 💎 {u['mat_crystal']}")
    energy_line = "∞" if u.get("is_premium") else f"{u.get('energy', 0)}/{u.get('energy_max', 20)}"

    # Экипировка
    eq_lines = []
    for slot in SLOTS:
        val = u.get(f"equipped_{slot}") or "—"
        eq_lines.append(f"{SLOT_NAMES[slot]}: {val}")

    set_b = get_set_bonus(u)
    set_line = f"\n🎁 <b>Сет:</b> {set_b['desc']}" if set_b else ""

    await m.answer(
        f"⭐ <b>{u['char_name']}</b>\n\n"
        f"Раса: {race_name}\n"
        f"Класс: {class_name} ({role})\n"
        f"Тип урона: {dmg_t}\n"
        f"Фракция: {faction_name}{guild_line}\n"
        f"Уровень: {u['level']} (XP {u['xp']}/{need})\n"
        f"❤️ HP: {u['hp']}/{u['max_hp']} · 💧 MP: {u.get('mp', 0)}/{u.get('max_mp', 0)}\n"
        f"⚡ Энергия: {energy_line}\n"
        f"💰 Золото: {u['gold']}\n"
        f"🏅 Репутация: {u['reputation']}{pet_line}\n"
        f"🎯 Очки умений: {u.get('skill_points', 0)}\n\n"
        f"<b>Статы:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Защита:</b> 🛡 P.Def {pdef} · 🔮 M.Def {mdef}\n\n"
        f"<b>Экипировка:</b>\n" + "\n".join(eq_lines) + set_line + "\n\n"
        f"<b>Материалы:</b> {materials}\n\n"
        f"⚔️ Боссов: {u['bosses_defeated']} · 💀 Смертей: {u['deaths']}\n"
        f"🗡 PvP: {u['pvp_wins']}/{u['pvp_losses']}",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML,
    )


@router.message(Command("top"))
@router.message(F.text == "🏅 Рейтинг")
async def top_cmd(m: Message):
    top = await g.db.get_top_players(10)
    if not top:
        await m.answer("🏅 Пока нет игроков.", reply_markup=main_kb()); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["char_name"] or "Аноним"
        race = RACES.get(p["race"], {}).get("name", "?")
        cls = CLASSES.get(p["class"], {}).get("name", "?")
        lines.append(f"{medal} <b>{name}</b> ({race} {cls}) — Ур.{p['level']}")
    await m.answer("🏅 <b>Топ-10</b>\n\n" + "\n".join(lines),
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("pvptop"))
async def pvp_top_cmd(m: Message):
    top = await g.db.get_pvp_top(10)
    if not top:
        await m.answer("🏅 Нет победителей дуэлей.", reply_markup=main_kb()); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} <b>{p['char_name']}</b> — {p['pvp_wins']}🏆 / {p['pvp_losses']}💀")
    await m.answer("⚔️ <b>Топ дуэлянтов</b>\n\n" + "\n".join(lines),
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("achievements"))
@router.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    earned = await g.db.get_achievements(m.from_user.id)
    codes = {a["code"] for a in earned}
    lines = [f"{'✅' if c in codes else '🔒'} {t}" for c, t in ACHIEVEMENTS.items()]
    await m.answer(
        f"🏆 <b>Достижения ({len(codes)}/{len(ACHIEVEMENTS)})</b>\n\n" + "\n".join(lines),
        reply_markup=main_kb(), parse_mode=ParseMode.HTML,
    )


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
