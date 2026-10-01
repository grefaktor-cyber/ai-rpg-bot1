"""Меню титулов. back+close."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.titles import TITLES, get_available_titles
from core.keyboards import main_kb
from services.ui import send_menu, close_menu

router = Router()


@router.message(Command("titles"))
@router.message(Command("title"))
@router.message(F.text == "🏆 Титулы")
async def titles_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text, kb = await _build_menu(u)
    await send_menu(m, text, kb)


async def _build_menu(u):
    earned = await g.db.get_achievements(u["user_id"])
    achievements_codes = {a["code"] for a in earned}
    unlocked = set(get_available_titles(u, achievements_codes))
    active = u.get("active_title", "")

    text = "🏆 <b>Титулы</b>\n\n"
    if active and active in TITLES:
        d = TITLES[active]
        text += f"<b>Активный:</b> {d['icon']} {d['name']}\n\n"
    else:
        text += "<b>Активный:</b> <i>не выбран</i>\n\n"

    text += f"Открыто: <b>{len(unlocked)}</b> / {len(TITLES)}\n\n"
    text += "<b>Все титулы:</b>\n"
    for code, data in TITLES.items():
        mark = "✅" if code in unlocked else "🔒"
        active_mark = " ← активный" if code == active else ""
        text += f"{mark} {data['icon']} <b>{data['name']}</b>{active_mark}\n"
        text += f"    <i>{data['desc']}</i>\n"

    rows = []
    for code, data in TITLES.items():
        if code not in unlocked:
            continue
        rows.append([InlineKeyboardButton(
            text=f"{data['icon']} {data['name']}",
            callback_data=f"title_set_{code}"
        )])
    if active:
        rows.append([InlineKeyboardButton(
            text="🚫 Снять титул",
            callback_data="title_clear"
        )])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_progress"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "title_close")
async def title_close(c: CallbackQuery):
    await close_menu(c)
    await c.answer()


@router.callback_query(F.data == "title_clear")
async def title_clear(c: CallbackQuery):
    await g.db.set_active_title(c.from_user.id, "")
    await c.answer("🚫 Титул снят")
    u = await g.db.get_user(c.from_user.id)
    text, kb = await _build_menu(u)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass


@router.callback_query(F.data.startswith("title_set_"))
async def title_set(c: CallbackQuery):
    code = c.data.replace("title_set_", "")
    if code not in TITLES:
        await c.answer("Не найдено"); return
    u = await g.db.get_user(c.from_user.id)
    earned = await g.db.get_achievements(c.from_user.id)
    achievements_codes = {a["code"] for a in earned}
    unlocked = get_available_titles(u, achievements_codes)
    if code not in unlocked:
        await c.answer("🔒 Титул не открыт", show_alert=True); return
    await g.db.set_active_title(c.from_user.id, code)
    await c.answer(f"✅ {TITLES[code]['name']}")
    u = await g.db.get_user(c.from_user.id)
    text, kb = await _build_menu(u)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass
