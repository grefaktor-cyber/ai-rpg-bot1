"""Хендлеры мировых боссов с очередью действий (как в PvP)."""
import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.world_bosses import WORLD_BOSSES, ATTACK_COOLDOWN_SEC, MIN_HP_PCT
from core.game_data import (
    POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE,
)
from core.skills import get_skill
from services.world_boss_service import execute_boss_actions
from services.ui import send_menu, close_menu
import world as W

router = Router()

MAX_ACTIONS = 4

ACTION_NAMES = {
    "attack": "Атака",
    "defend": "Защита",
    "potion_hp": "Зелье HP",
    "potion_mp": "Зелье MP",
}

ACTION_ICONS = {
    "attack": "⚔️",
    "defend": "🛡",
    "potion_hp": "💚",
    "potion_mp": "🔮",
}


def _hp_bar(hp, max_hp, length=15):
    if max_hp <= 0:
        return "░" * length
    filled = int((hp / max_hp) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def _back_close_row():
    return [
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]


def _format_pending(pending):
    if not pending:
        return "📋 <i>Очередь пуста. Добавь до 4 действий.</i>"
    slots = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    lines = []
    for i, a in enumerate(pending[:4]):
        if a.startswith("skill_"):
            code = a.replace("skill_", "")
            s = get_skill(code)
            name = s["name"] if s else code
            lines.append(f"{slots[i]} ✨ {name}")
        else:
            icon = ACTION_ICONS.get(a, "•")
            name = ACTION_NAMES.get(a, a)
            lines.append(f"{slots[i]} {icon} {name}")
    return "📋 <b>Очередь:</b>\n" + "\n".join(lines)


def _boss_text(boss, damage_list, u, pending):
    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    bar = _hp_bar(boss["current_hp"], boss["max_hp"])

    dmg_type = boss_data.get("dmg_type", "phys")
    dmg_type_icon = "🔮 Магия" if dmg_type == "magic" else "⚔️ Физика"

    is_raid = boss_data.get("raid", False)
    raid_tag = " ⚔️ РЕЙД" if is_raid else ""

    text = (f"🐉 <b>{boss_data.get('name', '?')}</b> "
            f"(Ур. {boss_data.get('level', '?')}){raid_tag}\n"
            f"<i>{boss_data.get('desc', '')}</i>\n\n"
            f"{bar}\n"
            f"HP: <b>{boss['current_hp']}/{boss['max_hp']}</b>\n"
            f"⚔️ Урон: ~{boss_data.get('attack_dmg', 100)} ({dmg_type_icon})\n"
            f"<i>Твоя {'M.Def' if dmg_type == 'magic' else 'P.Def'} защищает</i>\n\n")

    hp_pct = int((u["hp"] / max(1, u["max_hp"])) * 100)
    mp = u.get("mp", 0)
    max_mp = u.get("max_mp", 0)
    mp_line = f" · 💧 MP: {mp}/{max_mp}" if max_mp else ""
    text += f"❤️ Твой HP: <b>{u['hp']}/{u['max_hp']}</b> ({hp_pct}%){mp_line}\n"
    if hp_pct < int(MIN_HP_PCT * 100):
        text += f"⚠️ <b>HP < {int(MIN_HP_PCT*100)}% — атака заблокирована!</b>\n"
    text += "\n"

    text += f"<b>Топ по урону:</b>\n"
    if damage_list:
        for i, d in enumerate(damage_list):
            medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "•"))
            text += f"{medal} {d['username']} — {d['damage']}\n"
    else:
        text += "<i>Ещё никто не бил.</i>\n"

    text += "\n" + _format_pending(pending)
    return text


def _boss_kb(u, pending):
    """Клавиатура с очередью действий."""
    try:
        active = json.loads(u.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    mp = u.get("mp", 0)
    max_mp = u.get("max_mp", 0)

    rows = []

    # Ряд 1: Атака + Защита
    rows.append([
        InlineKeyboardButton(text="⚔️ Атака", callback_data="wb_add_attack"),
        InlineKeyboardButton(text="🛡 Защита", callback_data="wb_add_defend"),
    ])

    # Ряд 2: скиллы (если есть)
    if active:
        skill_row = []
        for code in active:
            s = get_skill(code)
            if not s:
                continue
            label = f"✨ {s['name']}"
            if len(label) > 18:
                label = label[:17] + "…"
            skill_row.append(InlineKeyboardButton(
                text=label, callback_data=f"wb_add_skill_{code}"
            ))
        if skill_row:
            rows.append(skill_row)

    # Ряд 3: зелья
    potion_row = []
    if u["hp"] < u["max_hp"]:
        potion_row.append(InlineKeyboardButton(
            text=f"💚 HP ({POTION_PRICE}💰)", callback_data="wb_add_potion_hp"
        ))
    if max_mp and mp < max_mp:
        potion_row.append(InlineKeyboardButton(
            text=f"🔮 MP ({MP_POTION_PRICE}💰)", callback_data="wb_add_potion_mp"
        ))
    if potion_row:
        rows.append(potion_row)

    # Ряд 4: Выполнить + Отменить
    action_row = []
    if pending:
        action_row.append(InlineKeyboardButton(
            text="⚡ Выполнить", callback_data="wb_execute"
        ))
        action_row.append(InlineKeyboardButton(
            text="↩️ Отменить", callback_data="wb_undo"
        ))
    if action_row:
        rows.append(action_row)

    # Ряд 5: Обновить
    rows.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="wb_refresh"),
    ])
    rows.append(_back_close_row())

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_pending(uid, boss_id):
    """Читает очередь из БД, чистит если босс сменился."""
    row = await g.db.get_boss_pending(uid)
    if not row:
        return []
    if row.get("boss_id") != boss_id:
        await g.db.clear_boss_pending(uid)
        return []
    try:
        return json.loads(row["actions"] or "[]")
    except Exception:
        return []


async def _save_pending(uid, boss_id, pending):
    await g.db.set_boss_pending(uid, boss_id, json.dumps(pending))


# ================= КОМАНДА /boss =================
@router.message(Command("boss"))
@router.message(F.text == "🐉 Боссы")
async def boss_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)

    if not boss:
        all_bosses = await g.db.get_all_active_world_bosses()
        text = "🐉 <b>Мировые боссы</b>\n\n"
        if all_bosses:
            text += "<b>Активны в мире:</b>\n"
            for b in all_bosses:
                bd = WORLD_BOSSES.get(b["boss_code"], {})
                loc_n = W.get_location(b["location_code"]).get("name", "?")
                text += f"• {bd.get('name', '?')} в «{loc_n}»\n"
                text += f"  HP: {b['current_hp']}/{b['max_hp']}\n\n"
            text += "<i>Иди в локацию босса и напиши /boss снова.</i>"
        else:
            text += ("<i>Сейчас в мире тихо.</i>\n\n"
                     "🕐 <b>Спавн: 14:00, 20:00, 02:00, 08:00 (МСК)</b>")
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_close_row()])
        await send_menu(m, text, kb)
        return

    pending = await _get_pending(m.from_user.id, boss["id"])
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)
    text = _boss_text(boss, damage_list, u, pending)
    await send_menu(m, text, _boss_kb(u, pending))


# ================= ОБНОВЛЕНИЕ =================
async def _refresh_boss_view(c, uid):
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return
    pending = await _get_pending(uid, boss["id"])
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)
    text = _boss_text(boss, damage_list, u, pending)
    try:
        await c.message.edit_text(text, reply_markup=_boss_kb(u, pending),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        pass


@router.callback_query(F.data == "wb_refresh")
async def wb_refresh_cb(c: CallbackQuery):
    await _refresh_boss_view(c, c.from_user.id)
    await c.answer("🔄")


@router.callback_query(F.data == "boss_refresh")
async def boss_refresh_cb(c: CallbackQuery):
    """Старый колбэк — редирект для совместимости."""
    await wb_refresh_cb(c)


# ================= ЗАКРЫТИЕ =================
@router.callback_query(F.data == "wb_close")
async def wb_close_cb(c: CallbackQuery):
    await close_menu(c)
    await c.answer()


@router.callback_query(F.data == "boss_close")
async def boss_close_cb(c: CallbackQuery):
    await wb_close_cb(c)


# ================= ДОБАВЛЕНИЕ В ОЧЕРЕДЬ =================
async def _add_action(c, action):
    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        await c.answer("Босс больше не активен", show_alert=True)
        return

    pending = await _get_pending(uid, boss["id"])
    if len(pending) >= MAX_ACTIONS:
        await c.answer(f"Очередь полна ({MAX_ACTIONS})", show_alert=True)
        return

    pending.append(action)
    await _save_pending(uid, boss["id"], pending)
    await _refresh_boss_view(c, uid)
    await c.answer("✅")


@router.callback_query(F.data == "wb_add_attack")
async def wb_add_attack(c: CallbackQuery):
    await _add_action(c, "attack")


@router.callback_query(F.data == "wb_add_defend")
async def wb_add_defend(c: CallbackQuery):
    await _add_action(c, "defend")


@router.callback_query(F.data.startswith("wb_add_skill_"))
async def wb_add_skill(c: CallbackQuery):
    code = c.data.replace("wb_add_skill_", "")
    s = get_skill(code)
    if not s:
        await c.answer("Скилл не найден", show_alert=True); return
    u = await g.db.get_user(c.from_user.id)
    if u.get("mp", 0) < s["mp_cost"]:
        await c.answer(f"❌ Нужно {s['mp_cost']} MP", show_alert=True); return
    await _add_action(c, f"skill_{code}")


@router.callback_query(F.data == "wb_add_potion_hp")
async def wb_add_potion_hp(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    if u["hp"] >= u["max_hp"]:
        await c.answer("❤️ HP полное", show_alert=True); return
    await _add_action(c, "potion_hp")


@router.callback_query(F.data == "wb_add_potion_mp")
async def wb_add_potion_mp(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    if u.get("mp", 0) >= u.get("max_mp", 0):
        await c.answer("💧 MP полное", show_alert=True); return
    await _add_action(c, "potion_mp")


# ================= ОТМЕНА =================
@router.callback_query(F.data == "wb_undo")
async def wb_undo_cb(c: CallbackQuery):
    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        await c.answer("Босс больше не активен", show_alert=True); return

    pending = await _get_pending(uid, boss["id"])
    if not pending:
        await c.answer("Очередь пуста", show_alert=True); return
    pending.pop()
    await _save_pending(uid, boss["id"], pending)
    await _refresh_boss_view(c, uid)
    await c.answer("↩️")


# ================= ВЫПОЛНИТЬ РАУНД =================
@router.callback_query(F.data == "wb_execute")
async def wb_execute_cb(c: CallbackQuery):
    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        await c.answer("Босс больше не активен", show_alert=True); return

    pending = await _get_pending(uid, boss["id"])
    if not pending:
        await c.answer("Очередь пуста", show_alert=True); return

    ok, info = await execute_boss_actions(uid, pending)
    await g.db.clear_boss_pending(uid)

    if not ok:
        err = info.get("error")
        if err == "cooldown":
            await c.answer(f"⏳ Кулдаун: {info['seconds']}с", show_alert=True)
        elif err == "low_hp":
            await c.answer(
                f"⚠️ HP {info['hp']}/{info['max_hp']} "
                f"(нужно {info['pct']}%). Подлечись!",
                show_alert=True)
        elif err == "no_boss":
            await c.answer("Босс больше не активен", show_alert=True)
        elif err == "not_enough_players":
            await c.answer(
                f"❌ Нужно {info['min_players']}+ игроков "
                f"(сейчас {info['current']})",
                show_alert=True)
        else:
            await c.answer("Ошибка", show_alert=True)
        return

    # === ЛОГ РАУНДА ===
    log_text = "\n".join(f"  {x}" for x in info.get("log", []))
    header = (f"⚔️ <b>Раунд!</b>\n"
              f"💥 Ты нанёс: <b>{info['my_damage']}</b>\n"
              f"💔 Получил: <b>{info['boss_atk']}</b>")
    if info.get("boss_heal", 0) > 0:
        header += f"\n💚 Босс восстановил: +{info['boss_heal']}"

    await c.answer(f"⚔️ {info['my_damage']} / 💔 {info['boss_atk']}",
                   show_alert=False)

    # === СМЕРТЬ ИГРОКА ===
    if info.get("player_died"):
        try:
            await c.message.edit_text(
                f"💀 <b>Ты пал от лап босса!</b>\n\n"
                f"Потеряно <b>{info['lost_gold']}💰</b>\n"
                f"Ты очнулся в Начальной деревне.",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass
        try:
            await c.message.answer("Возвращайся в деревню.",
                                    reply_markup=main_kb())
        except Exception:
            pass
        return

    # === БОСС УБИТ ===
    if info.get("killed"):
        try:
            await c.message.edit_text(
                f"🏆 <b>Босс побеждён!</b>\n\n{log_text}\n\n"
                f"💥 Ты нанёс: <b>{info['my_damage']}</b>\n"
                f"Награды выданы.",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return

    # === ОБНОВЛЯЕМ ВИД ===
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if boss:
        damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)
        text = _boss_text(boss, damage_list, u, [])
        text = f"{header}\n\n{log_text}\n\n———\n\n{text}"
        try:
            await c.message.edit_text(text, reply_markup=_boss_kb(u, []),
                                       parse_mode=ParseMode.HTML)
        except Exception:
            pass
