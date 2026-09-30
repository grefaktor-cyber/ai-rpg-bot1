"""Дневник игрока: просмотр истории приключений."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.journal import format_journal_entry

router = Router()


def _journal_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="journal_refresh")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="journal_close")],
    ])


async def _render_journal(uid):
    u = await g.db.get_user(uid)
    if not u["char_name"]:
        return None
    entries = await g.db.get_journal(uid, limit=25)
    text = f"📜 <b>Дневник {u['char_name']}</b>\n\n"
    if not entries:
        text += "<i>Пока пусто. Приключения только начинаются!</i>"
        return text
    text += f"<b>Последние события:</b>\n\n"
    for e in entries:
        text += format_journal_entry(e) + "\n\n"
    if len(text) > 3800:
        text = text[:3800] + "\n<i>...и ещё</i>"
    return text


@router.message(Command("journal"))
async def journal_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text = await _render_journal(m.from_user.id)
    await m.answer(text, reply_markup=_journal_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "journal_refresh")
async def journal_refresh_cb(c: CallbackQuery):
    text = await _render_journal(c.from_user.id)
    if not text:
        await c.answer("Сначала создай героя", show_alert=True); return
    try:
        await c.message.edit_text(text, reply_markup=_journal_kb(),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer("🔄")


@router.callback_query(F.data == "journal_close")
async def journal_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
