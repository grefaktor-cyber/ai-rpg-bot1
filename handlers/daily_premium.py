"""Ежедневная награда. Премиум — в handlers/premium.py."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb

router = Router()


@router.message(Command("daily"))
@router.message(F.text == "🎁 Награда")
async def daily(m: Message):
    streak = await g.db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer("🎁 Уже получал сегодня.", reply_markup=main_kb()); return
    bonus = {1: 5, 2: 5, 3: 10, 4: 10, 5: 15, 6: 15, 7: 30}.get(streak, 10)
    gold_bonus = streak * 20
    await g.db.add_gold(m.from_user.id, gold_bonus)
    await g.db.add_material(m.from_user.id, "iron", 1)
    u = await g.db.get_user(m.from_user.id)
    msg = (f"🎁 <b>Награда!</b>\n\nДень {streak}\n"
           f"+{gold_bonus}💰 · +1 🔩\n"
           f"⚡ Энергия: {u.get('energy', 0)}/{u.get('energy_max', 20)}")
    if streak == 7:
        await g.db.add_item(m.from_user.id, "Амулет мудреца")
        msg += "\n\n🏆 <b>Амулет мудреца!</b>"
    await m.answer(msg, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
