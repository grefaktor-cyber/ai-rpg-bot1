"""Гильдии. back+close."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from services.broadcast import broadcast_to_location
from services.ui import send_menu, close_menu
import world as W

router = Router()


class GuildStates(StatesGroup):
    waiting_name_tag = State()


def _back_close_row():
    return [
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_social"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]


def _guild_menu_kb(has_guild):
    rows = []
    if has_guild:
        rows.append([InlineKeyboardButton(text="📋 Инфо", callback_data="guild_info"),
                     InlineKeyboardButton(text="👥 Участники", callback_data="guild_members")])
        rows.append([InlineKeyboardButton(text="⚔️ Захватить", callback_data="guild_capture"),
                     InlineKeyboardButton(text="🚪 Выйти", callback_data="guild_leave")])
    else:
        rows.append([InlineKeyboardButton(text="🏛 Создать (1000💰)",
                                           callback_data="guild_create_start")])
        rows.append([InlineKeyboardButton(text="🏆 Топ гильдий",
                                           callback_data="guild_top")])
    rows.append(_back_close_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="guild_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")],
    ])


@router.message(Command("guild"))
@router.message(F.text == "🏛 Гильдия")
async def guild_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    guild = await g.db.get_user_guild(m.from_user.id)
    if guild:
        text = (f"🏛 <b>[{guild['tag']}] {guild['name']}</b>\n\n"
                f"📊 Уровень: {guild['level']}\n"
                f"💰 Казна: {guild['treasury']}")
        await send_menu(m, text, _guild_menu_kb(True))
    else:
        text = ("🏛 <b>Гильдии</b>\n\n"
                "Ты не в гильдии. Создай свою и приглашай друзей!\n\n"
                f"<b>Стоимость создания:</b> {W.GUILD_CREATE_COST}💰")
        await send_menu(m, text, _guild_menu_kb(False))


@router.callback_query(F.data == "guild_menu")
async def guild_menu_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if guild:
        text = (f"🏛 <b>[{guild['tag']}] {guild['name']}</b>\n\n"
                f"📊 Уровень: {guild['level']}\n"
                f"💰 Казна: {guild['treasury']}")
        kb = _guild_menu_kb(True)
    else:
        text = ("🏛 <b>Гильдии</b>\n\n"
                "Ты не в гильдии. Создай свою!\n\n"
                f"<b>Стоимость:</b> {W.GUILD_CREATE_COST}💰")
        kb = _guild_menu_kb(False)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "guild_close")
async def guild_close_cb(c: CallbackQuery):
    await close_menu(c)
    await c.answer()


@router.callback_query(F.data == "guild_top")
async def guild_top_cb(c: CallbackQuery):
    guilds = await g.db.get_guilds_top(10)
    if not guilds:
        await c.answer("Пока нет гильдий", show_alert=True); return
    lines = ["🏆 <b>Топ гильдий</b>\n"]
    for i, guild in enumerate(guilds):
        medals = ["🥇", "🥈", "🥉"]
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} <b>[{guild['tag']}] {guild['name']}</b> — "
                     f"ур.{guild['level']}, {guild['members']} чел.")
    try:
        await c.message.edit_text("\n".join(lines), reply_markup=_back_kb(),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer("\n".join(lines), reply_markup=_back_kb(),
                                parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "guild_create_start")
async def guild_create_start(c: CallbackQuery, state: FSMContext):
    u = await g.db.get_user(c.from_user.id)
    if u["gold"] < W.GUILD_CREATE_COST:
        await c.answer(f"Нужно {W.GUILD_CREATE_COST}💰", show_alert=True); return
    if await g.db.get_user_guild(c.from_user.id):
        await c.answer("Ты уже в гильдии", show_alert=True); return
    await state.set_state(GuildStates.waiting_name_tag)
    await c.answer()
    await c.message.answer(
        f"🏛 Напиши название и тег:\n"
        f"Формат: <code>Название | ТЕГ</code>\n"
        f"Пример: <code>Тёмный Легион | TL</code>\n\n"
        f"Тег до {W.GUILD_TAG_MAX}, название до {W.GUILD_NAME_MAX}.\n"
        f"<i>Отмена: /cancel</i>",
        parse_mode=ParseMode.HTML
    )


@router.message(GuildStates.waiting_name_tag)
async def guild_create_input(m: Message, state: FSMContext):
    if m.text and m.text.strip() == "/cancel":
        await state.clear()
        await m.answer("Отменено."); return
    if "|" not in m.text:
        await m.answer("Нужен формат: Название | ТЕГ"); return
    parts = m.text.split("|", 1)
    name = parts[0].strip()[:W.GUILD_NAME_MAX]
    tag = parts[1].strip()[:W.GUILD_TAG_MAX].upper()
    if len(name) < 3 or len(tag) < 2:
        await m.answer("Слишком коротко. Название 3+, тег 2+."); return
    u = await g.db.get_user(m.from_user.id)
    if u["gold"] < W.GUILD_CREATE_COST:
        await m.answer(f"Нужно {W.GUILD_CREATE_COST}💰")
        await state.clear(); return
    gid = await g.db.create_guild(name, tag, m.from_user.id)
    if not gid:
        await m.answer("Название уже занято."); return
    await g.db.spend_gold(m.from_user.id, W.GUILD_CREATE_COST)
    await g.db.add_achievement(m.from_user.id, "guild_founder")
    await g.db.add_journal_entry(
        m.from_user.id, f"Основал гильдию «[{tag}] {name}»", "guild")
    await state.clear()
    await m.answer(
        f"🏛 <b>Гильдия создана!</b>\n\n<b>[{tag}] {name}</b>\n\n"
        f"Приглашай: /guild_invite Ник",
        parse_mode=ParseMode.HTML)


@router.message(Command("guild_invite"))
async def guild_invite(m: Message):
    u = await g.db.get_user(m.from_user.id)
    guild = await g.db.get_user_guild(m.from_user.id)
    if not guild:
        await m.answer("Ты не в гильдии."); return
    if guild["leader_id"] != m.from_user.id:
        await m.answer("Только лидер может приглашать."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /guild_invite Ник"); return
    target = await g.db.get_user_by_char_name(parts[1].strip())
    if not target:
        await m.answer("Игрок не найден."); return
    if await g.db.get_user_guild(target["user_id"]):
        await m.answer("Он уже в гильдии."); return
    await g.db.add_guild_member(target["user_id"], guild["id"])
    await g.db.add_achievement(target["user_id"], "guild_member")
    await g.db.add_journal_entry(
        target["user_id"],
        f"Вступил в гильдию «[{guild['tag']}] {guild['name']}»", "guild")
    try:
        await g.bot.send_message(target["user_id"],
            f"🏛 Ты принят в гильдию <b>[{guild['tag']}] {guild['name']}</b>!",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await m.answer(f"✅ {target['char_name']} принят в гильдию.")


@router.callback_query(F.data == "guild_info")
async def guild_info_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if not guild:
        await c.answer("Не в гильдии"); return
    members = await g.db.get_guild_members(guild["id"])
    owned = [x for x in await g.db.get_all_captured_locations()
             if x["guild_id"] == guild["id"]]
    text = (f"📋 <b>[{guild['tag']}] {guild['name']}</b>\n\n"
            f"📊 Уровень: {guild['level']}\n"
            f"👥 Участников: {len(members)}\n"
            f"🏴 Захвачено: {len(owned)}")
    try:
        await c.message.edit_text(text, reply_markup=_back_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=_back_kb(), parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "guild_members")
async def guild_members_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if not guild:
        await c.answer("Не в гильдии"); return
    members = await g.db.get_guild_members(guild["id"])
    lines = [f"👥 <b>Участники [{guild['tag']}] {guild['name']}</b>\n"]
    for mm in members:
        rank_icon = "👑" if mm["rank"] == "leader" else "•"
        lines.append(f"{rank_icon} <b>{mm['char_name']}</b> — ур.{mm['level']}")
    try:
        await c.message.edit_text("\n".join(lines), reply_markup=_back_kb(),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer("\n".join(lines), reply_markup=_back_kb(),
                                parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "guild_leave")
async def guild_leave_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if not guild:
        await c.answer("Не в гильдии"); return
    if guild["leader_id"] == c.from_user.id:
        await c.answer("Лидер не может выйти.", show_alert=True); return
    guild_tag = guild.get("tag", "?")
    guild_name = guild.get("name", "?")
    await g.db.remove_guild_member(c.from_user.id)
    await g.db.add_journal_entry(
        c.from_user.id,
        f"Вышел из гильдии «[{guild_tag}] {guild_name}»", "guild")
    await c.answer("Ты вышел из гильдии")
    await guild_menu_cb(c)


@router.callback_query(F.data == "guild_capture")
async def guild_capture_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if not guild:
        await c.answer("Не в гильдии"); return
    u = await g.db.get_user(c.from_user.id)
    code = u.get("location_code", "village")
    loc = W.get_location(code)
    if loc.get("type") == "safe":
        await c.answer("Мирные локации нельзя захватывать", show_alert=True); return
    players = await g.db.get_players_at_location(code, 0)
    my_count = len([p for p in players if p.get("guild_id") == guild["id"]]) + 1
    if my_count < 3:
        await c.answer(f"Нужно 3+ членов гильдии здесь (сейчас {my_count})",
                       show_alert=True)
        return
    owner = await g.db.get_location_owner(code)
    if owner and owner["guild_id"] == guild["id"]:
        await c.answer("Локация уже твоя", show_alert=True); return
    await g.db.capture_location(code, guild["id"])
    await g.db.add_achievement(c.from_user.id, "conqueror")
    await g.db.add_world_event(c.from_user.id, u["username"],
                               f"гильдия [{guild['tag']}] захватила «{loc['name']}»")
    await g.db.add_journal_entry(
        c.from_user.id, f"Гильдия захватила «{loc['name']}»", "capture")
    await g.db.add_location_event(
        code, f"гильдия [{guild['tag']}] захватила локацию", "capture", "")
    await broadcast_to_location(
        code,
        f"🏴 <b>Гильдия [{guild['tag']}] {guild['name']}</b> захватила «{loc['name']}»!",
        0)
    await c.answer("Захвачено!")
    text = (f"🏴 <b>Локация «{loc['name']}» захвачена!</b>\n\n"
            f"Члены гильдии получают +15% золота и +10% XP здесь.")
    try:
        await c.message.edit_text(text, reply_markup=_back_kb(),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=_back_kb(),
                                parse_mode=ParseMode.HTML)
