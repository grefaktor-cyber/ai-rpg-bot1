"""Питомцы: покупка, переименование."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import PETS
from core.keyboards import main_kb, pets_kb
from config import ADMIN_IDS

router = Router()


@router.message(Command("pet"))
@router.message(F.text == "🐾 Питомец")
async def pet_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    pet = await g.db.get_pet(m.from_user.id)
    if pet:
        pet_info = PETS.get(pet["pet_type"], {})
        await m.answer(
            f"🐾 <b>{pet['name']}</b> ({pet_info.get('name', '?')})\n"
            f"Уровень: {pet['level']}\nXP: {pet['xp']}/{pet['level'] * 100}\n\n"
            f"<b>Эффект:</b> {pet_info.get('desc', '—')}\n"
            f"<b>Пассивно:</b> " + ", ".join(f"+{v} {k.upper()}"
                                              for k, v in pet_info.get("bonus", {}).items()) +
            f"\n\n<i>Переименовать: /pet_name НовоеИмя</i>",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return
    text = "🐾 <b>Питомцы</b>\n\nВыбери верного спутника:\n\n"
    for code, p in PETS.items():
        text += f"• <b>{p['name']}</b> ({p['price']}💰) — {p['desc']}\n"
    await m.answer(text, reply_markup=pets_kb(PETS), parse_mode=ParseMode.HTML)


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
    await c.answer(f"✅ {p['name']} теперь с тобой!")
    await c.message.answer(f"🐾 <b>{p['name']}</b> присоединился!\n\nЭффект: {p['desc']}",
                           reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(c.from_user.id, "pet_owner"):
        await c.message.answer("🏆 Достижение: 🐾 Хозяин", parse_mode=ParseMode.HTML)


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
