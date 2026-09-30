"""Премиум-магазин: подписки, расы, классы, эксклюзивы за Stars."""
import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.premium import (
    SUBSCRIPTIONS, EXCLUSIVE_RACES, EXCLUSIVE_CLASSES,
    EXCLUSIVE_ITEMS, EXCLUSIVE_PETS, COSMETICS, CONSUMABLES, BUNDLES,
)

router = Router()

# 100 лет в часах — для "навсегда"
FOREVER_HOURS = 24 * 365 * 100


def _format_until(pu):
    if not pu:
        return None
    try:
        if hasattr(pu, "year"):
            if pu.year >= 2099:
                return "∞ навсегда"
            return pu.strftime("%d.%m.%Y %H:%M")
    except Exception:
        pass
    return None


async def _show_main_menu(chat_id, u):
    until = _format_until(u.get("premium_until"))
    is_prem = bool(u.get("is_premium"))

    text = "💎 <b>Премиум-магазин</b>\n\n"
    if is_prem and until:
        text += f"⭐ Твой премиум: до <b>{until}</b>\n\n"
    else:
        text += "⭐ Премиум не активен\n\n"
    text += "<b>Категории:</b>"

    rows = [
        [InlineKeyboardButton(text="⚡ Подписки", callback_data="prem_cat_subs")],
        [InlineKeyboardButton(text="🎭 Эксклюзивные расы", callback_data="prem_cat_races")],
        [InlineKeyboardButton(text="🛡 Класс Хранитель", callback_data="prem_cat_class")],
        [InlineKeyboardButton(text="⚔️ Эксклюзивная экипировка", callback_data="prem_cat_items")],
        [InlineKeyboardButton(text="🐉 Эксклюзивные питомцы", callback_data="prem_cat_pets")],
        [InlineKeyboardButton(text="🧪 Расходники", callback_data="prem_cat_consum")],
        [InlineKeyboardButton(text="✨ Косметика", callback_data="prem_cat_cosmetics")],
        [InlineKeyboardButton(text="📦 Наборы (выгода)", callback_data="prem_cat_bundles")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="prem_close")],
    ]
    await g.bot.send_message(chat_id, text,
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                             parse_mode=ParseMode.HTML)


@router.message(Command("premium"))
@router.message(F.text == "💎 Премиум")
async def premium_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    await _show_main_menu(m.chat.id, u)


@router.callback_query(F.data == "prem_close")
async def prem_close(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data == "prem_back")
async def prem_back(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    try:
        await c.message.delete()
    except Exception:
        pass
    await _show_main_menu(c.message.chat.id, u)
    await c.answer()


# ================= ПОДПИСКИ =================
@router.callback_query(F.data == "prem_cat_subs")
async def prem_subs(c: CallbackQuery):
    text = "⚡ <b>Подписки</b>\n\n<b>Что даёт премиум:</b>\n"
    text += "• Безлимит энергии\n• ×2 регенерация\n• Скидка 10% (с месячного)\n\n"
    text += "<b>Выбери тариф:</b>"
    rows = []
    for code, tier in SUBSCRIPTIONS.items():
        rows.append([InlineKeyboardButton(
            text=f"{tier['name']} — {tier['price']}⭐",
            callback_data=f"prem_tier_{code}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_tier_"))
async def prem_tier(c: CallbackQuery):
    code = c.data.replace("prem_tier_", "")
    tier = SUBSCRIPTIONS.get(code)
    if not tier:
        await c.answer("Тариф не найден"); return

    text = (f"<b>{tier['name']}</b>\n\n"
            f"{tier['desc']}\n\n"
            f"Цена: <b>{tier['price']} ⭐</b>")
    rows = [
        [InlineKeyboardButton(
            text=f"💎 Купить за {tier['price']} ⭐",
            callback_data=f"prem_buy_{code}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_cat_subs")],
    ]
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_buy_"))
async def prem_buy(c: CallbackQuery):
    code = c.data.replace("prem_buy_", "")
    tier = SUBSCRIPTIONS.get(code)
    if not tier:
        await c.answer("Тариф не найден"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=tier["name"],
        description=tier["desc"],
        payload=f"premium_tier:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=tier["name"], amount=tier["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= РАСЫ =================
@router.callback_query(F.data == "prem_cat_races")
async def prem_races(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    try:
        owned = set(json.loads(u.get("unlocked_premium_races") or "[]"))
    except Exception:
        owned = set()

    text = "🎭 <b>Эксклюзивные расы</b>\n\nРазблокируются <b>навсегда</b>.\n\n"
    rows = []
    for code, race in EXCLUSIVE_RACES.items():
        if code in owned:
            text += f"✅ {race['name']} — <i>куплено</i>\n   {race['desc']}\n\n"
        else:
            text += f"🔒 {race['name']} — {race['price']}⭐\n   {race['desc']}\n\n"
            rows.append([InlineKeyboardButton(
                text=f"Купить {race['name']} — {race['price']}⭐",
                callback_data=f"prem_race_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_race_buy_"))
async def prem_race_buy(c: CallbackQuery):
    code = c.data.replace("prem_race_buy_", "")
    race = EXCLUSIVE_RACES.get(code)
    if not race:
        await c.answer("Раса не найдена"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=f"Раса: {race['name']}",
        description=race["desc"],
        payload=f"premium_race:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=race["name"], amount=race["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= КЛАСС =================
@router.callback_query(F.data == "prem_cat_class")
async def prem_class(c: CallbackQuery):
    text = "🛡 <b>Эксклюзивные классы</b>\n\nРазблокируются навсегда.\n\n"
    rows = []
    for code, cl in EXCLUSIVE_CLASSES.items():
        text += f"🔒 {cl['name']} — {cl['price']}⭐\n   {cl['desc']}\n\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {cl['name']} — {cl['price']}⭐",
            callback_data=f"prem_class_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_class_buy_"))
async def prem_class_buy(c: CallbackQuery):
    code = c.data.replace("prem_class_buy_", "")
    cl = EXCLUSIVE_CLASSES.get(code)
    if not cl:
        await c.answer("Класс не найден"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=f"Класс: {cl['name']}",
        description=cl["desc"],
        payload=f"premium_class:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=cl["name"], amount=cl["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= ЭКИПИРОВКА =================
@router.callback_query(F.data == "prem_cat_items")
async def prem_items(c: CallbackQuery):
    text = "⚔️ <b>Эксклюзивная экипировка</b>\n\nТолько за Stars, нигде больше не получить.\n\n"
    rows = []
    for code, item in EXCLUSIVE_ITEMS.items():
        text += f"🔒 <b>{code}</b> — {item['price']}⭐\n"
        bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in item["bonus"].items())
        text += f"   {bonus_str} · {item.get('extra', '')}\n\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {code} — {item['price']}⭐",
            callback_data=f"prem_item_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_item_buy_"))
async def prem_item_buy(c: CallbackQuery):
    code = c.data.replace("prem_item_buy_", "")
    item = EXCLUSIVE_ITEMS.get(code)
    if not item:
        await c.answer("Не найдено"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=code,
        description=item.get("extra", "") or "Эксклюзивный предмет",
        payload=f"premium_item:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=code, amount=item["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= ПИТОМЦЫ =================
@router.callback_query(F.data == "prem_cat_pets")
async def prem_pets(c: CallbackQuery):
    text = "🐉 <b>Эксклюзивные питомцы</b>\n\n"
    rows = []
    for code, pet in EXCLUSIVE_PETS.items():
        text += f"🔒 {pet['name']} — {pet['price']}⭐\n   {pet['desc']}\n\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {pet['name']} — {pet['price']}⭐",
            callback_data=f"prem_pet_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_pet_buy_"))
async def prem_pet_buy(c: CallbackQuery):
    code = c.data.replace("prem_pet_buy_", "")
    pet = EXCLUSIVE_PETS.get(code)
    if not pet:
        await c.answer("Не найдено"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=pet["name"],
        description=pet["desc"],
        payload=f"premium_pet:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=pet["name"], amount=pet["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= РАСХОДНИКИ =================
@router.callback_query(F.data == "prem_cat_consum")
async def prem_consum(c: CallbackQuery):
    text = "🧪 <b>Расходники</b>\n\n"
    rows = []
    for code, con in CONSUMABLES.items():
        text += f"🔒 {con['name']} — {con['price']}⭐\n   {con['desc']}\n\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {con['name']} — {con['price']}⭐",
            callback_data=f"prem_consum_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_consum_buy_"))
async def prem_consum_buy(c: CallbackQuery):
    code = c.data.replace("prem_consum_buy_", "")
    con = CONSUMABLES.get(code)
    if not con:
        await c.answer("Не найдено"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=con["name"],
        description=con["desc"],
        payload=f"premium_consum:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=con["name"], amount=con["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= КОСМЕТИКА =================
@router.callback_query(F.data == "prem_cat_cosmetics")
async def prem_cosmetics(c: CallbackQuery):
    text = "✨ <b>Косметика</b>\n\n"
    rows = []
    for code, cos in COSMETICS.items():
        text += f"🔒 {cos['name']} — {cos['price']}⭐\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {cos['name']} — {cos['price']}⭐",
            callback_data=f"prem_cosm_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_cosm_buy_"))
async def prem_cosm_buy(c: CallbackQuery):
    code = c.data.replace("prem_cosm_buy_", "")
    cos = COSMETICS.get(code)
    if not cos:
        await c.answer("Не найдено"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=cos["name"],
        description="Косметика",
        payload=f"premium_cosm:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=cos["name"], amount=cos["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= НАБОРЫ =================
@router.callback_query(F.data == "prem_cat_bundles")
async def prem_bundles(c: CallbackQuery):
    text = "📦 <b>Наборы</b>\n\nСо скидкой.\n\n"
    rows = []
    for code, b in BUNDLES.items():
        text += f"🔒 {b['name']} — {b['price']}⭐ (экономия {b['save']}⭐)\n"
        rows.append([InlineKeyboardButton(
            text=f"Купить {b['name']} — {b['price']}⭐",
            callback_data=f"prem_bundle_buy_{code}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prem_back")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("prem_bundle_buy_"))
async def prem_bundle_buy(c: CallbackQuery):
    code = c.data.replace("prem_bundle_buy_", "")
    b = BUNDLES.get(code)
    if not b:
        await c.answer("Не найдено"); return
    await g.bot.send_invoice(
        chat_id=c.message.chat.id,
        title=b["name"],
        description=f"Набор со скидкой {b['save']}⭐",
        payload=f"premium_bundle:{code}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=b["name"], amount=b["price"])],
        start_parameter="premium",
    )
    await c.answer()


# ================= ОПЛАТА =================
@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def on_payment(m: Message):
    payload = m.successful_payment.invoice_payload

    # --- Подписки ---
    if payload.startswith("premium_tier:"):
        code = payload.split(":", 1)[1]
        tier = SUBSCRIPTIONS.get(code)
        if tier:
            dur = tier["duration_hours"]
            if dur == -1:
                dur = FOREVER_HOURS  # вечный
            await g.db.set_premium_tier(m.from_user.id, code, dur)
            if code == "forever":
                for r in EXCLUSIVE_RACES:
                    await g.db.unlock_premium_race(m.from_user.id, r)
            await m.answer(
                f"💎 <b>Премиум активирован!</b>\n\n{tier['name']} — оплачено.",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Расы ---
    if payload.startswith("premium_race:"):
        code = payload.split(":", 1)[1]
        race = EXCLUSIVE_RACES.get(code)
        if race:
            await g.db.unlock_premium_race(m.from_user.id, code)
            await m.answer(
                f"🎭 <b>Раса открыта!</b>\n\n{race['name']} доступна в /newchar.",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Класс ---
    if payload.startswith("premium_class:"):
        code = payload.split(":", 1)[1]
        cl = EXCLUSIVE_CLASSES.get(code)
        if cl:
            await g.db.unlock_premium_class(m.from_user.id, code)
            await m.answer(
                f"🛡 <b>Класс открыт!</b>\n\n{cl['name']} доступен в /newchar.",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Экипировка ---
    if payload.startswith("premium_item:"):
        code = payload.split(":", 1)[1]
        item = EXCLUSIVE_ITEMS.get(code)
        if item:
            await g.db.add_item(m.from_user.id, code)
            await m.answer(
                f"⚔️ <b>Предмет получен!</b>\n\n{code} → /inventory",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Питомец ---
    if payload.startswith("premium_pet:"):
        code = payload.split(":", 1)[1]
        pet = EXCLUSIVE_PETS.get(code)
        if pet:
            await g.db.add_pet(m.from_user.id, code, pet["name"])
            await m.answer(
                f"🐉 <b>Питомец получен!</b>\n\n{pet['name']} → /pet",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Расходники ---
    if payload.startswith("premium_consum:"):
        code = payload.split(":", 1)[1]
        con = CONSUMABLES.get(code)
        if con:
            if code == "xp_scroll":
                await g.db.add_xp(m.from_user.id, 500)
                await m.answer(f"📜 <b>+500 XP!</b>", reply_markup=main_kb(),
                               parse_mode=ParseMode.HTML)
            elif code == "treasure":
                from core.game_data import DROP_TABLE
                import random
                item = random.choice(DROP_TABLE)
                await g.db.add_item(m.from_user.id, item)
                await m.answer(f"🎁 <b>Получено:</b> {item}", reply_markup=main_kb(),
                               parse_mode=ParseMode.HTML)
            else:
                await g.db.add_item(m.from_user.id, con["name"])
                await m.answer(f"✅ <b>{con['name']}</b> добавлен в /inventory",
                               reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Косметика ---
    if payload.startswith("premium_cosm:"):
        code = payload.split(":", 1)[1]
        cos = COSMETICS.get(code)
        if cos:
            await g.db.unlock_cosmetic(m.from_user.id, code)
            await m.answer(
                f"✨ <b>Косметика активирована!</b>\n\n{cos['name']}",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    # --- Наборы ---
    if payload.startswith("premium_bundle:"):
        code = payload.split(":", 1)[1]
        b = BUNDLES.get(code)
        if b:
            # Простая логика: выдаём содержимое
            # Детально — во второй итерации
            await m.answer(
                f"📦 <b>Набор получен!</b>\n\n{b['name']} → проверь /inventory",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
            return

    await m.answer("✅ Оплата получена.", reply_markup=main_kb())
