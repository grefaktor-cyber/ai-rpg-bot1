"""Туториал: интерактивное обучение с выбором."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb

router = Router()


STEPS = [
    {
        "title": "👋 Добро пожаловать!",
        "text": (
            "Ты — герой в мире тёмного фэнтези.\n\n"
            "Мир — <b>12 локаций</b>, соединённых дорогами. "
            "Исследуй, сражайся, становись сильнее.\n\n"
            "Ты управляешь героем через <b>текст</b>: пиши что делает герой, "
            "и ИИ-мастер опишет сцену.\n\n"
            "<i>Пример: «осматриваюсь по сторонам»</i>"
        ),
    },
    {
        "title": "🚶 Путешествия",
        "text": (
            "Кнопка <b>🚶 Идти</b> — переход между локациями.\n\n"
            "📍 Ты стартуешь в <b>Начальной деревне</b>.\n"
            "Отсюда можно пойти:\n"
            "• В таверну «Пьяный гоблин»\n"
            "• На Большой тракт\n"
            "• В Тёмный лес\n\n"
            "<i>Или напиши: «иду в лес».</i>"
        ),
    },
    {
        "title": "📜 NPC и квесты",
        "text": (
            "В локациях живут <b>NPC</b> — Кузнец, Старейшина, Лесник.\n\n"
            "<b>/npc</b> — открыть список NPC в текущей локации.\n"
            "У каждого — квесты с наградами: золото, XP, предметы.\n\n"
            "<b>/quests</b> — ежедневные квесты (3 в день).\n\n"
            "<i>Попробуй: /npc в деревне.</i>"
        ),
    },
    {
        "title": "⚔️ Бой и скилы",
        "text": (
            "Чтобы начать бой — напиши действие:\n"
            "<i>«атакую волка»</i>\n\n"
            "В бою появятся кнопки:\n"
            "• ⚔️ Атака · 🛡 Защита · ✨ Скил\n"
            "• 💚 Зелье · 🏃 Бежать\n\n"
            "<b>/skills</b> — настроить 3 активных скила и прокачать их.\n"
            "MP тратится на скилы, восстанавливается зельями."
        ),
    },
    {
        "title": "🏛 Гильдии и события",
        "text": (
            "<b>/guild</b> — создать гильдию (1000💰).\n"
            "Гильдии могут захватывать локации — это даёт +15% золота и XP.\n\n"
            "<b>/world</b> — что происходит в мире:\n"
            "• 🔴 Нашествия\n"
            "• 💰 Клады\n"
            "• ☠️ Моры\n\n"
            "<i>События меняются каждый час.</i>"
        ),
    },
    {
        "title": "🎉 Готово!",
        "text": (
            "Ты прошёл обучение!\n\n"
            "<b>Что дальше:</b>\n"
            "• Иди в лес — там гоблины, с них падает золото\n"
            "• Возьми квест у Кузнеца (/npc)\n"
            "• Купи зелье HP в магазине (🛒)\n"
            "• Пригласи друга (/ref) — +10 к энергии\n\n"
            "<b>Награда за обучение:</b>\n"
            "💰 100 золота\n"
            "🏆 Достижение «🎓 Ученик»\n\n"
            "Удачи, герой! 🎮"
        ),
        "reward": True,
    },
]


async def offer_tutorial(chat_id, uid, force=False):
    """Предложить пройти обучение."""
    if not force:
        step, finished = await g.db.get_tutorial_step(uid)
        if finished:
            return
    text = (
        "🎓 <b>Обучение</b>\n\n"
        "Хочешь пройти короткое обучение (6 шагов)?\n"
        "Это займёт минуту и даст <b>100 золота + достижение</b>.\n\n"
        "<i>Можно пройти позже — команда /tutorial.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📚 Пройти", callback_data="tut_start"),
        InlineKeyboardButton(text="⏭ Пропустить", callback_data="tut_skip"),
    ]])
    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)


def _step_kb(step_idx):
    rows = []
    if step_idx < len(STEPS) - 1:
        rows.append([InlineKeyboardButton(
            text="➡️ Дальше", callback_data=f"tut_step_{step_idx + 1}")])
    rows.append([InlineKeyboardButton(
        text="⏭ Пропустить остальное", callback_data="tut_finish")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_step(chat_id, step_idx):
    if step_idx < 0 or step_idx >= len(STEPS):
        return
    step = STEPS[step_idx]
    text = f"<b>{step['title']}</b>\n\n{step['text']}"
    if step_idx == len(STEPS) - 1:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎮 В игру", callback_data="tut_finish")
        ]])
    else:
        kb = _step_kb(step_idx)
    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)


# ================= CALLBACK =================
@router.callback_query(F.data == "tut_start")
async def tut_start(c: CallbackQuery):
    await g.db.set_tutorial_step(c.from_user.id, 0)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer("Начинаем!")
    await show_step(c.message.chat.id, 0)


@router.callback_query(F.data == "tut_skip")
async def tut_skip(c: CallbackQuery):
    await g.db.set_tutorial_step(c.from_user.id, 99, finished=True)
    try:
        await c.message.edit_text(
            "👌 Пропущено. Если захочешь — /tutorial в любой момент.",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("tut_step_"))
async def tut_step(c: CallbackQuery):
    try:
        idx = int(c.data.replace("tut_step_", ""))
    except ValueError:
        await c.answer("Ошибка"); return
    await g.db.set_tutorial_step(c.from_user.id, idx)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
    await show_step(c.message.chat.id, idx)


@router.callback_query(F.data == "tut_finish")
async def tut_finish(c: CallbackQuery):
    uid = c.from_user.id
    step, finished = await g.db.get_tutorial_step(uid)
    if not finished:
        await g.db.add_gold(uid, 100)
        await g.db.add_achievement(uid, "tutorial_done")
    await g.db.set_tutorial_step(uid, 99, finished=True)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
    await g.bot.send_message(
        c.message.chat.id,
        "🎉 <b>Обучение завершено!</b>\n\n"
        "💰 +100 золота\n"
        "🏆 Достижение «🎓 Ученик»\n\n"
        "Открой /help или /skills — исследуй!",
        reply_markup=main_kb(),
        parse_mode=ParseMode.HTML
    )


async def run_tutorial(uid, chat_id):
    """Старая функция — вызывается автоматически. Теперь показывает выбор."""
    await offer_tutorial(chat_id, uid)
