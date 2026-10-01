"""Магазин: категории, покупка с проверками."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.equipment import (
    SHOP, SLOTS, SLOT_NAMES, can_use_item, get_armor_type,
)
from core.formulas import faction_mult, calc_max_hp, calc_max_mp, parse_item
from core.keyboards import main_kb

router = Router()


def _grade_icon(grade):
    return {"common": "⚪", "D": "🔷", "C": "🔶", "B": "💎"}.get(grade, "⚪")


CATEGORIES = {
    "weapon":    ("🗡 Оружие", "🗡"),
    "armor":     ("🛡 Броня", "🛡"),
    "shield":    ("🛡 Щиты", "🛡"),
    "accessory": ("💍 Аксессуары", "💍"),
    "potion":    ("🧪 Зелья", "🧪"),
}


def _get_items(user_class, player_level, shop_mult, category):
    groups = {"common": [], "D": [], "C": [], "B": []}
    for name, data in SHOP.items():
        if category == "accessory" and data["type"] != "accessory":
            continue
        if category == "shield" and data["type"] != "shield":
            continue
        if category not in ("accessory", "shield") and data["type"] != category:
            continue
        if data["type"] != "potion":
            if not can_use_item(user_class, name):
                continue
        if player_level < data.get("level_req", 1):
            continue
        if data.get("premium"):
            continue
        price = int(data["price"] * shop_mult)
        grade = data.get("grade", "common")
        groups[grade].append((name, data, price))
    return groups


@router.message(Command("shop"))
@router.message(F.text == "🛒 Магазин")
async def shop(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    shop_mult = faction_mult(u, "shop_mult")
    armor_type = get_armor_type(u["class"])
    armor_names = {"heavy": "Тяжёлая", "light": "Лёгкая", "robe": "Мантия"}

    text = (f"🛒 <b>Магазин</b>\n\n"
            f"💰 Золото: <b>{u['gold']}</b>\n"
            f"🎭 Класс: <b>{u['class']}</b> ({armor_names.get(armor_type, '?')})\n"
            f"⭐ Уровень: <b>{u['level']}</b>\n")
    if shop_mult < 1:
        text += f"🏷 Скидка фракции: <b>−{int((1-shop_mult)*100)}%</b>\n"
    counts = {}
    for cat in CATEGORIES:
        g_ = _get_items(u["class"], u["level"], shop_mult, cat)
        counts[cat] = sum(len(v) for v in g_.values())
    text += "\n<b>Категории:</b>\n"
    for cat, (label, icon) in CATEGORIES.items():
        cnt = counts[cat]
        if cnt > 0:
            text += f"• {label} — <b>{cnt}</b>\n"
        else:
            text += f"• {label} — <i>нет</i>\n"
    text += "\n⚪ Обычный · 🔷 D (15+) · 🔶 C (30+) · 💎 B (45+)"

    rows = []
    for cat, (label, icon) in CATEGORIES.items():
        rows.append([InlineKeyboardButton(
            text=f"{label} ({counts[cat]})",
            callback_data=f"shop_cat_{cat}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="shop_close")])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "shop_menu")
async def shop_menu_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    shop_mult = faction_mult(u, "shop_mult")
    armor_type = get_armor_type(u["class"])
    armor_names = {"heavy": "Тяжёлая", "light": "Лёгкая", "robe": "Мантия"}
    text = (f"🛒 <b>Магазин</b>\n\n"
            f"💰 Золото: <b>{u['gold']}</b>\n"
            f"🎭 Класс: <b>{u['class']}</b> ({armor_names.get(armor_type, '?')})\n"
            f"⭐ Уровень: <b>{u['level']}</b>\n")
    counts = {}
    for cat in CATEGORIES:
        g_ = _get_items(u["class"], u["level"], shop_mult, cat)
        counts[cat] = sum(len(v) for v in g_.values())
    text += "\n<b>Категории:</b>\n"
    for cat, (label, icon) in CATEGORIES.items():
        text += f"• {label} — <b>{counts[cat]}</b>\n"
    text += "\n⚪ Обычный · 🔷 D (15+) · 🔶 C (30+) · 💎 B (45+)"
    rows = []
    for cat, (label, icon) in CATEGORIES.items():
        rows.append([InlineKeyboardButton(
            text=f"{label} ({counts[cat]})", callback_data=f"shop_cat_{cat}")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="shop_close")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("shop_cat_"))
async def shop_category(c: CallbackQuery):
    cat = c.data.replace("shop_cat_", "")
    if cat not in CATEGORIES:
        await c.answer("Нет"); return
    u = await g.db.get_user(c.from_user.id)
    shop_mult = faction_mult(u, "shop_mult")
    groups = _get_items(u["class"], u["level"], shop_mult, cat)
    label, _ = CATEGORIES[cat]
    text = f"{label}\n\n💰 Золото: <b>{u['gold']}</b>\n\n"
    rows = []
    has_items = False
    for grade in ("common", "D", "C", "B"):
        items = groups[grade]
        if not items:
            continue
        has_items = True
        grade_label = {"common": "Обычный", "D": "D-грейд",
                       "C": "C-грейд", "B": "B-грейд"}[grade]
        text += f"<b>{grade_label}:</b>\n"
        for name, data, price in items:
            g_icon = _grade_icon(grade)
            if data["type"] == "potion":
                hp = data.get("heal_hp", 0)
                mp = data.get("heal_mp", 0)
                eff = f"+{hp} HP" if hp else f"+{mp} MP"
                text += f"{g_icon} {name} — {price}💰 ({eff})\n"
            else:
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                text += f"{g_icon} {name} — {price}💰 ({bonus_str})\n"
            rows.append([InlineKeyboardButton(
                text=f"Купить {name} — {price}💰",
                callback_data=f"shop_buy_{name}")])
        text += "\n"
    if not has_items:
        text += "<i>Нет доступных предметов.</i>"
        if u["level"] < 15:
            text += "\n\n💡 D-грейд с 15 уровня."
        elif u["level"] < 30:
            text += "\n\n💡 C-грейд с 30 уровня."
        elif u["level"] < 45:
            text += "\n\n💡 B-грейд с 45 уровня."
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_menu")])
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "shop_close")
async def shop_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery):
    item_name = c.data.replace("shop_buy_", "", 1)
    if item_name not in SHOP:
        await c.answer("Не найдено"); return
    data = SHOP[item_name]
    user = await g.db.get_user(c.from_user.id)
    if not user["char_name"]:
        await c.answer("Сначала создай героя"); return
    if data.get("premium"):
        await c.answer("Эксклюзив — только за Stars", show_alert=True); return
    if data["type"] != "potion":
        if not can_use_item(user["class"], item_name):
            await c.answer("❌ Класс не может использовать", show_alert=True); return
    if user["level"] < data.get("level_req", 1):
        await c.answer(f"❌ Нужен {data['level_req']} уровень", show_alert=True); return
    price = int(data["price"] * faction_mult(user, "shop_mult"))
    ok = await g.db.spend_gold(c.from_user.id, price)
    if not ok:
        await c.answer(f"❌ Нужно {price}💰 (у тебя {user['gold']})", show_alert=True)
        return
    await g.db.add_item(c.from_user.id, item_name)
    await c.answer(f"✅ −{price}💰")
    u2 = await g.db.get_user(c.from_user.id)
    hint = f"/use {item_name}" if data["type"] == "potion" else f"/equip {item_name}"
    await c.message.answer(
        f"✅ <b>{item_name}</b> куплен (−{price}💰)\n"
        f"Осталось: {u2['gold']}💰\n{hint}",
        parse_mode=ParseMode.HTML)


# ================= ЭКИПИРОВКА =================
@router.message(Command("equip"))
async def equip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /equip Название"); return
    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    from core.fuzzy import find_inventory_item
    exact, sugg = find_inventory_item(parts[1].strip(), inv_names)
    if exact:
        await _do_equip(m.from_user.id, exact, m); return
    if sugg:
        rows = [[InlineKeyboardButton(
            text=f"⚔️ Надеть {s}",
            callback_data=f"equip_item_{s}")] for s in sugg[:10]]
        rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="fuzzy_cancel")])
        await m.answer("🔍 Нашёл несколько:",
                       reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return
    await m.answer(f"❌ Не нашёл «{parts[1]}».")


@router.callback_query(F.data.startswith("equip_item_"))
async def equip_item_cb(c: CallbackQuery):
    item_name = c.data.replace("equip_item_", "", 1)
    await _do_equip(c.from_user.id, item_name, c.message, cb=c)


async def _do_equip(uid, item_name, message, cb=None):
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        msg = "❌ Нельзя экипировать."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    data = SHOP[base_name]
    if data["type"] == "potion":
        msg = "❌ Не экипируется."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    user = await g.db.get_user(uid)
    if not can_use_item(user["class"], base_name):
        msg = "❌ Класс не может носить."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    if user["level"] < data.get("level_req", 1):
        msg = f"❌ Нужен {data['level_req']} уровень."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    inv = await g.db.get_inventory(uid)
    if not any(i["item_name"] == item_name for i in inv):
        msg = "❌ Нет в инвентаре."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    slot = data["slot"]
    old = await g.db.equip_item(uid, slot, item_name)
    await g.db.remove_item(uid, item_name)
    if old:
        await g.db.add_item(uid, old)
    u = await g.db.get_user(uid)
    new_max_hp = calc_max_hp(u)
    new_max_mp = calc_max_mp(u)
    await g.db.update_hp_max(uid, min(u["hp"], new_max_hp), new_max_hp)
    await g.db.update_mp(uid, min(u.get("mp", 0), new_max_mp))
    txt = f"⚔️ Экипировано: <b>{item_name}</b>"
    if old:
        txt += f"\nСнято: {old}"
    if cb:
        await cb.answer("✅ Экипировано")
        await message.answer(txt, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(txt, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(uid, "equipped"):
        await message.answer("🏆 Достижение: ⚔️ Снаряжён", parse_mode=ParseMode.HTML)


@router.message(Command("unequip"))
async def unequip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer(f"Слоты: {', '.join(SLOTS)}"); return
    slot = parts[1].strip().lower()
    if slot not in SLOTS:
        await m.answer(f"Слоты: {', '.join(SLOTS)}"); return
    item = await g.db.unequip_item(m.from_user.id, slot)
    if item:
        await g.db.add_item(m.from_user.id, item)
        await m.answer(f"✅ Снято: {item}", reply_markup=main_kb())
    else:
        await m.answer("Слот пуст.", reply_markup=main_kb())
    u = await g.db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    await g.db.update_hp_max(m.from_user.id, min(u["hp"], new_max), new_max)
