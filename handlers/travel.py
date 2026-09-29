"""Путешествия, карта, кто в локации."""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
import world as W

router = Router()


# ================= СПРАВОЧНИКИ =================
RACES = {
    "human": "Человек", "elf": "Эльф", "dark_elf": "Тёмный эльф",
    "orc": "Орк", "dwarf": "Гном", "prit": "Плут",
    "demon": "Демон", "angel": "Ангел",
}

CLASSES = {
    "warrior": "Воин", "knight": "Рыцарь", "mage": "Маг",
    "archer": "Лучник", "assassin": "Убийца", "necro": "Некромант",
    "dancer": "Танцор", "destroyer": "Разрушитель", "tyrant": "Тиранин",
    "overlord": "Владыка", "priest": "Жрец", "bard": "Певчий",
    "guardian": "Страж", "hunter": "Охотник", "defender": "Защитник",
    "keeper": "Хранитель",
}


# ================= УТИЛИТЫ =================
def _kb():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
            [KeyboardButton(text="📋 Квесты"),    KeyboardButton(text="🗺 Карта")],
            [KeyboardButton(text="🚶 Идти"),      KeyboardButton(text="🌍 Мир")],
            [KeyboardButton(text="👥 Кто здесь"), KeyboardButton(text="🐾 Питомец")],
            [KeyboardButton(text="🏰 Подземелья"),KeyboardButton(text="⚒️ Кузница")],
            [KeyboardButton(text="🏛 Гильдия"),   KeyboardButton(text="🎁 Награда")],
            [KeyboardButton(text="🏅 Рейтинг"),   KeyboardButton(text="💎 Премиум")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что делает герой?"
    )


def travel_kb(location_code, player_level):
    rows = []
    for code, info in W.get_neighbors(location_code):
        can, reason = W.can_enter(code, player_level)
        if can:
            rows.append([InlineKeyboardButton(text=f"→ {info['name']}",
                                              callback_data=f"travel_to_{code}")])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🔒 {info['name']} (ур.{info['level_req']}+)",
                callback_data="travel_locked")])
    rows.append([InlineKeyboardButton(text="❌ Остаться", callback_data="travel_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _broadcast_to_location(location_code, text, exclude_uid=0):
    players = await g.db.get_players_at_location(location_code, exclude_uid)
    for p in players:
        try:
            await g.bot.send_message(p["user_id"], text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


# ================= КАРТА =================
@router.message(Command("map"))
@router.message(F.text == "🗺 Карта")
async def map_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    loc_code = u.get("location_code", "village")
    visited = await g.db.get_all_location_codes_visited(m.from_user.id)
    visited_set = set(visited)

    lines = ["🗺 <b>Карта мира</b>\n"]
    for code, info in W.LOCATIONS.items():
        marker = "📍" if code == loc_code else ("✅" if info["name"] in visited_set else "❓")
        if code == loc_code or info["name"] in visited_set:
            lines.append(f"{marker} {info['name']}")
        else:
            lines.append("❓ Неизвестная локация")

    captured = await g.db.get_all_captured_locations()
    if captured:
        lines.append("\n<b>Захвачено гильдиями:</b>")
        for c in captured:
            loc_name = W.get_location(c["location_code"]).get("name", c["location_code"])
            lines.append(f"🏴 {loc_name} — [{c['tag']}] {c['name']}")

    lines.append(f"\n📍 Ты в: <b>{W.get_location(loc_code).get('name', '?')}</b>")
    lines.append(f"\nВсего открыто: {len(visited_set)}/{len(W.LOCATIONS)}")
    await m.answer("\n".join(lines), reply_markup=_kb(), parse_mode=ParseMode.HTML)


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
                       reply_markup=_kb(), parse_mode=ParseMode.HTML)
        return
    await m.answer(
        f"🚶 <b>Куда идёшь?</b>\n\n"
        f"📍 Сейчас ты в: <b>{loc['name']}</b>\n"
        f"<i>{loc['desc']}</i>",
        reply_markup=travel_kb(loc_code, u["level"]),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("travel_to_"))
async def travel_do(c):
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
    await g.db.set_location_code(c.from_user.id, code)
    await g.db.add_location(c.from_user.id, new_loc["name"])
    await g.db.progress_quest(c.from_user.id, "visit_locations", 1)

    loc = W.get_location(code)
    event = await g.db.get_active_event(code)
    owner = await g.db.get_location_owner(code)

    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

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

    await g.bot.send_message(c.from_user.id, text, reply_markup=_kb(),
                             parse_mode=ParseMode.HTML)
    await c.answer(f"→ {loc['name']}")

    await _broadcast_to_location(
        code,
        f"👤 <b>{u['char_name']}</b> прибыл в локацию.",
        exclude_uid=c.from_user.id
    )


@router.callback_query(F.data == "travel_locked")
async def travel_locked(c):
    await c.answer("Уровень слишком низкий для этой локации", show_alert=True)


@router.callback_query(F.data == "travel_cancel")
async def travel_cancel(c):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
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
    if not players:
        await m.answer(
            f"👥 В «{loc_name}» больше никого нет.\n\n"
            f"<i>Когда другие игроки зайдут сюда, ты их увидишь.</i>",
            reply_markup=_kb(), parse_mode=ParseMode.HTML)
        return
    lines = []
    for p in players:
        race = RACES.get(p["race"], "?")
        cls = CLASSES.get(p["class"], "?")
        gtag = ""
        if p.get("guild_id"):
            guild = await g.db.get_guild(p["guild_id"])
            if guild:
                gtag = f" [{guild['tag']}]"
        lines.append(f"• <b>{p['char_name']}</b>{gtag} (Ур.{p['level']}, {race} {cls})")
    await m.answer(f"👥 <b>В «{loc_name}»:</b>\n\n" + "\n".join(lines) +
                   f"\n\n<i>/duel Имя — вызвать на дуэль</i>",
                   reply_markup=_kb(), parse_mode=ParseMode.HTML)
