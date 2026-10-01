"""Квесты: сюжетные, ежедневные, еженедельные, очки заданий."""
import json
import random
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


# ================= ДАТЫ СБРОСА =================
def get_daily_reset_date():
    return str(date.today())


def get_weekly_reset_date():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return str(monday)


def _filter_name(code):
    return {"all": "все", "story": "сюжетные",
            "daily": "ежедневные", "weekly": "еженедельные"}.get(code, "все")


# ================= ГЛАВНОЕ МЕНЮ =================
@router.message(Command("quests"))
@router.message(F.text == "📋 Квесты")
async def quests_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    await _ensure_daily_quests(m.from_user.id)
    await _ensure_weekly_quests(m.from_user.id)
    await _show_quests(m.from_user.id, "all", reply_message=m)


async def _show_quests(uid, filter_type="all", chat_id=None,
                       edit_message=None, reply_message=None):
    """Показать / обновить меню квестов с фильтром."""
    u = await g.db.get_user(uid)
    active_story = await g.db.get_active_story_quests(uid)
    daily = await g.db.get_timed_quests(uid, "daily", get_daily_reset_date())
    weekly = await g.db.get_timed_quests(uid, "weekly", get_weekly_reset_date())
    qp = await g.db.get_quest_points(uid)

    text = "📋 <b>Квесты</b>\n\n"
    text += f"⭐ Очки заданий: <b>{qp['points']}</b>\n"
    text += f"🔀 Фильтр: <b>{_filter_name(filter_type)}</b>\n\n"

    complete_buttons = []

    # --- СЮЖЕТНЫЕ ---
    if filter_type in ("all", "story"):
        if active_story:
            text += "📜 <b>Сюжетные (активные):</b>\n"
            for q in active_story:
                quest = STORY_QUESTS.get(q["quest_code"])
                if not quest:
                    continue
                prog = q["progress"]
                count = quest["count"]
                done = "✅" if prog >= count else "⏳"
                text += f"{done} <b>{quest['title']}</b> — {prog}/{count}\n"
                text += f"   <i>{quest['desc'][:60]}...</i>\n"
            text += "\n"
        else:
            text += "📜 <b>Сюжетные (можно взять):</b>\n"
            avail_story = []
            for code, q in STORY_QUESTS.items():
                prog = await g.db.get_story_quest(uid, code)
                if prog and prog["completed"]:
                    continue
                if u["level"] >= q["req_level"]:
                    avail_story.append((code, q))
            if avail_story:
                for code, q in avail_story:
                    text += f"• <b>{q['title']}</b> [Ур. {q['req_level']}+]\n"
                for code, q in avail_story[:4]:
                    complete_buttons.append([InlineKeyboardButton(
                        text=f"📜 Взять: {q['title']}",
                        callback_data=f"quest_take_{code}")])
            else:
                text += "<i>Нет доступных сюжетных квестов.</i>\n"
            text += "\n"

    # --- ЕЖЕДНЕВНЫЕ ---
    if filter_type in ("all", "daily"):
        text += "⚔️ <b>Ежедневные:</b>\n"
        if not daily:
            text += "<i>Загрузка...</i>\n"
        for dq in daily:
            status = "✅" if dq["completed"] else "⏳"
            desc = ""
            for pool_q in DAILY_QUEST_POOL:
                if pool_q["title"] == dq["quest_code"]:
                    desc = pool_q.get("desc", "")
                    break
            text += f"{status} <b>{dq['quest_code']}</b> — {dq['progress']}/{dq['target']}\n"
            if desc:
                text += f"   <i>{desc[:60]}</i>\n"
            if not dq["completed"] and dq["progress"] >= dq["target"]:
                complete_buttons.append([InlineKeyboardButton(
                    text=f"✅ Сдать: {dq['quest_code'][:20]}",
                    callback_data=f"quest_turn_{dq['id']}")])
        text += "\n"

    # --- ЕЖЕНЕДЕЛЬНЫЕ ---
    if filter_type in ("all", "weekly"):
        text += "🏆 <b>Еженедельные:</b>\n"
        if not weekly:
            text += "<i>Загрузка...</i>\n"
        for wq in weekly:
            status = "✅" if wq["completed"] else "⏳"
            desc = ""
            for pool_q in WEEKLY_QUESTS:
                if pool_q["title"] == wq["quest_code"]:
                    desc = pool_q.get("desc", "")
                    break
            text += f"{status} <b>{wq['quest_code']}</b> — {wq['progress']}/{wq['target']}\n"
            if desc:
                text += f"   <i>{desc[:60]}</i>\n"
            if not wq["completed"] and wq["progress"] >= wq["target"]:
                complete_buttons.append([InlineKeyboardButton(
                    text=f"✅ Сдать: {wq['quest_code'][:20]}",
                    callback_data=f"quest_turnw_{wq['id']}")])

    # === Клавиатура ===
    rows = []

    if complete_buttons:
        rows.append([InlineKeyboardButton(text="— ГОТОВО К СДАЧЕ —",
                                          callback_data="quest_noop")])
        for row in complete_buttons:
            rows.append(row)

    def f_btn(text, code):
        mark = "•" if filter_type == code else " "
        return InlineKeyboardButton(text=f"{mark} {text}",
                                     callback_data=f"qfilter_{code}")

    rows.append([f_btn("📋 Все", "all"), f_btn("📜 Сюжет", "story")])
    rows.append([f_btn("⚔️ Ежедн.", "daily"), f_btn("🏆 Еженед.", "weekly")])
    rows.append([InlineKeyboardButton(text="⭐ Очки заданий",
                                       callback_data="quest_points")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть",
                                       callback_data="quest_close")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # === Отправка ===
    # 1) Reply-сообщение → автоочистка через send_menu
    if reply_message is not None:
        try:
            from services.ui import send_menu
            await send_menu(reply_message, text, kb, uid=uid)
            return
        except Exception:
            # Если services.ui ещё нет — fallback на обычный ответ
            pass

    # 2) Callback → edit_text
    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=kb,
                                          parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass

    # 3) Обычная отправка в чат
    if chat_id:
        await g.bot.send_message(chat_id, text, reply_markup=kb,
                                  parse_mode=ParseMode.HTML)


# ================= ФИЛЬТР =================
@router.callback_query(F.data.startswith("qfilter_"))
async def qfilter_cb(c: CallbackQuery):
    filter_type = c.data.replace("qfilter_", "")
    if filter_type not in ("all", "story", "daily", "weekly"):
        await c.answer("Неизвестно"); return
    await _ensure_daily_quests(c.from_user.id)
    await _ensure_weekly_quests(c.from_user.id)
    await _show_quests(c.from_user.id, filter_type, edit_message=c.message)
    await c.answer()


@router.callback_query(F.data == "quest_noop")
async def quest_noop(c: CallbackQuery):
    await c.answer()


@router.callback_query(F.data == "quest_close")
async def quest_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


# ================= СОЗДАНИЕ КВЕСТОВ =================
async def _ensure_daily_quests(uid):
    reset_date = get_daily_reset_date()
    existing = await g.db.get_timed_quests(uid, "daily", reset_date)
    if existing:
        return
    picked = random.sample(DAILY_QUEST_POOL, min(3, len(DAILY_QUEST_POOL)))
    for q in picked:
        await g.db.create_timed_quest(
            uid, "daily", q["title"], q["target"],
            q["reward_gold"], q["reward_xp"], reset_date
        )


async def _ensure_weekly_quests(uid):
    reset_date = get_weekly_reset_date()
    existing = await g.db.get_timed_quests(uid, "weekly", reset_date)
    if existing:
        return
    for q in WEEKLY_QUESTS:
        await g.db.create_timed_quest(
            uid, "weekly", q["title"], q["target"],
            q["reward_gold"], q["reward_xp"], reset_date
        )


# ================= ПРОГРЕСС (из боя) =================
async def progress_quest(uid, quest_type, amount=1, target_name=None):
    """Обновить прогресс всех подходящих квестов игрока."""
    # Сюжетные
    active_story = await g.db.get_active_story_quests(uid)
    for q in active_story:
        quest = STORY_QUESTS.get(q["quest_code"])
        if not quest:
            continue
        if quest.get("type") == "kill":
            if target_name and quest["target"].lower() in target_name.lower():
                await g.db.incr_story_quest(uid, q["quest_code"], amount)

    # Ежедневные
    daily = await g.db.get_timed_quests(uid, "daily", get_daily_reset_date())
    for dq in daily:
        if dq["completed"]:
            continue
        tgt = dq["quest_code"].lower()
        match = False
        if quest_type == "kill_enemies" and ("охотник" in tgt or "убить" in tgt):
            match = True
        elif quest_type == "kill_bosses" and ("босс" in tgt or "легендарн" in tgt):
            match = True
        elif quest_type == "visit_locations" and "исследова" in tgt:
            match = True
        elif quest_type == "win_duels" and "арена" in tgt:
            match = True
        if match:
            await g.db.incr_timed_quest(uid, "daily", dq["quest_code"],
                                        get_daily_reset_date(), amount)

    # Еженедельные
    weekly = await g.db.get_timed_quests(uid, "weekly", get_weekly_reset_date())
    for wq in weekly:
        if wq["completed"]:
            continue
        tgt = wq["quest_code"].lower()
        match = False
        if quest_type == "kill_bosses" and ("босс" in tgt or "легендарн" in tgt):
            match = True
        elif quest_type == "win_duels" and "арена" in tgt:
            match = True
        if match:
            await g.db.incr_timed_quest(uid, "weekly", wq["quest_code"],
                                        get_weekly_reset_date(), amount)


# ================= ВЗЯТИЕ СЮЖЕТНОГО =================
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
    loc_name = W.get_location(quest.get("location", "village")).get("name", "?")
    await c.message.answer(
        f"📜 <b>Квест взят:</b> {quest['title']}\n\n"
        f"{quest['desc']}\n\n"
        f"🎯 Цель: убить <b>{quest['count']}×</b> {quest['target']}\n"
        f"📍 Локация: «{loc_name}»",
        parse_mode=ParseMode.HTML)
    await _ensure_daily_quests(c.from_user.id)
    await _ensure_weekly_quests(c.from_user.id)
    await _show_quests(c.from_user.id, "story", edit_message=c.message)


# ================= СДАЧА ЕЖЕДНЕВНЫХ =================
@router.callback_query(F.data.startswith("quest_turn_"))
async def quest_turn_cb(c: CallbackQuery):
    raw = c.data.replace("quest_turn_", "")
    try:
        qid = int(raw)
    except ValueError:
        await c.answer("Ошибка"); return

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM timed_quest_progress WHERE id=$1", qid
        )
    if not row or row["completed"]:
        await c.answer("Уже сдано"); return
    if row["progress"] < row["target"]:
        await c.answer(f"Не готово: {row['progress']}/{row['target']}",
                       show_alert=True); return

    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE timed_quest_progress SET completed=1 WHERE id=$1", qid
        )
    await g.db.add_gold(c.from_user.id, row["reward_gold"])
    await g.db.add_xp(c.from_user.id, row["reward_xp"])
    await g.db.add_quest_points(c.from_user.id, 5)

    await c.answer(f"✅ +{row['reward_gold']}💰 · +{row['reward_xp']} XP · +5⭐")
    await _show_quests(c.from_user.id, "daily", edit_message=c.message)


# ================= СДАЧА ЕЖЕНЕДЕЛЬНЫХ =================
@router.callback_query(F.data.startswith("quest_turnw_"))
async def quest_turnw_cb(c: CallbackQuery):
    raw = c.data.replace("quest_turnw_", "")
    try:
        qid = int(raw)
    except ValueError:
        await c.answer("Ошибка"); return

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM timed_quest_progress WHERE id=$1", qid
        )
    if not row or row["completed"]:
        await c.answer("Уже сдано"); return
    if row["progress"] < row["target"]:
        await c.answer(f"Не готово: {row['progress']}/{row['target']}",
                       show_alert=True); return

    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE timed_quest_progress SET completed=1 WHERE id=$1", qid
        )
    await g.db.add_gold(c.from_user.id, row["reward_gold"])
    await g.db.add_xp(c.from_user.id, row["reward_xp"])
    await g.db.add_quest_points(c.from_user.id, 15)

    await c.answer(f"✅ +{row['reward_gold']}💰 · +{row['reward_xp']} XP · +15⭐")
    await _show_quests(c.from_user.id, "weekly", edit_message=c.message)


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
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="qfilter_all")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
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
