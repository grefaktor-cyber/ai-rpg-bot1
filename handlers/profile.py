"""Профиль с вкладками: Статы / Экип / Достижения / Материалы."""
import logging
import traceback

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS, ACHIEVEMENTS
from core.equipment import SLOTS, SLOT_NAMES, get_set_bonus
from core.formulas import calc_p_def, calc_m_def, get_role, get_dmg_type
from core.keyboards import main_kb, profile_tabs_kb

router = Router()

ROLE_NAMES = {"tank": "🛡 Танк", "fighter": "⚔️ Боец", "agile": "🏃 Ловкий",
              "mage": "🔮 Маг", "universal": "⚖️ Универсал"}
DMG_NAMES = {"phys": "Физический", "agile": "Ловкий", "magic": "Магический"}


def _stats_text(u):
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
    energy_line = "∞" if u.get("is_premium") else f"{u.get('energy', 0)}/{u.get('energy_max', 20)}"

    from core.titles import format_active_title
    title_str = format_active_title(u)
    title_line = f" — {title_str}" if title_str else ""

    pet_line = ""
    if u.get("pet_type"):
        pet_line = f"\n🐾 {u.get('pet_name', '?')} (ур. {u.get('pet_level', 1)})"

    return (
        f"📊 <b>Статы {u['char_name']}</b>{title_line}\n\n"
        f"Раса: {race_name}\n"
        f"Класс: {class_name} ({role})\n"
        f"Тип урона: {dmg_t}\n"
        f"Фракция: {faction_name}\n"
        f"Уровень: {u['level']} · XP {u['xp']}/{need}\n"
        f"⚡ Энергия: {energy_line}\n"
        f"💰 Золото: {u['gold']}\n"
        f"🏅 Репутация: {u['reputation']}{pet_line}\n"
        f"🎯 Очки умений: {u.get('skill_points', 0)}\n"
        f"📖 Сезонный XP: {u.get('season_xp', 0)}\n\n"
        f"<b>Характеристики:</b>\n"
        f"STR {eff['str']} · DEX {eff['dex']} · CON {eff['con']}\n"
        f"INT {eff['int']} · WIT {eff['wit']} · MEN {eff['men']}\n\n"
        f"<b>Защита:</b>\n"
        f"🛡 P.Def {pdef} · 🔮 M.Def {mdef}\n"
        f"❤️ HP {u['hp']}/{u['max_hp']} · 💧 MP {u.get('mp', 0)}/{u.get('max_mp', 0)}\n\n"
        f"⚔️ Боссов: {u['bosses_defeated']} · 💀 Смертей: {u['deaths']}\n"
        f"🗡 PvP: {u['pvp_wins']}/{u['pvp_losses']}"
    )


def _equip_text(u):
    text = f"👑 <b>Экипировка {u['char_name']}</b>\n\n"
    for slot in SLOTS:
        val = u.get(f"equipped_{slot}") or "—"
        text += f"{SLOT_NAMES[slot]}: <b>{val}</b>\n"
    set_b = get_set_bonus(u)
    if set_b:
        text += f"\n🎁 <b>Сетовый бонус:</b> {set_b['desc']}\n"
    return text


async def _ach_text(uid):
    earned = await g.db.get_achievements(uid)
    codes = {a["code"] for a in earned}
    lines = [f"{'✅' if c in codes else '🔒'} {t}" for c, t in ACHIEVEMENTS.items()]
    return (f"🏆 <b>Достижения ({len(codes)}/{len(ACHIEVEMENTS)})</b>\n\n"
            + "\n".join(lines))


async def _mats_text(uid, u):
    rare = await g.db.get_rare_materials(uid)
    from core.materials import RARE_MATERIALS
    text = "📦 <b>Материалы</b>\n\n"
    text += "<b>Обычные:</b>\n"
    text += f"🔩 Железо: <b>{u.get('mat_iron', 0)}</b>\n"
    text += f"🧵 Кожа: <b>{u.get('mat_leather', 0)}</b>\n"
    text += f"✨ Пыль: <b>{u.get('mat_dust', 0)}</b>\n"
    text += f"💎 Кристалл: <b>{u.get('mat_crystal', 0)}</b>\n\n"
    text += "<b>Редкие (спойл):</b>\n"
    if rare:
        for code, amt in rare.items():
            mat_name = RARE_MATERIALS.get(code, {}).get("name", code)
            text += f"{mat_name}: <b>{amt}</b>\n"
    else:
        text += "<i>Пока нет</i>\n"
    return text


# ================= ХЕНДЛЕРЫ =================
@router.message(Command("stats"))
@router.message(F.text == "⭐ Профиль")
async def stats_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["race"]:
        await m.answer("Сначала /start"); return
    from services.ui import send_menu
    await send_menu(m, _stats_text(u), profile_tabs_kb("stats"))


@router.callback_query(F.data.startswith("prof_tab_"))
async def prof_tab_cb(c: CallbackQuery):
    tab = c.data.replace("prof_tab_", "")
    uid = c.from_user.id
    u = await g.db.get_user(uid)
    if not u["race"]:
        await c.answer("Нет героя", show_alert=True); return

    if tab == "stats":
        text = _stats_text(u)
    elif tab == "equip":
        text = _equip_text(u)
    elif tab == "ach":
        text = await _ach_text(uid)
    elif tab == "mats":
        text = await _mats_text(uid, u)
    else:
        text = _stats_text(u)
        tab = "stats"

    try:
        await c.message.edit_text(text, reply_markup=profile_tabs_kb(tab),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=profile_tabs_kb(tab),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "prof_close")
async def prof_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


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
    from services.ui import send_menu
    await send_menu(m, "🏅 <b>Топ-10</b>\n\n" + "\n".join(lines), main_kb())


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
    text = await _ach_text(m.from_user.id)
    from services.ui import send_menu
    await send_menu(m, text, main_kb())


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
