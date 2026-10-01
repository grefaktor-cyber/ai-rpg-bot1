"""Чат: общий, гильдии, личные сообщения."""
import time

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from core.keyboards import main_kb

router = Router()


class ChatStates(StatesGroup):
    waiting_pm = State()


# ================= АНТИСПАМ =================
_last_sent = {}  # uid -> timestamp
SPAM_INTERVAL = 3  # секунд


def _check_spam(uid):
    now = time.time()
    last = _last_sent.get(uid, 0)
    if now - last < SPAM_INTERVAL:
        return False
    _last_sent[uid] = now
    return True


# ================= ГЛАВНОЕ МЕНЮ ЧАТА =================
@router.message(Command("chat"))
async def chat_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    guild = await g.db.get_user_guild(m.from_user.id)

    # Последние сообщения общего чата
    msgs = await g.db.get_chat_messages("global", limit=10)
    text = "💬 <b>Чат</b>\n\n"
    text += "<b>🌍 Общий чат</b> (последние 10):\n"
    if msgs:
        for msg in reversed(msgs):
            text += f"• <b>{msg['from_name']}</b>: {msg['text']}\n"
    else:
        text += "<i>Пусто. Будь первым!</i>\n"

    text += (
        "\n<b>Как писать:</b>\n"
        "• <code>/c текст</code> — в общий чат\n"
        f"• <code>/g текст</code> — в гильдию"
        + (f" ({guild['tag']})" if guild else " (нужна гильдия)") + "\n"
        "• <code>/w Ник текст</code> — личное\n\n"
        "<i>Антиспам: 1 сообщение в 3 сек.</i>"
    )

    rows = [
        [InlineKeyboardButton(text="🌍 Общий", callback_data="chat_global"),
         InlineKeyboardButton(text="🏛 Гильдия", callback_data="chat_guild")],
        [InlineKeyboardButton(text="✉️ Личное", callback_data="chat_pm_prompt")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="chat_close")],
    ]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "chat_close")
async def chat_close(c: CallbackQuery):
    from services.ui import close_menu
    await close_menu(c)
    await c.answer()


# ================= ОБЩИЙ ЧАТ =================
@router.message(Command("c"))
async def global_chat_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await m.answer("Использование: <code>/c текст</code>",
                       parse_mode=ParseMode.HTML); return
    if not _check_spam(m.from_user.id):
        await m.answer("⏳ Слишком часто. Подожди 3 секунды."); return
    text = parts[1].strip()[:300]
    await g.db.add_chat_message("global", m.from_user.id, u["char_name"], text)

    # Отправить всем, у кого есть персонаж (опционально можно ограничить)
    # Пока — просто подтверждение себе + тем, кто рядом
    await m.answer(f"✅ Отправлено в общий чат:\n<b>{u['char_name']}</b>: {text}",
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "chat_global")
async def chat_global_cb(c: CallbackQuery):
    msgs = await g.db.get_chat_messages("global", limit=15)
    text = "🌍 <b>Общий чат</b>\n\n"
    if not msgs:
        text += "<i>Пусто.</i>"
    else:
        for msg in reversed(msgs):
            text += f"• <b>{msg['from_name']}</b>: {msg['text']}\n"
    text += "\n\nПиши: <code>/c текст</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data="chat_global"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="chat_menu_back"),
    ]])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


# ================= ГИЛЬДИЯ =================
@router.message(Command("g"))
async def guild_chat_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    guild = await g.db.get_user_guild(m.from_user.id)
    if not guild:
        await m.answer("🏛 Ты не в гильдии. /guild — создать."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await m.answer("Использование: <code>/g текст</code>",
                       parse_mode=ParseMode.HTML); return
    if not _check_spam(m.from_user.id):
        await m.answer("⏳ Слишком часто. Подожди 3 секунды."); return
    text = parts[1].strip()[:300]
    await g.db.add_chat_message("guild", m.from_user.id, u["char_name"], text,
                                 guild_id=guild["id"])

    # Рассылаем всем членам гильдии
    members = await g.db.get_all_guild_members_ids(guild["id"])
    for uid in members:
        if uid == m.from_user.id:
            continue
        try:
            await g.bot.send_message(
                uid,
                f"🏛 <b>[{guild['tag']}]</b> {u['char_name']}: {text}",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass
    await m.answer(f"✅ Отправлено в гильдию:\n<b>{u['char_name']}</b>: {text}",
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "chat_guild")
async def chat_guild_cb(c: CallbackQuery):
    guild = await g.db.get_user_guild(c.from_user.id)
    if not guild:
        await c.answer("Ты не в гильдии", show_alert=True); return
    msgs = await g.db.get_chat_messages("guild", limit=15, guild_id=guild["id"])
    text = f"🏛 <b>Чат гильдии [{guild['tag']}]</b>\n\n"
    if not msgs:
        text += "<i>Пусто.</i>"
    else:
        for msg in reversed(msgs):
            text += f"• <b>{msg['from_name']}</b>: {msg['text']}\n"
    text += "\n\nПиши: <code>/g текст</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data="chat_guild"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="chat_menu_back"),
    ]])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


# ================= ЛИЧНЫЕ СООБЩЕНИЯ =================
@router.message(Command("w"))
async def pm_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    parts = m.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[2].strip():
        await m.answer("Использование: <code>/w Ник текст</code>",
                       parse_mode=ParseMode.HTML); return
    target_name = parts[1]
    text = parts[2].strip()[:300]
    if not _check_spam(m.from_user.id):
        await m.answer("⏳ Слишком часто."); return
    target = await g.db.get_user_by_char_name(target_name)
    if not target:
        await m.answer(f"❌ «{target_name}» не найден."); return
    if target["user_id"] == u["user_id"]:
        await m.answer("❌ Нельзя себе."); return

    await g.db.add_chat_message("pm", u["user_id"], u["char_name"], text,
                                 to_id=target["user_id"])
    try:
        await g.bot.send_message(
            target["user_id"],
            f"✉️ <b>{u['char_name']}</b> → тебе:\n{text}\n\n"
            f"<i>Ответить: /w {u['char_name']} текст</i>",
            parse_mode=ParseMode.HTML)
    except Exception:
        await m.answer("⚠️ Не удалось доставить. Возможно, игрок не начал чат с ботом.")
        return
    await m.answer(f"✉️ Отправлено <b>{target['char_name']}</b>:\n{text}",
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "chat_pm_prompt")
async def chat_pm_prompt(c: CallbackQuery, state: FSMContext):
    await state.set_state(ChatStates.waiting_pm)
    await c.answer()
    await c.message.answer(
        "✉️ Напиши: <code>/w Ник текст</code>\n\n"
        "Например: <code>/w Арагорн привет!</code>",
        parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "chat_menu_back")
async def chat_menu_back(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    guild = await g.db.get_user_guild(c.from_user.id)
    msgs = await g.db.get_chat_messages("global", limit=10)
    text = "💬 <b>Чат</b>\n\n"
    text += "<b>🌍 Общий чат</b> (последние 10):\n"
    if msgs:
        for msg in reversed(msgs):
            text += f"• <b>{msg['from_name']}</b>: {msg['text']}\n"
    else:
        text += "<i>Пусто.</i>\n"
    text += (
        "\n<b>Как писать:</b>\n"
        "• <code>/c текст</code> — в общий\n"
        "• <code>/g текст</code> — в гильдию\n"
        "• <code>/w Ник текст</code> — личное"
    )
    rows = [
        [InlineKeyboardButton(text="🌍 Общий", callback_data="chat_global"),
         InlineKeyboardButton(text="🏛 Гильдия", callback_data="chat_guild")],
        [InlineKeyboardButton(text="✉️ Личное", callback_data="chat_pm_prompt")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="chat_close")],
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
