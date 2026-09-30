"""Квесты: ежедневные + NPC-квесты."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
import world as W

router = Router()


# ================= ЕЖЕДНЕВНЫЕ =================
@router.message(Command("quests"))
@router.message(F.text == "📋 Квесты")
async def quests_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя: /start"); return
    daily = await g.db.get_daily_quests(m.from_user.id)
    npc_active = await g.db.get_user_quests(m.from_user.id)
    quest_names = {
        "kill_enemies": "⚔️ Убить врагов",
        "visit_locations": "🗺 Посетить локации",
        "win_duels": "🗡 Победить в дуэлях",
        "craft_items": "⚒️ Создать предметы",
        "earn_gold": "💰 Заработать золото",
    }
    text = "📋 <b>Ежедневные квесты</b>\n\n"
    for q in daily:
        name = quest_names.get(q["quest_type"], q["quest_type"])
        done = "✅" if q["completed"] else "⏳"
        text += (f"{done} <b>{name}</b>\n"
                 f"   {q['progress']}/{q['target']} · {q['reward_gold']}💰 +{q['reward_xp']} XP\n\n")
    active_npc = [x for x in npc_active if not x["completed"]]
    done_npc = [x for x in npc_active if x["completed"]]
    if active_npc:
        text += "\n📜 <b>Активные NPC-квесты:</b>\n"
        for x in active_npc:
            q = W.get_quest(x["quest_code"])
            if q:
                text += f"• {q['title']} — {x['progress']}/{q['count']}\n"
    if done_npc:
        text += f"\n✅ Выполнено NPC-квестов: {len(done_npc)}"
    await m.answer(text, reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= NPC-КВЕСТЫ =================
@router.callback_query(F.data.startswith("npcquest_"))
async def npc_quest_open(c: CallbackQuery):
    if c.data.startswith("npcquest_accept_") or c.data.startswith("npcquest_done_"):
        return
    qcode = c.data.replace("npcquest_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    u = await g.db.get_user(c.from_user.id)
    if u["level"] < q.get("req_level", 1):
        await c.answer(f"Нужен уровень {q['req_level']}+", show_alert=True); return
    prog = await g.db.get_npc_quest(c.from_user.id, qcode)
    if prog and prog["completed"]:
        await c.answer("Этот квест уже выполнен", show_alert=True); return
    if prog:
        text = (f"📜 <b>{q['title']}</b>\n\n{q['desc']}\n\n"
                f"Прогресс: {prog['progress']}/{q['count']}\n"
                f"Награда: {q['reward_gold']}💰 + {q['reward_xp']} XP")
        await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сдать",
                                  callback_data=f"npcquest_done_{qcode}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"npc_{q['npc']}")],
        ]), parse_mode=ParseMode.HTML)
        return
    text = (f"📜 <b>{q['title']}</b>\n\n{q['desc']}\n\n"
            f"Награда: {q['reward_gold']}💰 + {q['reward_xp']} XP")
    if q.get("reward_item"):
        text += f"\n🎁 Предмет: {q['reward_item']}"
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять",
                              callback_data=f"npcquest_accept_{qcode}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"npc_{q['npc']}")],
    ]), parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("npcquest_accept_"))
async def npc_quest_accept(c: CallbackQuery):
    qcode = c.data.replace("npcquest_accept_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    ok = await g.db.accept_npc_quest(c.from_user.id, qcode)
    if not ok:
        await c.answer("Квест уже активен", show_alert=True); return
    await c.answer("Квест принят!")
    await c.message.edit_text(
        f"📜 <b>{q['title']}</b> — принят!\n\n{q['desc']}",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("npcquest_done_"))
async def npc_quest_done(c: CallbackQuery):
    qcode = c.data.replace("npcquest_done_", "")
    q = W.get_quest(qcode)
    if not q:
        await c.answer("Не найдено"); return
    prog = await g.db.get_npc_quest(c.from_user.id, qcode)
    if not prog or prog["completed"]:
        await c.answer("Уже сдано", show_alert=True); return
    if prog["progress"] < q["count"]:
        await c.answer(f"Не готово: {prog['progress']}/{q['count']}", show_alert=True); return
    await g.db.complete_npc_quest(c.from_user.id, qcode)
    await g.db.add_gold(c.from_user.id, q["reward_gold"])
    await g.db.add_xp(c.from_user.id, q["reward_xp"])
    if q.get("reward_item"):
        await g.db.add_item(c.from_user.id, q["reward_item"])
    text = (f"✅ <b>Квест выполнен: {q['title']}</b>\n\n"
            f"+{q['reward_gold']}💰 · +{q['reward_xp']} XP")
    if q.get("reward_item"):
        text += f"\n🎁 Получен: {q['reward_item']}"
    all_q = await g.db.get_user_quests(c.from_user.id)
    done_count = sum(1 for x in all_q if x["completed"])
    if done_count >= 5:
        if await g.db.add_achievement(c.from_user.id, "quest_master"):
            text += "\n\n🏆 Достижение: 📜 Мастер квестов"
    await c.answer("Квест сдан!")
    await c.message.edit_text(text, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
