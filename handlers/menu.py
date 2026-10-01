"""Inline-меню категорий главного меню + автоочистка."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import (
    menu_game_kb, menu_social_kb, menu_progress_kb,
)
from services.ui import send_menu

router = Router()


# ================= REPLY-КНОПКИ КАТЕГОРИЙ =================
@router.message(F.text == "🎮 Игра")
async def menu_game(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "🎮 <b>Игра</b>\n\nВыбери раздел:",
                    menu_game_kb())


@router.message(F.text == "👥 Социум")
async def menu_social(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "👥 <b>Социум</b>\n\nВыбери раздел:",
                    menu_social_kb())


@router.message(F.text == "📊 Прогресс")
async def menu_progress(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "📊 <b>Прогресс</b>\n\nВыбери раздел:",
                    menu_progress_kb())


# ================= CALLBACK'И КАТЕГОРИЙ =================
@router.callback_query(F.data == "menu_close")
async def menu_close(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


async def _edit_or_answer(c, text, kb):
    try:
        await c.message.edit_text(text, reply_markup=kb,
                                   parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb,
                                parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "menu_game")
async def cb_game(c: CallbackQuery):
    await _edit_or_answer(c, "🎮 <b>Игра</b>\n\nВыбери раздел:", menu_game_kb())
    await c.answer()


@router.callback_query(F.data == "menu_social")
async def cb_social(c: CallbackQuery):
    await _edit_or_answer(c, "👥 <b>Социум</b>\n\nВыбери раздел:", menu_social_kb())
    await c.answer()


@router.callback_query(F.data == "menu_progress")
async def cb_progress(c: CallbackQuery):
    await _edit_or_answer(c, "📊 <b>Прогресс</b>\n\nВыбери раздел:", menu_progress_kb())
    await c.answer()


# ================= ЗАПУСК РАЗДЕЛОВ =================
@router.callback_query(F.data == "menu_inv")
async def cb_inv(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.inventory import inventory_cmd
    await inventory_cmd(c.message)


@router.callback_query(F.data == "menu_shop")
async def cb_shop(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.shop import shop
    await shop(c.message)


@router.callback_query(F.data == "menu_skills")
async def cb_skills(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.skills import skills_cmd
    await skills_cmd(c.message)


@router.callback_query(F.data == "menu_craft")
async def cb_craft(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.craft import craft_cmd
    await craft_cmd(c.message)


@router.callback_query(F.data == "menu_quests")
async def cb_quests(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.quests import quests_cmd
    await quests_cmd(c.message)


@router.callback_query(F.data == "menu_dungeon")
async def cb_dungeon(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.combat import dungeon_cmd
    await dungeon_cmd(c.message)


@router.callback_query(F.data == "menu_who")
async def cb_who(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.travel import who_cmd
    await who_cmd(c.message)


@router.callback_query(F.data == "menu_guild")
async def cb_guild(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.guild import guild_cmd
    await guild_cmd(c.message)


@router.callback_query(F.data == "menu_chat")
async def cb_chat(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.chat import chat_cmd
    await chat_cmd(c.message)


@router.callback_query(F.data == "menu_trade")
async def cb_trade(c: CallbackQuery):
    await c.answer("Использование: /trade Имя", show_alert=True)


@router.callback_query(F.data == "menu_duel_info")
async def cb_duel_info(c: CallbackQuery):
    await c.answer("Использование: /duel Имя", show_alert=True)


@router.callback_query(F.data == "menu_profile")
async def cb_profile(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.profile import stats_cmd
    await stats_cmd(c.message)


@router.callback_query(F.data == "menu_ach")
async def cb_ach(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.profile import achievements_cmd
    await achievements_cmd(c.message)


@router.callback_query(F.data == "menu_top")
async def cb_top(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.profile import top_cmd
    await top_cmd(c.message)


@router.callback_query(F.data == "menu_daily")
async def cb_daily(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.daily_premium import daily
    await daily(c.message)


@router.callback_query(F.data == "menu_journal")
async def cb_journal(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.journal import journal_cmd
    await journal_cmd(c.message)


@router.callback_query(F.data == "menu_premium")
async def cb_premium(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.premium import premium_cmd
    await premium_cmd(c.message)


@router.callback_query(F.data == "menu_pet")
async def cb_pet(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.pets import pet_cmd
    await pet_cmd(c.message)


@router.callback_query(F.data == "menu_titles")
async def cb_titles(c: CallbackQuery):
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.titles import titles_cmd
    await titles_cmd(c.message)
