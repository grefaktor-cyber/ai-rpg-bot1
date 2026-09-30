"""Ежедневная награда, премиум, оплата Stars."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton, LabeledPrice)
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from config import PREMIUM_PRICE_STARS

router = Router()


# ================= ЕЖЕДНЕВНАЯ =================
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
           f"⚡ Энергия полностью восстановлена: {u.get('energy', 0)}/{u.get('energy_max', 20)}")
    if streak == 7:
        await g.db.add_item(m.from_user.id, "Амулет мудреца")
        msg += "\n\n🏆 <b>Амулет мудреца!</b>"
    await m.answer(msg, reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= ПРЕМИУМ =================
@router.message(Command("premium"))
@router.message(F.text == "💎 Премиум")
async def premium(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"💎 Купить за {PREMIUM_PRICE_STARS} ⭐",
                             callback_data="buy_premium")
    ]])
    await m.answer(
        f"💎 <b>Премиум</b>\n\n• Безлимит действий\n• Приоритет\n\n"
        f"Цена: {PREMIUM_PRICE_STARS} ⭐ / 30 дней",
        reply_markup=kb, parse_mode=ParseMode.HTML)


@router.message(Command("buy"))
async def buy(m: Message):
    await g.bot.send_invoice(
        chat_id=m.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium")


@router.callback_query(F.data == "buy_premium")
async def buy_premium_cb(c: CallbackQuery):
    await g.bot.send_invoice(
        chat_id=c.message.chat.id, title="Премиум-подписка",
        description="Безлимитные действия", payload="premium_30d",
        provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium")
    await c.answer()


@router.pre_checkout_query()
async def pre_checkout(q):
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def on_payment(m: Message):
    await g.db.set_premium(m.from_user.id, 1)
    await m.answer("💎 <b>Оплата получена!</b>", reply_markup=main_kb(),
                   parse_mode=ParseMode.HTML)
