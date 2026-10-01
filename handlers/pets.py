"""Питомцы. back+close."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from core.game_data import PETS
from core.keyboards import main_kb
from services.ui import send_menu, close_menu
from config import ADMIN_IDS

router = Router()


class PetStates(StatesGroup):
    waiting_new_name = State()


def _pet_menu_kb(has_pet=False):
    rows = []
    if has_pet:
        rows.append([InlineKeyboardButton(
            text="✏️ Переименовать",
            callback_data="pet_rename_start")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_progress"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _pets_shop_kb():
    rows = []
    for code, p in PETS.items():
        rows.append([InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}💰",
            callback_data=f"pet_buy_{code}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_progress"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _render_pet(pet):
    pet_info = PETS.get(pet["pet_type"], {})
    xp_need = pet["level"] * 100
    bonus_str = ", ".join(f"+{v} {k.upper()}"
                           for k, v in pet_info.get("bonus", {}).items())
    return (
        f"🐾 <b>{pet['name']}</b> ({pet_info.get('name', '?')})\n\n"
        f"📊 Уровень: <b>{pet['level']}</b>\n"
        f"⭐ XP: {pet['xp']}/{xp_need}\n\n"
        f"<b>Эффект:</b> {pet_info.get('desc', '—')}\n"
        f"<b>Пассивно:</b> {bonus_str}"
    )


def _render_shop():
    text = "🐾 <b>Питомцы</b>\n\nВыбери верного спутника:\n\n"
    for code, p in PETS.items():
        text += f"• <b>{p['name']}</b> ({p['price']}💰)\n   <i>{p['desc']}</i>\n\n"
    text += "<i>Питомец даёт пассивные бонусы.</i>"
    return text


@router.message(Command("pet"))
@router.message(F.text == "🐾 Питомец")
async def pet_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    pet = await g.db.get_pet(m.from_user.id)
    if pet:
        await send_menu(m, _render_pet(pet), _pet_menu_kb(has_pet=True))
    else:
        await send_menu(m, _render_shop(), _pets_shop_kb())


@router.callback_query(F.data.startswith("pet_buy_"))
async def pet_buy(c: CallbackQuery):
    code = c.data.replace("pet_buy_", "")
    if code not in PETS:
        await c.answer("Нет"); return
    p = PETS[code]
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin:
        ok = await g.db.spend_gold(c.from_user.id, p["price"])
        if not ok:
            await c.answer(f"❌ Нужно {p['price']}💰", show_alert=True); return
    await g.db.add_pet(c.from_user.id, code, p["name"])
    if await g.db.add_achievement(c.from_user.id, "pet_owner"):
        pass

    pet = await g.db.get_pet(c.from_user.id)
    await c.answer(f"✅ {p['name']} теперь с тобой!")
    try:
        await c.message.edit_text(_render_pet(pet),
                                   reply_markup=_pet_menu_kb(has_pet=True),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        pass


@router.callback_query(F.data == "pet_rename_start")
async def pet_rename_start(c: CallbackQuery, state: FSMContext):
    pet = await g.db.get_pet(c.from_user.id)
    if not pet:
        await c.answer("У тебя нет питомца", show_alert=True); return
    await state.set_state(PetStates.waiting_new_name)
    await c.answer()
    await c.message.answer(
        "✏️ Напиши новое имя для питомца (2–20 символов).\n"
        "Или отправь /cancel для отмены.",
        parse_mode=ParseMode.HTML)


@router.message(PetStates.waiting_new_name)
async def pet_rename_input(m: Message, state: FSMContext):
    if m.text and m.text.strip() == "/cancel":
        await state.clear()
        await m.answer("Отменено.")
        return
    name = (m.text or "").strip()[:20]
    if len(name) < 2:
        await m.answer("Имя 2–20 символов:"); return
    await g.db.set_pet_name(m.from_user.id, name)
    await state.clear()
    await m.answer(f"🐾 Питомец теперь зовётся <b>{name}</b>!",
                    reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("pet_name"))
async def pet_name_cmd(m: Message):
    pet = await g.db.get_pet(m.from_user.id)
    if not pet:
        await m.answer("У тебя нет питомца."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or len(parts[1].strip()) < 2:
        await m.answer("Использование: /pet_name Имя (2–20)"); return
    name = parts[1].strip()[:20]
    await g.db.set_pet_name(m.from_user.id, name)
    await m.answer(f"🐾 Питомец теперь зовётся <b>{name}</b>!",
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "pet_close")
async def pet_close_cb(c: CallbackQuery):
    await close_menu(c)
    await c.answer()
