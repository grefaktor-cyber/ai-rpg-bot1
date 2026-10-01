"""Мир: события, NPC-список, граффити."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb, npc_list_kb, npc_menu_kb
import world as W

router = Router()


# ================= МИР =================
@router.message(Command("world"))
@router.message(F.text == "🌍 Мир")
async def world_cmd(m: Message):
    events = await g.db.get_all_active_events()
    captured = await g.db.get_all_captured_locations()

    text = "🌍 <b>Мир</b>\n\n"

    if events:
        text += "<b>🔥 Активные события:</b>\n"
        for e in events:
            loc_name = W.get_location(e["location_code"]).get("name", "?")
            text += f"• {e['event_name']} в <b>{loc_name}</b> — {e['event_desc']}\n"
        text += "\n"
    else:
        text += "<i>Сейчас в мире тихо.</i>\n\n"

    if captured:
        text += "<b>🏴 Захваченные локации:</b>\n"
        for c_ in captured:
            loc_name = W.get_location(c_["location_code"]).get("name", "?")
            text += f"• {loc_name} — [{c_['tag']}] {c_['name']}\n"
        text += "\n"

    recent = await g.db.get_world_events(8)
    if recent:
        text += "<b>📰 Последние события:</b>\n"
        for e in recent:
            text += f"• <b>{e['username'] or '?'}</b>: {e['event_text']}\n"

    from core.keyboards import world_menu_kb
    from services.ui import send_menu
    await send_menu(m, text, world_menu_kb(has_events=bool(events)))


@router.callback_query(F.data == "world_close")
async def world_close_cb(c: CallbackQuery):
    from services.ui import close_menu
    await close_menu(c)
    await c.answer()


@router.callback_query(F.data == "world_refresh")
async def world_refresh_cb(c: CallbackQuery):
    # Перерисовываем меню
    events = await g.db.get_all_active_events()
    captured = await g.db.get_all_captured_locations()

    text = "🌍 <b>Мир</b>\n\n"
    if events:
        text += "<b>🔥 Активные события:</b>\n"
        for e in events:
            loc_name = W.get_location(e["location_code"]).get("name", "?")
            text += f"• {e['event_name']} в <b>{loc_name}</b> — {e['event_desc']}\n"
        text += "\n"
    else:
        text += "<i>Сейчас в мире тихо.</i>\n\n"
    if captured:
        text += "<b>🏴 Захваченные локации:</b>\n"
        for c_ in captured:
            loc_name = W.get_location(c_["location_code"]).get("name", "?")
            text += f"• {loc_name} — [{c_['tag']}] {c_['name']}\n"
        text += "\n"
    recent = await g.db.get_world_events(8)
    if recent:
        text += "<b>📰 Последние события:</b>\n"
        for e in recent:
            text += f"• <b>{e['username'] or '?'}</b>: {e['event_text']}\n"

    from core.keyboards import world_menu_kb
    try:
        await c.message.edit_text(text,
                                   reply_markup=world_menu_kb(has_events=bool(events)),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer("🔄")


# ================= NPC =================
@router.message(Command("npc"))
async def npc_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты в бою!"); return
    code = u.get("location_code", "village")
    npcs = W.get_npcs_in_location(code)
    if not npcs:
        await m.answer("👤 В этой локации нет NPC.", reply_markup=main_kb()); return
    loc_name = W.get_location(code).get("name", "?")
    await m.answer(f"👤 <b>NPC в «{loc_name}»</b>\n\nВыбери, с кем поговорить:",
                   reply_markup=npc_list_kb(code, W), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "npc_close")
async def npc_close(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("npc_") & ~F.data.startswith("npcquest_") & ~F.data.startswith("npctalk_"))
async def npc_pick(c: CallbackQuery):
    if c.data == "npc_close":
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await c.answer(); return
    code = c.data.replace("npc_", "")
    npc = W.get_npc(code)
    if not npc:
        await c.answer("Не найдено"); return
    text = f"👤 <b>{npc['name']}</b>\n\n<i>{npc['greeting']}</i>"
    await c.message.edit_text(text, reply_markup=npc_menu_kb(code, W),
                              parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("npctalk_"))
async def npc_talk(c: CallbackQuery):
    code = c.data.replace("npctalk_", "")
    npc = W.get_npc(code)
    if not npc:
        await c.answer("Не найдено"); return
    await c.answer()
    await c.message.answer(
        f"💬 <i>{npc['name']} смотрит на тебя, ожидая, что ты скажешь.</i>\n\n"
        f"Просто напиши, что говоришь — ИИ ответит от лица NPC.",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML
    )


# ================= ГРАФФИТИ =================
@router.message(Command("write"))
async def write_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await m.answer("Использование: /write текст"); return
    text = parts[1].strip()[:200]
    loc_name = W.get_location(u.get("location_code", "village")).get("name", "?")
    await g.db.add_graffiti(m.from_user.id, u["char_name"], loc_name, text)
    await m.answer(f"✍️ Запись оставлена в «{loc_name}».",
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(m.from_user.id, "graffiti"):
        await m.answer("🏆 Достижение: ✍️ Летописец", parse_mode=ParseMode.HTML)


@router.message(Command("read"))
async def read_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    loc_name = W.get_location(u.get("location_code", "village")).get("name", "?")
    notes = await g.db.get_graffiti(loc_name, 15)
    if not notes:
        await m.answer(f"📜 В «{loc_name}» нет записей.",
                       reply_markup=main_kb()); return
    lines = [f"• <b>{n['username']}</b>: <i>{n['text']}</i>" for n in notes]
    await m.answer(f"📜 <b>Записи в «{loc_name}»:</b>\n\n" + "\n".join(lines),
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)
