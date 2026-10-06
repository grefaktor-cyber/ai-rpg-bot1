"""Хендлеры мировых боссов с очередью действий (как в PvP).

ВАЖНО: c.answer() вызывается ПЕРВЫМ делом в каждом callback —
иначе Telegram инвалидирует callback через 30 сек и падает
с 'query is too old'.
"""
import json
import logging
from html import escape

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
log = logging.getLogger(__name__)

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


def _safe(v):
    if v is None:
        return "?"
    return escape(str(v), quote=False)


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
            name = _safe(s["name"]) if s else _safe(code)
            lines.append(f"{slots[i]} ✨ {name}")
        else:
            icon = ACTION_ICONS.get(a, "•")
            name = ACTION_NAMES.get(a, _safe(a))
            lines.append(f"{slots[i]} {icon} {name}")
    return "📋 <b>Очередь:</b>\n" + "\n".join(lines)


def _boss_text(boss, damage_list, u, pending):
    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    bar = _hp_bar(boss["current_hp"], boss["max_hp"])

    dmg_type = boss_data.get("dmg_type", "phys")
    dmg_type_icon = "🔮 Магия" if dmg_type == "magic" else "⚔️ Физика"

    is_raid = boss_data.get("raid", False)
    raid_tag = " ⚔️ РЕЙД" if is_raid else ""

    boss_name = _safe(boss_data.get("name", "?"))
    boss_level = _safe(boss_data.get("level", "?"))
    boss_desc = _safe(boss_data.get("desc", ""))
    boss_atk = _safe(boss_data.get("attack_dmg", 100))

    text = (f"🐉 <b>{boss_name}</b> "
            f"(Ур. {boss_level}){raid_tag}\n"
            f"<i>{boss_desc}</i>\n\n"
            f"{bar}\n"
            f"HP: <b>{boss['current_hp']}/{boss['max_hp']}</b>\n"
            f"⚔️ Урон: ~{boss_atk} ({dmg_type_icon})\n"
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
            uname = _safe(d.get("username") or "?")
            text += f"{medal} {uname} — {d['damage']}\n"
    else:
        text += "<i>Ещё никто не бил.</i>\n"

    text += "\n" + _format_pending(pending)
    return text


def _boss_kb(u, pending):
    """Клавиатура с очередью. Скиллы и зелья показываются ВСЕГДА."""
    try:
        active = json.loads(u.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    mp = u.get("mp", 0)
    max_mp = u.get("max_mp", 0)

    rows = []

    rows.append([
        InlineKeyboardButton(text="⚔️ Атака", callback_data="wb_add_attack"),
        InlineKeyboardButton(text="🛡 Защита", callback_data="wb_add_defend"),
    ])

    if active:
        skill_row = []
        for code in active:
            s = get_skill(code)
            if not s:
                continue
            label = f"✨ {s['name']}"
            if len(label) > 18:
                label = label[:17] + "…"
            if mp < s["mp_cost"]:
                label = f"⚠️ {label}"
            skill_row.append(InlineKeyboardButton(
                text=label, callback_data=f"wb_add_skill_{code}"
            ))
        if skill_row:
            rows.append(skill_row)

    rows.append([
        InlineKeyboardButton(
            text=f"💚 HP ({POTION_PRICE}💰)", callback_data="wb_add_potion_hp"),
        InlineKeyboardButton(
            text=f"🔮 MP ({MP_POTION_PRICE}💰)", callback_data="wb_add_potion_mp"),
    ])

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

    rows.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="wb_refresh"),
    ])
    rows.append(_back_close_row())

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_pending(uid, boss_id):
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
    try:
        u = await g.db.get_user(m.from_user.id)
        if not u["char_name"]:
            await m.answer("Сначала создай героя — /newchar")
            return

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
                    text += f"• {_safe(bd.get('name', '?'))} в «{_safe(loc_n)}»\n"
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
    except Exception as e:
        log.error(f"[BOSS] cmd error: {e}", exc_info=True)
        try:
            await m.answer(f"⚠️ Ошибка: {type(e).__name__}")
        except Exception:
            pass


# ================= ОБНОВЛЕНИЕ =================
async def _refresh_boss_view(c, uid):
    """Только правит сообщение. НЕ отвечает на callback."""
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
    except Exception as e:
        log.debug(f"[BOSS] refresh edit skipped: {e}")


@router.callback_query(F.data == "wb_refresh")
async def wb_refresh_cb(c: CallbackQuery):
    # ✅ answer ПЕРВЫМ — до долгих операций
    try:
        await c.answer("🔄")
    except Exception:
        pass
    await _refresh_boss_view(c, c.from_user.id)


@router.callback_query(F.data == "boss_refresh")
async def boss_refresh_cb(c: CallbackQuery):
    # Редирект — но без двойного answer
    try:
        await c.answer("🔄")
    except Exception:
        pass
    await _refresh_boss_view(c, c.from_user.id)


# ================= ЗАКРЫТИЕ =================
@router.callback_query(F.data == "wb_close")
async def wb_close_cb(c: CallbackQuery):
    try:
        await c.answer()
    except Exception:
        pass
    await close_menu(c)


@router.callback_query(F.data == "boss_close")
async def boss_close_cb(c: CallbackQuery):
    try:
        await c.answer()
    except Exception:
        pass
    await close_menu(c)


# ================= ДОБАВЛЕНИЕ В ОЧЕРЕДЬ =================
async def _add_action(c, action, ack_text="✅"):
    """Общий хелпер. c.answer — ПЕРВЫМ делом."""
    # ✅ Первое — ответ на callback
    try:
        await c.answer(ack_text)
    except Exception:
        pass

    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return

    pending = await _get_pending(uid, boss["id"])
    if len(pending) >= MAX_ACTIONS:
        return

    pending.append(action)
    await _save_pending(uid, boss["id"], pending)
    await _refresh_boss_view(c, uid)


@router.callback_query(F.data == "wb_add_attack")
async def wb_add_attack(c: CallbackQuery):
    await _add_action(c, "attack", "⚔️ +Атака")


@router.callback_query(F.data == "wb_add_defend")
async def wb_add_defend(c: CallbackQuery):
    await _add_action(c, "defend", "🛡 +Защита")


@router.callback_query(F.data.startswith("wb_add_skill_"))
async def wb_add_skill(c: CallbackQuery):
    """БЕЗ проверки MP — скилл сработает, если хватит MP в момент хода."""
    code = c.data.replace("wb_add_skill_", "")
    s = get_skill(code)
    if not s:
        try:
            await c.answer("Скилл не найден", show_alert=True)
        except Exception:
            pass
        return
    await _add_action(c, f"skill_{code}", f"✨ +{s['name']}")


@router.callback_query(F.data == "wb_add_potion_hp")
async def wb_add_potion_hp(c: CallbackQuery):
    await _add_action(c, "potion_hp", f"💚 +HP ({POTION_PRICE}💰)")


@router.callback_query(F.data == "wb_add_potion_mp")
async def wb_add_potion_mp(c: CallbackQuery):
    await _add_action(c, "potion_mp", f"🔮 +MP ({MP_POTION_PRICE}💰)")


# ================= ОТМЕНА =================
@router.callback_query(F.data == "wb_undo")
async def wb_undo_cb(c: CallbackQuery):
    try:
        await c.answer("↩️")
    except Exception:
        pass

    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return

    pending = await _get_pending(uid, boss["id"])
    if not pending:
        return
    pending.pop()
    await _save_pending(uid, boss["id"], pending)
    await _refresh_boss_view(c, uid)


# ================= ВЫПОЛНИТЬ РАУНД =================
@router.callback_query(F.data == "wb_execute")
async def wb_execute_cb(c: CallbackQuery):
    # ✅ ОТВЕТ ПЕРВЫМ — иначе при долгом execute_boss_actions будет timeout
    try:
        await c.answer("⚡ Выполняю...")
    except Exception:
        pass

    uid = c.from_user.id
    u = await g.db.get_user(uid)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return

    pending = await _get_pending(uid, boss["id"])
    if not pending:
        return

    ok, info = await execute_boss_actions(uid, pending)
    await g.db.clear_boss_pending(uid)

    if not ok:
        err = info.get("error")
        # Второй c.answer уже не сработает — используем send_message
        text = None
        if err == "cooldown":
            text = f"⏳ Кулдаун: {info['seconds']}с"
        elif err == "low_hp":
            text = (f"⚠️ HP {info['hp']}/{info['max_hp']} "
                    f"(нужно {info['pct']}%). Подлечись!")
        elif err == "no_boss":
            text = "❌ Босс больше не активен"
        elif err == "not_enough_players":
            text = (f"❌ Нужно {info['min_players']}+ игроков "
                    f"(сейчас {info['current']})")
        else:
            text = "Ошибка"
        try:
            await c.message.answer(text)
        except Exception:
            pass
        return

    log_text = "\n".join(f"  {_safe(x)}" for x in info.get("log", []))
    header = (f"⚔️ <b>Раунд!</b>\n"
              f"💥 Ты нанёс: <b>{info['my_damage']}</b>\n"
              f"💔 Получил: <b>{info['boss_atk']}</b>")
    if info.get("boss_heal", 0) > 0:
        header += f"\n💚 Босс восстановил: +{info['boss_heal']}"

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
        except Exception as e:
            log.debug(f"[BOSS] execute edit skipped: {e}")
