"""Профиль с вкладками. back+close везде. Визуализация + аватар."""
import logging
import traceback

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton,
                           FSInputFile)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS, ACHIEVEMENTS
from core.equipment import SLOTS, SLOT_NAMES, get_set_bonus
from core.formulas import (
    calc_p_def, calc_m_def, get_role, get_dmg_type,
    effective_stats,
)
from core.keyboards import main_kb, profile_tabs_kb
from core.ui_graphics import (
    hp_bar, mp_bar, xp_bar, energy_bar,
    race_icon, class_icon, faction_icon,
    hp_status,
)
from services.ui import send_menu, close_menu, typing, send_menu_from_chat

router = Router()

ROLE_NAMES = {"tank": "🛡 Танк", "fighter": "⚔️ Боец", "agile": "🏃 Ловкий",
              "mage": "🔮 Маг", "universal": "⚖️ Универсал"}
DMG_NAMES = {"phys": "Физический", "agile": "Ловкий", "magic": "Магический"}


def _back_close_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_progress"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]])


async def _send_class_avatar(chat_id, class_code, caption):
    """Отправляет фото класса как аватар в профиле. True если ушло."""
    from core.race_class_art import get_class_image_path
    path = get_class_image_path(class_code)
    if not path:
        return False
    try:
        await g.bot.send_photo(
            chat_id,
            photo=FSInputFile(path),
            caption=caption[:1000],
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logging.warning(f"[PROFILE PHOTO] {class_code}: {e}")
        return False


def _stats_text(u):
    need = u["level"] * u["level"] * 100
    eff = effective_stats(u)
    faction_name = FACTIONS.get(u["faction"], {}).get("name", "—")
    race_name = RACES.get(u["race"], {}).get("name", "?")
    class_name = CLASSES.get(u["class"], {}).get("name", "?")
    role = ROLE_NAMES.get(get_role(u), "—")
    dmg_t = DMG_NAMES.get(get_dmg_type(u), "—")
    pdef = calc_p_def(u)
    mdef = calc_m_def(u)

    from core.titles import format_active_title
    title_str = format_active_title(u)
    title_line = f" — {title_str}" if title_str else ""

    c_ico = class_icon(u.get("class", ""))
    r_ico = race_icon(u.get("race", ""))
    f_ico = faction_icon(u.get("faction", ""))

    hp_ico, hp_txt, _ = hp_status(u["hp"], u["max_hp"])

    pet_line = ""
    if u.get("pet_type"):
        pet_line = f"\n🐾 {u.get('pet_name', '?')} (ур. {u.get('pet_level', 1)})"

    text = "━━━━━━━━━━━━━━━━━━━\n"
    text += f"{c_ico} <b>{u['char_name']}</b>{title_line}\n"
    text += f"{r_ico} {race_name} · {class_name} ({role})\n"
    text += f"{f_ico} {faction_name}\n"
    text += f"🎯 Тип урона: {dmg_t}{pet_line}\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"

    text += xp_bar(u['xp'], need, length=15) + "\n"
    text += hp_bar(u["hp"], u["max_hp"], length=15) + "\n"
    if u.get("max_mp", 0):
        text += mp_bar(u["mp"], u["max_mp"], length=15) + "\n"
    if u.get("is_premium"):
        text += "⚡ <b>∞ Безлимит</b>\n"
    else:
        text += energy_bar(u.get("energy", 0), u.get("energy_max", 20), length=15) + "\n"

    text += f"\n💰 Золото: <b>{u['gold']}</b>\n"
    text += f"🏅 Репутация: <b>{u['reputation']}</b>\n"
    text += f"🎯 Очки умений: <b>{u.get('skill_points', 0)}</b>\n"
    text += f"📖 Сезонный XP: <b>{u.get('season_xp', 0)}</b>\n\n"

    text += f"<b>📊 Характеристики:</b>\n"
    text += f"💪 STR <b>{eff['str']}</b> · 🏹 DEX <b>{eff['dex']}</b> · ❤️ CON <b>{eff['con']}</b>\n"
    text += f"🔮 INT <b>{eff['int']}</b> · ✨ WIT <b>{eff['wit']}</b> · 🛡 MEN <b>{eff['men']}</b>\n\n"

    text += f"<b>🛡 Защита:</b>\n"
    text += f"⚔️ P.Def <b>{pdef}</b> · 🔮 M.Def <b>{mdef}</b>\n\n"

    text += f"<b>📊 Статистика:</b>\n"
    text += f"🐉 Боссов: <b>{u['bosses_defeated']}</b> · 💀 Смертей: <b>{u['deaths']}</b>\n"
    text += f"🗡 PvP: <b>{u['pvp_wins']}</b>🏆 / <b>{u['pvp_losses']}</b>💀"

    return text


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

    # 🎬 «Печатает…»
    await typing(m.chat.id)

    # 🖼 Аватар — фото класса
    class_name = CLASSES.get(u["class"], {}).get("name", "?")
    c_ico = class_icon(u.get("class", ""))
    if class_name and class_name != "?":
        avatar_caption = f"{c_ico} <b>{u['char_name']}</b> — {class_name}"
        await _send_class_avatar(m.chat.id, u["class"], avatar_caption)

    # Меню профиля
    text = _stats_text(u)
    await send_menu(m, text, profile_tabs_kb("stats"))


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
    await close_menu(c)
    await c.answer()


@router.message(Command("top"))
@router.message(F.text == "🏅 Рейтинг")
async def top_cmd(m: Message):
    top = await g.db.get_top_players(10)
    if not top:
        await send_menu(m, "🏅 Пока нет игроков.", _back_close_kb()); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["char_name"] or "Аноним"
        race = RACES.get(p["race"], {}).get("name", "?")
        cls = CLASSES.get(p["class"], {}).get("name", "?")
        r_ico = race_icon(p["race"])
        c_ico = class_icon(p["class"])
        lines.append(f"{medal} <b>{name}</b> {c_ico}{r_ico} — Ур.{p['level']}")
    await send_menu(m, "🏅 <b>Топ-10 игроков</b>\n\n" + "\n".join(lines), _back_close_kb())


@router.message(Command("pvptop"))
async def pvp_top_cmd(m: Message):
    top = await g.db.get_pvp_top(10)
    if not top:
        await send_menu(m, "🏅 Нет победителей дуэлей.", _back_close_kb()); return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} <b>{p['char_name']}</b> — {p['pvp_wins']}🏆 / {p['pvp_losses']}💀")
    await send_menu(m, "⚔️ <b>Топ дуэлянтов</b>\n\n" + "\n".join(lines), _back_close_kb())


@router.message(Command("achievements"))
@router.message(F.text == "🏆 Достижения")
async def achievements_cmd(m: Message):
    text = await _ach_text(m.from_user.id)
    await send_menu(m, text, _back_close_kb())


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
