"""Inline-меню категорий + запуск разделов через fake_message."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import (
    menu_game_kb, menu_social_kb, menu_progress_kb,
)
from services.ui import send_menu, fake_message

router = Router()


# ================= REPLY-КНОПКИ КАТЕГОРИЙ =================
@router.message(F.text == "🎮 Игра")
async def menu_game(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "🎮 <b>Игра</b>\n\nВыбери раздел:", menu_game_kb())


@router.message(F.text == "👥 Социум")
async def menu_social(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "👥 <b>Социум</b>\n\nВыбери раздел:", menu_social_kb())


@router.message(F.text == "📊 Прогресс")
async def menu_progress(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя через /start"); return
    await send_menu(m, "📊 <b>Прогресс</b>\n\nВыбери раздел:", menu_progress_kb())


# ================= CALLBACK'И КАТЕГОРИЙ =================
@router.callback_query(F.data == "menu_close")
async def menu_close(c: CallbackQuery):
    from services.ui import close_menu
    await close_menu(c)
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
async def _run_cmd(c: CallbackQuery, module_name: str, func_name: str):
    """Запустить xxx_cmd(fake_message) с правильным from_user.
    Отслеживаем 'затуп' игрока — если 3 раза подряд ошибка, предложить /help."""
    from services.hints import register_lost_action, clear_lost, check_lost_hint

    msg_obj = c.message
    try:
        await msg_obj.delete()
    except Exception:
        try:
            await msg_obj.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await c.answer()

    # Создаём FakeMessage — from_user = игрок
    msg = fake_message(c)
    try:
        module = __import__(f"handlers.{module_name}", fromlist=[func_name])
        func = getattr(module, func_name)
        await func(msg)
        clear_lost(c.from_user.id)
    except Exception as e:
        import logging
        logging.error(f"_run_cmd {module_name}.{func_name}: {e}")
        try:
            await msg_obj.answer("⚠️ Ошибка открытия раздела.")
        except Exception:
            pass
        # Регистрируем "затуп"
        if register_lost_action(c.from_user.id):
            await check_lost_hint(c.from_user.id, c.message.chat.id)


@router.callback_query(F.data == "menu_inv")
async def cb_inv(c: CallbackQuery):
    await _run_cmd(c, "inventory", "inventory_cmd")


@router.callback_query(F.data == "menu_shop")
async def cb_shop(c: CallbackQuery):
    await _run_cmd(c, "shop", "shop")


@router.callback_query(F.data == "menu_skills")
async def cb_skills(c: CallbackQuery):
    await _run_cmd(c, "skills", "skills_cmd")


@router.callback_query(F.data == "menu_craft")
async def cb_craft(c: CallbackQuery):
    await _run_cmd(c, "craft", "craft_cmd")


@router.callback_query(F.data == "menu_quests")
async def cb_quests(c: CallbackQuery):
    await _run_cmd(c, "quests", "quests_cmd")


@router.callback_query(F.data == "menu_dungeon")
async def cb_dungeon(c: CallbackQuery):
    await _run_cmd(c, "combat", "dungeon_cmd")


@router.callback_query(F.data == "menu_map")
async def cb_map(c: CallbackQuery):
    await _run_cmd(c, "travel", "map_cmd")


@router.callback_query(F.data == "menu_travel")
async def cb_travel(c: CallbackQuery):
    await _run_cmd(c, "travel", "travel_cmd")


@router.callback_query(F.data == "menu_who")
async def cb_who(c: CallbackQuery):
    await _run_cmd(c, "travel", "who_cmd")


@router.callback_query(F.data == "menu_guild")
async def cb_guild(c: CallbackQuery):
    await _run_cmd(c, "guild", "guild_cmd")


@router.callback_query(F.data == "menu_chat")
async def cb_chat(c: CallbackQuery):
    await _run_cmd(c, "chat", "chat_cmd")


@router.callback_query(F.data == "menu_trade")
async def cb_trade(c: CallbackQuery):
    await c.answer("Использование: /trade Имя", show_alert=True)


@router.callback_query(F.data == "menu_duel_info")
async def cb_duel_info(c: CallbackQuery):
    await c.answer("Использование: /duel Имя", show_alert=True)


@router.callback_query(F.data == "menu_profile")
async def cb_profile(c: CallbackQuery):
    await _run_cmd(c, "profile", "stats_cmd")


@router.callback_query(F.data == "menu_ach")
async def cb_ach(c: CallbackQuery):
    await _run_cmd(c, "profile", "achievements_cmd")


@router.callback_query(F.data == "menu_top")
async def cb_top(c: CallbackQuery):
    await _run_cmd(c, "profile", "top_cmd")


@router.callback_query(F.data == "menu_daily")
async def cb_daily(c: CallbackQuery):
    await _run_cmd(c, "daily_premium", "daily")


@router.callback_query(F.data == "menu_journal")
async def cb_journal(c: CallbackQuery):
    await _run_cmd(c, "journal", "journal_cmd")


@router.callback_query(F.data == "menu_premium")
async def cb_premium(c: CallbackQuery):
    await _run_cmd(c, "premium", "premium_cmd")


@router.callback_query(F.data == "menu_pet")
async def cb_pet(c: CallbackQuery):
    await _run_cmd(c, "pets", "pet_cmd")


@router.callback_query(F.data == "menu_titles")
async def cb_titles(c: CallbackQuery):
    await _run_cmd(c, "titles", "titles_cmd")


@router.callback_query(F.data == "menu_season")
async def cb_season(c: CallbackQuery):
    await _run_cmd(c, "seasons", "season_cmd")
