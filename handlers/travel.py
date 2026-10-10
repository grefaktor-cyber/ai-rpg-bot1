"""Путешествия, карта, кто в локации. back+close везде. + картинки локаций."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES
from core.keyboards import main_kb, travel_kb as build_travel_kb
from services.broadcast import broadcast_to_location
from services.ui import send_menu, close_menu, send_location_photo
import world as W

router = Router()


def _back_close_row(back_cb):
    return [
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]


# ================= КАРТА =================
@router.message(Command("map"))
@router.message(F.text == "🗺 Карта")
async def map_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    loc_code = u.get("location_code", "village")
    visited = await g.db.get_all_location_codes_visited(m.from_user.id)
    visited_set = set(visited)
    captured = await g.db.get_all_captured_locations()
    captured_map = {c["location_code"]: c for c in captured}

    def loc_icon(code):
        info = W.get_location(code) or {}
        name = info.get("name", "?")
        if code == loc_code:
            marker = "📍"
        elif name in visited_set:
            marker = "✅"
        else:
            marker = "❓"
        guild_marker = " 🏴" if code in captured_map else ""
        lvl = info.get("level_req", 1)
        if lvl <= 3:
            diff = "🟢"
        elif lvl <= 8:
            diff = "🟡"
        elif lvl <= 15:
            diff = "🟠"
        else:
            diff = "🔴"
        if code == loc_code or name in visited_set:
            return f"{marker} {diff} {name[:14]}{guild_marker}"
        return f"{marker} {diff} ???{guild_marker}"

    row1 = "  ".join([loc_icon("tavern"), "──", loc_icon("village"),
                       "──", loc_icon("road")])
    row2 = "       │                 │"
    row3 = "  ".join([loc_icon("forest"), "──", loc_icon("ruins"),
                       "──", loc_icon("mountains")])
    row4 = "  │                 │"
    row5 = "  ".join([loc_icon("glade"), "  ", loc_icon("swamp"),
                       "  ", loc_icon("cave")])
    row6 = "                     │"
    row7 = "  ".join([" " * 22, "──", loc_icon("port")])
    row8 = "                            │"
    row9 = "  ".join([" " * 22, "──", loc_icon("sea"), "──", loc_icon("island")])

    text = "🗺 <b>Карта мира</b>\n\n"
    text += "<pre>"
    text += f"{row1}\n{row2}\n{row3}\n{row4}\n{row5}\n{row6}\n{row7}\n{row8}\n{row9}\n"
    text += "</pre>\n"

    text += "<b>Легенда:</b>\n"
    text += "📍 Ты здесь · ✅ Посещено · ❓ Неизвестно\n"
    text += "🏴 Захвачено гильдией\n"
    text += "🟢 Ур. 1-3 · 🟡 4-8 · 🟠 9-15 · 🔴 16+\n"

    loc = W.get_location(loc_code) or {}
    text += f"\n📍 <b>Ты в:</b> {loc.get('name', '?')}\n"
    text += f"<i>{loc.get('desc', '')}</i>\n"

    if loc_code in captured_map:
        c = captured_map[loc_code]
        text += f"\n🏴 Владелец: <b>[{c['tag']}]</b> {c['name']}\n"

    event = await g.db.get_active_event(loc_code)
    if event:
        text += f"\n{event['event_name']}: <i>{event['event_desc']}</i>\n"

    total = len(W.LOCATIONS)
    visited_count = len([l for l in W.LOCATIONS
                          if W.get_location(l)["name"] in visited_set])
    text += f"\n🌍 <b>Открыто: {visited_count}/{total}</b>"

    rows = []
    neighbors = W.get_neighbors(loc_code)
    for code, info in neighbors:
        can, reason = W.can_enter(code, u["level"])
        marker = "" if can else "🔒 "
        rows.append([InlineKeyboardButton(
            text=f"{marker}→ {info['name']}",
            callback_data=f"travel_to_{code}" if can else "travel_locked"
        )])
    rows.append(_back_close_row("menu_game"))

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await send_menu(m, text, kb)


@router.callback_query(F.data == "map_close")
async def map_close_cb(c: CallbackQuery):
    await close_menu(c)
    await c.answer()


# ================= ПУТЕШЕСТВИЕ =================
@router.message(Command("travel"))
@router.message(F.text == "🚶 Идти")
async def travel_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя.")
        return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!")
        return
    loc_code = u.get("location_code", "village")
    loc = W.get_location(loc_code)
    neighbors = W.get_neighbors(loc_code)
    if not neighbors:
        await m.answer(f"📍 Ты в <b>{loc['name']}</b>. Отсюда нет пути.",
                       reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return
    rows = []
    for code, info in neighbors:
        can, reason = W.can_enter(code, u["level"])
        if can:
            rows.append([InlineKeyboardButton(
                text=f"→ {info['name']}",
                callback_data=f"travel_to_{code}")])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🔒 {info['name']} (ур.{info['level_req']}+)",
                callback_data="travel_locked")])
    rows.append(_back_close_row("menu_game"))
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await send_menu(
        m,
        f"🚶 <b>Куда идёшь?</b>\n\n"
        f"📍 Сейчас ты в: <b>{loc['name']}</b>\n"
        f"<i>{loc['desc']}</i>",
        kb
    )


@router.callback_query(F.data.startswith("travel_to_"))
async def travel_do(c: CallbackQuery):
    code = c.data.replace("travel_to_", "")
    if code not in W.LOCATIONS:
        await c.answer("Не найдено")
        return
    u = await g.db.get_user(c.from_user.id)
    if await g.db.get_combat(c.from_user.id):
        await c.answer("⚔️ Ты в бою!")
        return
    cur_code = u.get("location_code", "village")
    if code not in W.LOCATIONS[cur_code]["exits"]:
        await c.answer("Отсюда туда не попасть!", show_alert=True)
        return
    can, reason = W.can_enter(code, u["level"])
    if not can:
        await c.answer(reason, show_alert=True)
        return

    old_name = W.get_location(cur_code).get("name", "?")
    new_loc = W.get_location(code)

    visited = await g.db.get_all_location_codes_visited(c.from_user.id)
    first_visit = new_loc["name"] not in visited

    await g.db.set_location_code(c.from_user.id, code)
    await g.db.add_location(c.from_user.id, new_loc["name"])

    # === ЗАЧЁТ КВЕСТА «Исследователь» ===
    await g.db.progress_quest(c.from_user.id, "visit_locations", 1)
    try:
        from handlers.quests import progress_quest as quest_progress
        await quest_progress(c.from_user.id, "visit_locations", 1)
    except Exception as _e:
        import logging
        logging.error(f"[TRAVEL QUEST] {_e}", exc_info=True)

    if first_visit:
        await g.db.add_journal_entry(
            c.from_user.id,
            f"Впервые посетил «{new_loc['name']}»",
            "location"
        )

    loc = W.get_location(code)
    event = await g.db.get_active_event(code)
    owner = await g.db.get_location_owner(code)

    await close_menu(c)

    # === ТЕКСТ О ЛОКАЦИИ ===
    text = f"🚶 <i>{old_name} → {loc['name']}</i>\n\n"
    text += f"📍 <b>{loc['name']}</b>\n<i>{loc['desc']}</i>\n"
    if owner:
        text += f"\n🏴 Владелец: <b>[{owner['guild_tag']}]</b> {owner['guild_name']}"
    if event:
        text += f"\n\n{event['event_name']}: <i>{event['event_desc']}</i>"
    npcs = W.get_npcs_in_location(code)
    if npcs:
        text += "\n\n👤 <b>Здесь есть:</b>"
        for c2, info in npcs:
            text += f"\n• {info['name']}"
    if loc.get("enemies"):
        text += f"\n\n⚔️ <i>Враги: {', '.join(loc['enemies'])}</i>"
    if first_visit:
        text += "\n\n🆕 <b>Новая локация открыта!</b>"

    # 🎨 Отправляем с картинкой локации
    await send_location_photo(
        c.from_user.id, code, text, kb=main_kb()
    )
    await c.answer(f"→ {loc['name']}")

    await broadcast_to_location(
        code,
        f"👤 <b>{u['char_name']}</b> прибыл в локацию.",
        exclude_uid=c.from_user.id
    )


@router.callback_query(F.data == "travel_locked")
async def travel_locked(c: CallbackQuery):
    await c.answer("Уровень слишком низкий для этой локации", show_alert=True)


@router.callback_query(F.data == "travel_cancel")
async def travel_cancel(c: CallbackQuery):
    await close_menu(c)
    await c.answer("Остаёшься здесь")


# ================= КТО ЗДЕСЬ =================
@router.message(Command("who"))
@router.message(F.text == "👥 Кто здесь")
async def who_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя.")
        return
    code = u.get("location_code", "village")
    players = await g.db.get_players_at_location(code, u["user_id"])
    loc_name = W.get_location(code).get("name", "?")

    rows = []
    if not players:
        text = (f"👥 В «{loc_name}» больше никого нет.\n\n"
                f"<i>Когда другие игроки зайдут сюда, ты их увидишь.</i>")
    else:
        from core.titles import TITLES
        lines = [f"👥 <b>В «{loc_name}»:</b>\n"]
        for p in players:
            race = RACES.get(p["race"], {}).get("name", "?")
            cls = CLASSES.get(p["class"], {}).get("name", "?")
            gtag = ""
            if p.get("guild_id"):
                guild = await g.db.get_guild(p["guild_id"])
                if guild:
                    gtag = f" [{guild['tag']}]"
            p_user = await g.db.get_user(p["user_id"])
            t_code = p_user.get("active_title", "") if p_user else ""
            t_str = f" {TITLES[t_code]['icon']}" if (t_code and t_code in TITLES) else ""
            lines.append(f"• <b>{p['char_name']}</b>{t_str}{gtag} (Ур.{p['level']}, {race} {cls})")
        lines.append("")
        lines.append("<i>/duel Имя — вызвать на дуэль</i>")
        text = "\n".join(lines)

    rows.append(_back_close_row("menu_social"))
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await send_menu(m, text, kb)
