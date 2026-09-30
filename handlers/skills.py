"""Меню скилов: просмотр, настройка слотов, прокачка."""
import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.skills import (
    available_skills, get_skill, skill_level,
)
from core.keyboards import (
    main_kb, skills_main_kb, skills_back_kb,
    skills_slot_choice_kb, skills_upgrade_kb,
)


router = Router()


def _load_learned(user):
    try:
        return json.loads(user.get("learned_skills") or "{}")
    except Exception:
        return {}


def _load_active(user):
    try:
        return json.loads(user.get("active_skills") or "[]")
    except Exception:
        return []


def _render_main(user):
    available = available_skills(user)
    active = _load_active(user)
    learned = _load_learned(user)
    sp = user.get("skill_points", 0)

    text = f"✨ <b>Скилы</b>\n\n"
    text += f"🎯 Очки умений: <b>{sp}</b>\n\n"

    text += "<b>Активные слоты:</b>\n"
    for i in range(3):
        slot_code = active[i] if i < len(active) else None
        if slot_code:
            s = get_skill(slot_code)
            if s:
                lvl = learned.get(slot_code, 1)
                text += f"{i+1}. <b>{s['name']}</b> (ур.{lvl}) · {s['mp_cost']} MP\n"
            else:
                text += f"{i+1}. <i>(пусто)</i>\n"
        else:
            text += f"{i+1}. <i>(пусто)</i>\n"

    text += f"\n<b>Всего доступно скилов:</b> {len(available)}\n"
    text += f"<i>Уровень {user['level']} · Скилы открываются по мере прокачки</i>"
    return text


@router.message(Command("skills"))
@router.message(F.text == "✨ Скилы")
async def skills_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text = _render_main(u)
    await m.answer(text, reply_markup=skills_main_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "skills_menu")
async def skills_menu_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    text = _render_main(u)
    try:
        await c.message.edit_text(text, reply_markup=skills_main_kb(),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=skills_main_kb(),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "skills_close")
async def skills_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data == "skills_noop")
async def skills_noop_cb(c: CallbackQuery):
    await c.answer("Максимальный уровень")


# ================= СПИСОК ВСЕХ =================
@router.callback_query(F.data == "skills_list")
async def skills_list_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    available = available_skills(u)
    learned = _load_learned(u)

    text = "📚 <b>Все доступные скилы</b>\n\n"
    for s in available:
        lvl = learned.get(s["code"], 1)
        if s["effect"] == "passive":
            text += f"🟢 <b>{s['name']}</b> (пассив)\n"
            text += f"   {s['desc']}\n\n"
        else:
            text += f"• <b>{s['name']}</b> (ур.{lvl})\n"
            text += f"   {s['mp_cost']} MP · {s['desc']}\n\n"

    if len(text) > 3500:
        text = text[:3500] + "\n<i>...список обрезан</i>"

    try:
        await c.message.edit_text(text, reply_markup=skills_back_kb(),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=skills_back_kb(),
                               parse_mode=ParseMode.HTML)
    await c.answer()


# ================= НАСТРОЙКА СЛОТОВ =================
@router.callback_query(F.data == "skills_slots")
async def skills_slots_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    active = _load_active(u)
    text = "🎯 <b>Активные слоты</b>\n\n"
    for i in range(3):
        slot_code = active[i] if i < len(active) else None
        if slot_code:
            s = get_skill(slot_code)
            text += f"{i+1}. {s['name'] if s else '?'}\n"
        else:
            text += f"{i+1}. <i>(пусто)</i>\n"
    text += "\n<i>Выбери слот для изменения:</i>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = [
        [InlineKeyboardButton(text=f"Слот 1", callback_data="skills_slot_1")],
        [InlineKeyboardButton(text=f"Слот 2", callback_data="skills_slot_2")],
        [InlineKeyboardButton(text=f"Слот 3", callback_data="skills_slot_3")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")],
    ]
    try:
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("skills_slot_"))
async def skills_slot_pick_cb(c: CallbackQuery):
    slot_num = int(c.data.replace("skills_slot_", ""))
    if slot_num not in (1, 2, 3):
        await c.answer("Ошибка"); return
    u = await g.db.get_user(c.from_user.id)
    available = available_skills(u)
    # Только не-пассивные
    active_skills = [s for s in available if s["effect"] != "passive"]
    if not active_skills:
        await c.answer("Нет доступных активных скилов", show_alert=True); return

    text = f"🎯 <b>Слот {slot_num}</b>\n\nВыбери скил:"
    try:
        await c.message.edit_text(text,
                                  reply_markup=skills_slot_choice_kb(active_skills, slot_num),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=skills_slot_choice_kb(active_skills, slot_num),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("skills_set_"))
async def skills_set_cb(c: CallbackQuery):
    # Формат: skills_set_<slot>_<code>
    parts = c.data.split("_", 3)
    if len(parts) < 4:
        await c.answer("Ошибка"); return
    try:
        slot_num = int(parts[2])
    except ValueError:
        await c.answer("Ошибка"); return
    code = parts[3]
    s = get_skill(code)
    if not s or s["effect"] == "passive":
        await c.answer("Нельзя в слот"); return

    u = await g.db.get_user(c.from_user.id)
    active = _load_active(u)
    # Расширяем до 3
    while len(active) < 3:
        active.append("")
    active[slot_num - 1] = code
    # Фильтруем пустые
    active = [x for x in active if x]
    # Убираем дубликаты
    seen = set()
    unique = []
    for x in active:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    active = unique[:3]

    await g.db.set_active_skills(c.from_user.id, json.dumps(active))
    await c.answer(f"✅ Слот {slot_num}: {s['name']}")
    # Перерисовать меню слотов
    await skills_slots_cb(c)


# ================= ПРОКАЧКА =================
@router.callback_query(F.data == "skills_upgrade")
async def skills_upgrade_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    sp = u.get("skill_points", 0)
    if sp <= 0:
        await c.answer("Нет очков умений. Получай уровни!", show_alert=True); return
    available = available_skills(u)
    learned = _load_learned(u)
    text = (f"⬆️ <b>Прокачка скилов</b>\n\n"
            f"🎯 Очки умений: <b>{sp}</b>\n\n"
            f"<i>Одно очко = +1 уровень скила (макс ур.3).\n"
            f"Каждый уровень скила: +15% к эффекту.</i>\n\n"
            f"Выбери скил:")
    try:
        await c.message.edit_text(text,
                                  reply_markup=skills_upgrade_kb(available, learned),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=skills_upgrade_kb(available, learned),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("skills_up_"))
async def skills_up_cb(c: CallbackQuery):
    code = c.data.replace("skills_up_", "")
    s = get_skill(code)
    if not s or s["effect"] == "passive":
        await c.answer("Нельзя прокачать"); return

    u = await g.db.get_user(c.from_user.id)
    sp = u.get("skill_points", 0)
    if sp <= 0:
        await c.answer("Нет очков", show_alert=True); return

    learned = _load_learned(u)
    cur = learned.get(code, 1)
    if cur >= 3:
        await c.answer("Уже максимум"); return

    learned[code] = cur + 1
    await g.db.set_learned_skills(c.from_user.id, json.dumps(learned))
    await g.db.spend_skill_point(c.from_user.id)

    new_lvl = learned[code]
    await c.answer(f"✅ {s['name']} → ур.{new_lvl}")

    # Перерисовать
    await skills_upgrade_cb(c)
