"""Квесты: сюжетные, ежедневные, еженедельные, очки заданий."""
import json
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.quests import (
    STORY_QUESTS, DAILY_QUEST_POOL, WEEKLY_QUESTS, QUEST_POINT_REWARDS,
)
import world as W

router = Router()


# ================= ПОЛУЧЕНИЕ ДАТ ДЛЯ СБРОСА =================
def get_daily_reset_date():
    """Текущая дата для сброса ежедневных квестов."""
    return str(date.today())

def get_weekly_reset_date():
    """Дата понедельника текущей недели для сброса еженедельных квестов."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return str(monday)


# ================= ГЛАВНОЕ МЕНЮ КВЕСТОВ =================
@router.message(Command("quests"))
@router.message(F.text == "📋 Квесты")
async def quests_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return

    # Проверяем и создаём ежедневные квесты, если их нет
    await _ensure_daily_quests(m.from_user.id)

    # Проверяем и создаём еженедельные квесты
    await _ensure_weekly_quests(m.from_user.id)

    # Получаем активные сюжетные квесты
    active_story = await g.db.get_active_story_quests(m.from_user.id)

    # Получаем ежедневные и еженедельные квесты
    daily_quests = await g.db.get_timed_quests(m.from_user.id, "daily", get_daily_reset_date())
    weekly_quests = await g.db.get_timed_quests(m.from_user.id, "weekly", get_weekly_reset_date())

    # Очки заданий
    qp = await g.db.get_quest_points(m.from_user.id)

    text = "📋 <b>Квесты</b>\n\n"
    text += f"⭐ <b>Очки заданий:</b> {qp['points']} (всего: {qp['total_points']})\n\n"

    # Сюжетные
    if active_story:
        text += "📜 <b>Сюжетные:</b>\n"
        for q in active_story:
            quest = STORY_QUESTS.get(q["quest_code"])
            if quest:
                text += f"• {quest['title']} — {q['progress']}/{quest['count']}\n"
        text += "\n"

    # Ежедневные
    text += "⚔️ <b>Ежедневные:</b>\n"
    for dq in daily_quests:
        status = "✅" if dq["completed"] else "⏳"
        text += f"{status} {dq['quest_code']} — {dq['progress']}/{dq['target']}\n"
    text += "\n"

    # Еженедельные
    text += "🏆 <b>Еженедельные:</b>\n"
    for wq in weekly_quests:
        status = "✅" if wq["completed"] else "⏳"
        text += f"{status} {wq['quest_code']} — {wq['progress']}/{wq['target']}\n"

    rows = [
        [InlineKeyboardButton(text="📜 Сюжетные квесты", callback_data="quest_story")],
        [InlineKeyboardButton(text="⚔️ Ежедневные", callback_data="quest_daily")],
        [InlineKeyboardButton(text="🏆 Еженедельные", callback_data="quest_weekly")],
        [InlineKeyboardButton(text="⭐ Очки заданий", callback_data="quest_points")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="quest_close")],
    ]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


# ================= ЕЖЕДНЕВНЫЕ / ЕЖЕНЕДЕЛЬНЫЕ =================
async def _ensure_daily_quests(uid):
    """Создать ежедневные квесты, если их нет на сегодня."""
    reset_date = get_daily_reset_date()
    existing = await g.db.get_timed_quests(uid, "daily", reset_date)
    if existing:
        return
    # Создаём 3 случайных квеста из пула
    import random
    picked = random.sample(DAILY_QUEST_POOL, min(3, len(DAILY_QUEST_POOL)))
    for q in picked:
        await g.db.create_timed_quest(
            uid, "daily", q["title"], q["target"],
            q["reward_gold"], q["reward_xp"], reset_date
        )

async def _ensure_weekly_quests(uid):
    """Создать еженедельные квесты, если их нет на эту неделю."""
    reset_date = get_weekly_reset_date()
    existing = await g.db.get_timed_quests(uid, "weekly", reset_date)
    if existing:
        return
    for q in WEEKLY_QUESTS:
        await g.db.create_timed_quest(
            uid, "weekly", q["title"], q["target"],
            q["reward_gold"], q["reward_xp"], reset_date
        )


# ================= ПРОГРЕСС КВЕСТОВ =================
async def progress_quest(uid, quest_type, amount=1, target_name=None):
    """Обновить прогресс всех подходящих квестов игрока."""
    # Сюжетные
    active_story = await g.db.get_active_story_quests(uid)
    for q in active_story:
        quest = STORY_QUESTS.get(q["quest_code"])
        if not quest:
            continue
        if quest["type"] == "kill" and target_name and quest["target"].lower() in target_name.lower():
            await g.db.incr_story_quest(uid, q["quest_code"], amount)
        elif quest["type"] == "kill" and not target_name:
            await g.db.incr_story_quest(uid, q["quest_code"], amount)

    # Ежедневные
    daily = await g.db.get_timed_quests(uid, "daily", get_daily_reset_date())
    for dq in daily:
        if dq["completed"]:
            continue
        if quest_type in dq["quest_code"].lower() or dq["quest_code"] == "Охотник за головами":
            await g.db.incr_timed_quest(uid, "daily", dq["quest_code"],
                                        get_daily_reset_date(), amount)

    # Еженедельные
    weekly = await g.db.get_timed_quests(uid, "weekly", get_weekly_reset_date())
    for wq in weekly:
        if wq["completed"]:
            continue
        if quest_type in wq["quest_code"].lower() or wq["quest_code"] == "Легендарный охотник":
            await g.db.incr_timed_quest(uid, "weekly", wq["quest_code"],
                                        get_weekly_reset_date(), amount)


# ================= СЮЖЕТНЫЕ =================
@router.callback_query(F.data == "quest_story")
async def quest_story_cb(c: CallbackQuery):
    uid = c.from_user.id
    active = await g.db.get_active_story_quests(uid)
    text = "📜 <b>Сюжетные квесты</b>\n\n"
    rows = []
    if not active:
        # Показываем, какие можно взять
        u = await g.db.get_user(uid)
        for code, q in STORY_QUESTS.items():
            prog = await g.db.get_story_quest(uid, code)
            if prog and prog["completed"]:
                continue
            if u["level"] >= q["req_level"]:
                text += f"• <b>{q['title']}</b>\n  {q['desc']}\n"
                rows.append([InlineKeyboardButton(
                    text=f"Взять: {q['title']}", callback_data=f"quest_take_{code}"
                )])
        if not rows:
            text += "<i>Нет доступных сюжетных квестов.</i>"
    else:
        for q in active:
            quest = STORY_QUESTS.get(q["quest_code"])
            if quest:
                text += (f"• <b>{quest['title']}</b>\n"
                         f"  {quest['desc']}\n"
                         f"  Прогресс: {q['progress']}/{quest['count']}\n\n")
        text += "<i>Продолжай выполнять!</i>"
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="quests_back")])
    try:
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("quest_take_"))
async def quest_take_cb(c: CallbackQuery):
    code = c.data.replace("quest_take_", "")
    quest = STORY_QUESTS.get(code)
    if not quest:
        await c.answer("Квест не найден"); return
    u = await g.db.get_user(c.from_user.id)
    if u["level"] < quest["req_level"]:
        await c.answer(f"Нужен {quest['req_level']} уровень", show_alert=True); return
    ok = await g.db.accept_story_quest(c.from_user.id, code)
    if not ok:
        await c.answer("Уже взят"); return
    await c.answer(f"✅ Взят: {quest['title']}")
    # Уведомляем
    await c.message.answer(
        f"📜 <b>Квест взят:</b> {quest['title']}\n\n"
        f"{quest['desc']}\n"
        f"🎯 Цель: убить {quest['count']}× {quest['target']} в локации «{W.get_location(quest['location'])['name']}»",
        parse_mode=ParseMode.HTML)


# ================= ЕЖЕДНЕВНЫЕ =================
@router.callback_query(F.data == "quest_daily")
async def quest_daily_cb(c: CallbackQuery):
    daily = await g.db.get_timed_quests(c.from_user.id, "daily", get_daily_reset_date())
    text = "⚔️ <b>Ежедневные квесты</b>\n\n"
    rows = []
    for dq in daily:
        status = "✅" if dq["completed"] else "⏳"
        # Находим описание в пуле
        desc = ""
        for pool_q in DAILY_QUEST_POOL:
            if pool_q["title"] == dq["quest_code"]:
                desc = pool_q["desc"]
                break
        text += (f"{status} <b>{dq['quest_code']}</b>\n"
                 f"  {desc}\n"
                 f"  Прогресс: {dq['progress']}/{dq['target']}\n"
                 f"  💰{dq['reward_gold']} · ⭐{dq['reward_xp']} XP\n\n")
        if not dq["completed"]:
            rows.append([InlineKeyboardButton(
                text=f"Сдать: {dq['quest_code']}", callback_data=f"quest_turn_{dq['id']}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="quests_back")])
    try:
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("quest_turn_"))
async def quest_turn_cb(c: CallbackQuery):
    try:
        qid = int(c.data.replace("quest_turn_", ""))
    except ValueError:
        await c.answer("Ошибка"); return

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM timed_quest_progress WHERE id=$1", qid
        )
    if not row or row["completed"]:
        await c.answer("Уже сдано"); return
    if row["progress"] < row["target"]:
        await c.answer(f"Не готово: {row['progress']}/{row['target']}", show_alert=True); return

    await conn.execute("UPDATE timed_quest_progress SET completed=1 WHERE id=$1", qid)
    await g.db.add_gold(c.from_user.id, row["reward_gold"])
    await g.db.add_xp(c.from_user.id, row["reward_xp"])
    await g.db.add_quest_points(c.from_user.id, 5) # +5 очков за ежедневку

    await c.answer(f"✅ +{row['reward_gold']}💰 · +{row['reward_xp']} XP · +5⭐")
    await quest_daily_cb(c)


# ================= ЕЖЕНЕДЕЛЬНЫЕ =================
@router.callback_query(F.data == "quest_weekly")
async def quest_weekly_cb(c: CallbackQuery):
    weekly = await g.db.get_timed_quests(c.from_user.id, "weekly", get_weekly_reset_date())
    text = "🏆 <b>Еженедельные квесты</b>\n\n"
    rows = []
    for wq in weekly:
        status = "✅" if wq["completed"] else "⏳"
        desc = ""
        for pool_q in WEEKLY_QUESTS:
            if pool_q["title"] == wq["quest_code"]:
                desc = pool_q["desc"]
                break
        text += (f"{status} <b>{wq['quest_code']}</b>\n"
                 f"  {desc}\n"
                 f"  Прогресс: {wq['progress']}/{wq['target']}\n"
                 f"  💰{wq['reward_gold']} · ⭐{wq['reward_xp']} XP\n\n")
        if not wq["completed"]:
            rows.append([InlineKeyboardButton(
                text=f"Сдать: {wq['quest_code']}", callback_data=f"quest_turnw_{wq['id']}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="quests_back")])
    try:
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("quest_turnw_"))
async def quest_turnw_cb(c: CallbackQuery):
    try:
        qid = int(c.data.replace("quest_turnw_", ""))
    except ValueError:
        await c.answer("Ошибка"); return

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM timed_quest_progress WHERE id=$1", qid
        )
    if not row or row["completed"]:
        await c.answer("Уже сдано"); return
    if row["progress"] < row["target"]:
        await c.answer(f"Не готово: {row['progress']}/{row['target']}", show_alert=True); return

    await conn.execute("UPDATE timed_quest_progress SET completed=1 WHERE id=$1", qid)
    await g.db.add_gold(c.from_user.id, row["reward_gold"])
    await g.db.add_xp(c.from_user.id, row["reward_xp"])
    await g.db.add_quest_points(c.from_user.id, 15) # +15 очков за еженедельку

    await c.answer(f"✅ +{row['reward_gold']}💰 · +{row['reward_xp']} XP · +15⭐")
    await quest_weekly_cb(c)


# ================= ОЧКИ ЗАДАНИЙ =================
@router.callback_query(F.data == "quest_points")
async def quest_points_cb(c: CallbackQuery):
    qp = await g.db.get_quest_points(c.from_user.id)
    text = (f"⭐ <b>Очки заданий</b>\n\n"
            f"Твои очки: <b>{qp['points']}</b>\n"
            f"Всего заработано: {qp['total_points']}\n\n"
            f"<b>Награды за очки:</b>\n")
    rows = []
    for cost, reward in QUEST_POINT_REWARDS.items():
        can = qp["points"] >= cost
        mark = "✅" if can else "🔒"
        text += f"{mark} {cost} очков — {reward['desc']}\n"
        if can:
            rows.append([InlineKeyboardButton(
                text=f"Купить: {reward['desc']} ({cost}⭐)",
                callback_data=f"quest_buy_{cost}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="quests_back")])
    try:
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("quest_buy_"))
async def quest_buy_cb(c: CallbackQuery):
    try:
        cost = int(c.data.replace("quest_buy_", ""))
    except ValueError:
        await c.answer("Ошибка"); return
    reward = QUEST_POINT_REWARDS.get(cost)
    if not reward:
        await c.answer("Награда не найдена"); return
    ok = await g.db.spend_quest_points(c.from_user.id, cost)
    if not ok:
        await c.answer("Не хватает очков", show_alert=True); return
    await g.db.add_item(c.from_user.id, reward["item"])
    await c.answer(f"✅ Получено: {reward['desc']}")
    await c.message.answer(
        f"🎁 <b>Награда получена!</b>\n{reward['desc']}",
        parse_mode=ParseMode.HTML)


# ================= ОБЩИЕ CALLBACK =================
@router.callback_query(F.data == "quests_back")
async def quests_back_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    # Просто перерисовываем главное меню квестов
    await quests_cmd(c.message)


@router.callback_query(F.data == "quest_close")
async def quest_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
