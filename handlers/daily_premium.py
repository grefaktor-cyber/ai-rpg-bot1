"""Ежедневная награда. Inline back+close. + ИИ-сон от GigaChat."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb

router = Router()


def _daily_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_progress"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"),
    ]])


# ================= ИИ-СОН =================
_DREAM_FALLBACKS = [
    "Ты видел бескрайнюю равнину и одинокое дерево на горизонте.",
    "Тебе снился старый друг, которого ты не помнишь.",
    "Приснился дракон, кружащий над замком. Он не был враждебен.",
    "Ты шёл по улицам древнего города, которого нет на карте.",
    "Во сне ты сражался с собственной тенью и не мог победить.",
    "Ты стоял у чёрной воды и слышал шёпот из глубины.",
    "Приснилась битва, где ты был одновременно воином и оружием.",
    "Ты видел себя ребёнком на месте, которое давно разрушено.",
]


async def _generate_dream(user):
    """Короткий сон 2-3 предложения. Через GigaChat или fallback."""
    race = user.get("race", "human")
    cls = user.get("class", "warrior")
    level = user.get("level", 1)
    location = user.get("location_code", "village")

    try:
        from ai import giga_chat
    except Exception as e:
        import logging
        logging.warning(f"[DREAM] ai.giga_chat not available: {e}")
        return random.choice(_DREAM_FALLBACKS)

    prompt = (
        f"Ты — рассказчик в тёмном фэнтези. Герой — {race} {cls} "
        f"{level} уровня, сейчас в локации {location}. "
        f"Опиши его короткий сон — 2-3 предложения. "
        f"Стиль: загадочный, атмосферный, лёгкая тревога. "
        f"Без приветствий, без пояснений, только текст сна."
    )

    try:
        resp = await giga_chat(prompt)
        if not resp or len(resp) < 10:
            return random.choice(_DREAM_FALLBACKS)
        # Обрезаем до 400 символов
        text = resp.strip()[:400]
        # Срезаем кавычки если ИИ их поставил
        text = text.strip('"').strip("«»").strip()
        return text
    except Exception as e:
        import logging
        logging.warning(f"[DREAM] GigaChat error: {e}")
        return random.choice(_DREAM_FALLBACKS)


@router.message(Command("daily"))
@router.message(F.text == "🎁 Награда")
async def daily(m: Message):
    streak = await g.db.claim_daily(m.from_user.id)
    if streak is None:
        await m.answer(
            "🎁 Уже получал сегодня.\n\n"
            "Возвращайся завтра!",
            reply_markup=_daily_kb(), parse_mode=ParseMode.HTML)
        return
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

    # 🛏 ИИ-сон
    try:
        dream_text = await _generate_dream(u)
        if dream_text:
            msg += f"\n\n💤 <b>Ночной сон:</b>\n<i>{dream_text}</i>"
    except Exception as e:
        import logging
        logging.error(f"[DREAM] {e}", exc_info=True)

    await m.answer(msg, reply_markup=_daily_kb(), parse_mode=ParseMode.HTML)
