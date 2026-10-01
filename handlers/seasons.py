"""Сезоны: /season — рейтинг и инфо."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES
from services.season_service import get_season_info, ensure_season
from services.ui import send_menu, close_menu

router = Router()


def _season_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="season_refresh")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="season_close")],
    ])


async def _render_season(uid):
    info = await get_season_info()
    top = await g.db.get_season_top(limit=10)
    rank = await g.db.get_user_season_rank(uid)
    user = await g.db.get_user(uid)

    text = f"🏆 <b>Сезон #{info['number']}</b>\n\n"
    text += f"⏳ До конца: <b>{info['days_left']} дней</b>\n\n"

    text += f"<b>Твоя позиция:</b> <b>#{rank}</b>\n"
    text += f"⭐ Сезонный XP: <b>{user.get('season_xp', 0)}</b>\n\n"

    text += "<b>Топ-10:</b>\n"
    if not top:
        text += "<i>Пока пусто. Будь первым!</i>\n"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(top):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = p.get("char_name") or "?"
            race = RACES.get(p.get("race"), {}).get("name", "?")
            cls = CLASSES.get(p.get("class"), {}).get("name", "?")
            marker = " ←ты" if p["user_id"] == uid else ""
            text += f"{medal} <b>{name}</b> ({race} {cls}) — {p['season_xp']}⭐{marker}\n"

    text += "\n<i>Сезонный XP начисляется за победы в бою.</i>"
    return text


@router.message(Command("season"))
async def season_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    await ensure_season()
    text = await _render_season(m.from_user.id)
    await send_menu(m, text, _season_kb())


@router.callback_query(F.data == "season_refresh")
async def season_refresh_cb(c: CallbackQuery):
    text = await _render_season(c.from_user.id)
    try:
        await c.message.edit_text(text, reply_markup=_season_kb(),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer("🔄")


@router.callback_query(F.data == "season_close")
async def season_close_cb(c: CallbackQuery):
    await close_menu(c)
    await c.answer()
