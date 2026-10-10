"""Ежедневная награда. Inline back+close. + ИИ-сон через ai.generate()."""
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
    """Короткий сон 2-3 предложения через GigaChat.

    Использует ai.generate() с пустой историей и специальной командой.
    """
    try:
        from ai import generate
    except Exception as e:
        import logging
        logging.warning(f"[DREAM] ai.generate not available: {e}")
        return random.choice(_DREAM_FALLBACKS)

    # Промпт-команда — акцент на сновидении
    action = (
        "опиши короткий сон моего героя (2-3 предложения). "
        "Стиль: загадочный, атмосферный, тёмное фэнтези. "
        "Без предметов, без боёв, без тегов. "
        "Только описание сна."
    )

    try:
        result = await generate(
            story="",
            user_action=action,
            arc=1,
            user=user,
            event=None,
            location_owner=None,
        )
        text = (result or {}).get("text", "")
        if not text or len(text) < 15:
            return random.choice(_DREAM_FALLBACKS)

        # Срезаем префиксы вида "Мастер:" если ИИ их добавил
        text = text.strip()
        for prefix in ("Мастер:", "Мастер :", "Сон:", "Сновидение:"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # Обрезка до 400 символов
        text = text[:400].strip()
        # Срезаем кавычки
        text = text.strip('"').strip("«»").strip()
        return text if text else random.choice(_DREAM_FALLBACKS)
    except Exception as e:
        import logging
        logging.warning(f"[DREAM] generate error: {e}")
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

    msg = (f"🎁 <b>Награда!</b>\n\n"
           f"📅 День <b>{streak}</b>\n"
           f"💰 +{gold_bonus} золота\n"
           f"🔩 +1 железо\n"
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
