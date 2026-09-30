"""Старт: /start, согласие, создание героя, главное меню."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS
from core.keyboards import (
    main_kb, race_selection_kb, class_selection_kb,
    faction_selection_kb, pvp_kb,
)
from core.texts import CONSENT_TEXT
from config import ADMIN_IDS
import world as W


router = Router()


# ================= СОГЛАСИЕ =================
def _consent_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Согласен (18+)", callback_data="consent_yes"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no"),
    ]])


@router.message(Command("start"))
async def start(m: Message):
    args = m.text.split()
    referrer_id = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = await g.db.get_user(m.from_user.id, m.from_user.username or "")

    if referrer_id and user["referred_by"] == 0:
        if await g.db.set_referrer(m.from_user.id, referrer_id):
            await m.answer("🎉 Вы пришли по приглашению!")
            try:
                await g.bot.send_message(referrer_id,
                    "🎉 По вашей ссылке пришёл новый игрок! +10 действий.")
            except Exception:
                pass
            user = await g.db.get_user(m.from_user.id)

    if not user["consent_given"]:
        await m.answer(CONSENT_TEXT, reply_markup=_consent_kb(), parse_mode=ParseMode.HTML)
        return

    if not user["race"]:
        await show_race_selection(m); return
    if not user["class"]:
        await show_class_selection(m, user["race"]); return
    if not user["faction"]:
        await show_faction_selection(m); return
    if not user["char_name"]:
        await m.answer("✏️ Как зовут вашего героя? (2–20 символов)")
        return

    combat = await g.db.get_combat(m.from_user.id)
    if combat:
        if combat.get("is_pvp"):
            await m.answer("⚔️ Ты в дуэли!", reply_markup=pvp_kb(combat["my_turn"]))
        else:
            from services.combat_service import send_combat_state
            await send_combat_state(m.chat.id, user, combat, "Ты в бою!")
        return

    await show_main_menu(m, user)


@router.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await g.db.give_consent(c.from_user.id)
    await c.message.edit_text("✅ Согласие получено. Создадим героя!",
                              parse_mode=ParseMode.HTML)
    await show_race_selection(c.message)


@router.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс.")


# ================= СОЗДАНИЕ ГЕРОЯ =================
async def show_race_selection(m):
    await g.bot.send_message(m.chat.id, "🧝 <b>Выбери расу:</b>",
                             reply_markup=race_selection_kb(RACES),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("race_"))
async def on_race(c: CallbackQuery):
    code = c.data.replace("race_", "")
    if code not in RACES:
        await c.answer("Ошибка"); return
    await g.db.set_race(c.from_user.id, code)
    await c.message.edit_text(f"✅ Раса: <b>{RACES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_class_selection(c.message, code)


async def show_class_selection(m, race_code):
    await g.bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                             reply_markup=class_selection_kb(CLASSES),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("class_"))
async def on_class(c: CallbackQuery):
    code = c.data.replace("class_", "")
    if code not in CLASSES:
        await c.answer("Ошибка"); return
    await g.db.set_class(c.from_user.id, code)
    await c.message.edit_text(f"✅ Класс: <b>{CLASSES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_faction_selection(c.message)


async def show_faction_selection(m):
    await g.bot.send_message(m.chat.id, "🏛 <b>Выбери фракцию:</b>",
                             reply_markup=faction_selection_kb(FACTIONS),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("faction_"))
async def on_faction(c: CallbackQuery):
    code = c.data.replace("faction_", "")
    if code not in FACTIONS:
        await c.answer("Ошибка"); return
    await g.db.set_faction(c.from_user.id, code)
    await c.message.edit_text(f"✅ Фракция: <b>{FACTIONS[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await g.bot.send_message(c.from_user.id,
                             "✏️ Напиши <b>имя героя</b> (2–20 символов).",
                             parse_mode=ParseMode.HTML)


# ================= ГЛАВНОЕ МЕНЮ =================
async def show_main_menu(m, user):
    loc_code = user.get("location_code", "village")
    loc = W.get_location(loc_code) or {}
    event = await g.db.get_active_event(loc_code)
    owner = await g.db.get_location_owner(loc_code)
    is_admin = user["user_id"] in ADMIN_IDS
    admin_tag = " 🛠 <i>ADMIN</i>" if is_admin else ""

    header = f"🎮 <b>С возвращением, {user['char_name']}!</b>{admin_tag}\n\n"
    header += f"⭐ Ур. {user['level']} · XP: {user['xp']}\n"
    header += f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
    header += f"💰 Золото: {user['gold']}\n"
    header += f"📍 <b>{loc.get('name', '?')}</b>"
    if owner:
        header += f" 🏴 [{owner.get('guild_tag', '?')}]"
    header += "\n"
    if event:
        header += f"\n{event['event_name']}: <i>{event['event_desc']}</i>\n"
    header += "\nОпиши действие или жми кнопки 👇"
    await m.answer(header, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
