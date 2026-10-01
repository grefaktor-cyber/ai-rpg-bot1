"""Меню скилов + изучение книг. back+close везде."""
import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.skills import available_skills, get_skill
from core.books import SKILL_BOOKS
from core.keyboards import (
    main_kb, skills_main_kb,
    skills_slot_choice_kb, skills_upgrade_kb,
)
from services.ui import send_menu, close_menu


router = Router()


def _back_close_row(back_cb):
    return [
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]


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


def _load_learned_books(user):
    try:
        return set(json.loads(user.get("learned_books") or "[]"))
    except Exception:
        return set()


def _render_main(user):
    learned_books = _load_learned_books(user)
    available = available_skills(user, learned_books)
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

    book_skills = [s for s in available if s.get("source") == "book"]
    text += f"\n<b>Всего скилов:</b> {len(available)}"
    if book_skills:
        text += f" (из книг: {len(book_skills)})"
    return text


@router.message(Command("skills"))
@router.message(F.text == "✨ Скилы")
async def skills_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text = _render_main(u)
    await send_menu(m, text, skills_main_kb())


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
    await close_menu(c)
    await c.answer()


@router.callback_query(F.data == "skills_noop")
async def skills_noop_cb(c: CallbackQuery):
    await c.answer("Максимальный уровень")


@router.callback_query(F.data == "skills_list")
async def skills_list_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    learned_books = _load_learned_books(u)
    available = available_skills(u, learned_books)
    learned = _load_learned(u)

    text = "📚 <b>Все доступные скилы</b>\n\n"
    for s in available:
        lvl = learned.get(s["code"], 1)
        src = " 📖" if s.get("source") == "book" else ""
        if s["effect"] == "passive":
            text += f"🟢 <b>{s['name']}</b> (пассив){src}\n   {s['desc']}\n\n"
        else:
            text += f"• <b>{s['name']}</b> (ур.{lvl}){src}\n   {s['mp_cost']} MP · {s['desc']}\n\n"

    if len(text) > 3500:
        text = text[:3500] + "\n<i>...список обрезан</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[_back_close_row("skills_menu")])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "skills_learn_menu")
async def skills_learn_menu(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    inv = await g.db.get_inventory(c.from_user.id)
    books_in_inv = []
    for it in inv:
        name = it["item_name"]
        for code, b in SKILL_BOOKS.items():
            if b["name"] == name:
                books_in_inv.append((code, b))
                break

    learned_books = _load_learned_books(u)

    text = "📖 <b>Изучение книг</b>\n\n"
    if not books_in_inv:
        text += "<i>В инвентаре нет книг.</i>\n\n"
        text += "💡 <b>Где найти книги:</b>\n"
        text += "• 3-5% шанс с боссов локаций\n"
        text += "• Мировые боссы — чаще\n"
        text += "• Еженедельные квесты\n"
    else:
        text += "Нажми на книгу, чтобы изучить:\n\n"

    rows = []
    for code, b in books_in_inv:
        already = code in learned_books
        user_class = u.get("class", "")
        if b.get("class") and b["class"] != user_class:
            text += f"❌ {b['name']} — не твой класс ({b['class']})\n"
            continue
        if already:
            text += f"✅ {b['name']} — изучено\n"
            continue
        text += f"• {b['name']}\n"
        rows.append([InlineKeyboardButton(
            text=f"📖 Изучить: {b['name']}",
            callback_data=f"learn_book_{code}"
        )])

    rows.append(_back_close_row("skills_menu"))

    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("learn_book_"))
async def learn_book_cb(c: CallbackQuery):
    code = c.data.replace("learn_book_", "")
    b = SKILL_BOOKS.get(code)
    if not b:
        await c.answer("Книга не найдена"); return

    u = await g.db.get_user(c.from_user.id)
    if b.get("class") and b["class"] != u.get("class"):
        await c.answer("❌ Не твой класс", show_alert=True); return

    inv = await g.db.get_inventory(c.from_user.id)
    has = any(i["item_name"] == b["name"] for i in inv)
    if not has:
        await c.answer("❌ Нет книги в инвентаре", show_alert=True); return

    await g.db.remove_item(c.from_user.id, b["name"])
    ok = await g.db.learn_book(c.from_user.id, code)
    if not ok:
        await c.answer("Уже изучено"); return

    await c.answer("✅ Скилл изучен!")
    await c.message.answer(
        f"📖 <b>Скилл изучен!</b>\n\n"
        f"<b>{b['name']}</b>\n\n"
        f"Открой ✨ Скилы → «📚 Все скилы», чтобы увидеть его в пуле.\n"
        f"Поставь в слот через «🎯 Настроить слоты».",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    await skills_learn_menu(c)


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

    rows = [
        [InlineKeyboardButton(text="Слот 1", callback_data="skills_slot_1")],
        [InlineKeyboardButton(text="Слот 2", callback_data="skills_slot_2")],
        [InlineKeyboardButton(text="Слот 3", callback_data="skills_slot_3")],
        _back_close_row("skills_menu"),
    ]
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("skills_slot_"))
async def skills_slot_pick_cb(c: CallbackQuery):
    slot_num = int(c.data.replace("skills_slot_", ""))
    if slot_num not in (1, 2, 3):
        await c.answer("Ошибка"); return
    u = await g.db.get_user(c.from_user.id)
    learned_books = _load_learned_books(u)
    available = available_skills(u, learned_books)
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
    while len(active) < 3:
        active.append("")
    active[slot_num - 1] = code
    active = [x for x in active if x]
    seen = set()
    unique = []
    for x in active:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    active = unique[:3]

    await g.db.set_active_skills(c.from_user.id, json.dumps(active))
    await c.answer(f"✅ Слот {slot_num}: {s['name']}")
    await skills_slots_cb(c)


@router.callback_query(F.data == "skills_upgrade")
async def skills_upgrade_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    sp = u.get("skill_points", 0)
    if sp <= 0:
        await c.answer("Нет очков умений. Получай уровни!", show_alert=True); return
    learned_books = _load_learned_books(u)
    available = available_skills(u, learned_books)
    learned = _load_learned(u)
    text = (f"⬆️ <b>Прокачка скилов</b>\n\n"
            f"🎯 Очки умений: <b>{sp}</b>\n\n"
            f"<i>Одно очко = +1 уровень скила (макс ур.3).\n"
            f"Каждый уровень: +15% к эффекту.</i>\n\n"
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
    await c.answer(f"✅ {s['name']} → ур.{learned[code]}")
    await skills_upgrade_cb(c)
