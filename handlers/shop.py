"""Магазин, инвентарь, экипировка (7 слотов)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.equipment import (
    SLOT_NAMES, SLOTS, get_armor_type, can_use_item,
)
from core.formulas import (
    faction_mult, calc_max_hp, calc_max_mp, parse_item,
)
from core.keyboards import main_kb

router = Router()


# ================= МАГАЗИН =================
@router.message(Command("shop"))
@router.message(F.text == "🛒 Магазин")
async def shop(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    shop_mult = faction_mult(u, "shop_mult")
    armor_type = get_armor_type(u["class"])
    armor_names = {"heavy": "Тяжёлая", "light": "Лёгкая", "robe": "Мантия"}

    text = f"🛒 <b>Магазин</b>\n\n💰 Золото: <b>{u['gold']}</b>"
    if shop_mult < 1:
        text += f" (−{int((1-shop_mult)*100)}% фракция)"
    text += f"\n🎭 Твой класс: <b>{u['class']}</b> ({armor_names.get(armor_type, '?')} броня)\n\n"

    categories = [
        ("weapon", "🗡 Оружие"),
        ("armor", "🛡 Броня"),
        ("shield", "🛡 Щиты"),
        ("accessory", "💍 Аксессуары"),
        ("potion", "🧪 Зелья"),
    ]

    buttons = []
    for cat_type, label in categories:
        cat_items = []
        for name, data in SHOP.items():
            # Фильтр по типу категории
            if cat_type == "accessory":
                if data["type"] not in ("accessory",):
                    continue
            elif cat_type == "shield":
                if data["type"] != "shield":
                    continue
            else:
                if data["type"] != cat_type:
                    continue

            # Проверка доступа
            if data["type"] == "potion":
                can_use = True
            else:
                can_use = can_use_item(u["class"], name)
            if not can_use:
                continue
            level_ok = u["level"] >= data.get("level_req", 1)
            if not level_ok:
                continue

            price = int(data["price"] * shop_mult)
            cat_items.append((name, data, price))

        if not cat_items:
            continue

        text += f"<b>{label}:</b>\n"
        for name, data, price in cat_items:
            grade = data.get("grade", "common")
            g_icon = {"common": "•", "D": "🔷", "C": "🔶"}.get(grade, "•")
            if data["type"] == "potion":
                hp = data.get("heal_hp", 0)
                mp = data.get("heal_mp", 0)
                eff = f"+{hp} HP" if hp else f"+{mp} MP"
                text += f"{g_icon} {name} — {price}💰 ({eff})\n"
            else:
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                text += f"{g_icon} {name} [{grade}] — {price}💰 ({bonus_str})\n"
            buttons.append([InlineKeyboardButton(
                text=f"{name} — {price}💰",
                callback_data=f"shop_buy_{name}")]
            )
        text += "\n"

    if not buttons:
        text += "<i>Нет доступных предметов для твоего класса.</i>"

    text += "🔷 = D-грейд · 🔶 = C-грейд"
    rows = buttons + [[InlineKeyboardButton(text="❌ Закрыть", callback_data="shop_close")]]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


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

    # Проверки
    if data["type"] != "potion":
        if not can_use_item(user["class"], item_name):
            await c.answer("❌ Твой класс не может это использовать", show_alert=True)
            return
    if user["level"] < data.get("level_req", 1):
        await c.answer(f"❌ Нужен {data['level_req']} уровень", show_alert=True)
        return

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
    item_name = parts[1].strip()
    await _do_equip(m.from_user.id, item_name, m)


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
    if data["type"] in ("potion",):
        msg = "❌ Не экипируется."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return

    user = await g.db.get_user(uid)
    # Проверка класса
    if not can_use_item(user["class"], base_name):
        msg = "❌ Твой класс не может носить это."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    # Проверка уровня
    if user["level"] < data.get("level_req", 1):
        msg = f"❌ Нужен {data['level_req']} уровень."
        await (cb.answer(msg, show_alert=True) if cb else message.answer(msg))
        return
    # Проверка инвентаря
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

    # Пересчёт HP/MP
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
        await m.answer("Использование: /unequip weapon|helmet|armor|boots|shield|accessory|ring")
        return
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


# ================= ИНВЕНТАРЬ =================
@router.message(Command("inventory"))
@router.message(F.text == "🎒 Инвентарь")
async def inventory(m: Message):
    u = await g.db.get_user(m.from_user.id)
    items = await g.db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=main_kb()); return

    lines = ["🎒 <b>Инвентарь</b>\n"]
    rows = []
    for it in items:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP:
            data = SHOP[name]
            grade = data.get("grade", "common")
            g_icon = {"common": "", "D": "🔷", "C": "🔶"}.get(grade, "")
            if data["type"] == "potion":
                hp = data.get("heal_hp", 0)
                mp = data.get("heal_mp", 0)
                eff = f"+{hp} HP" if hp else f"+{mp} MP"
                lines.append(f"• 🧪 {name} — {eff}")
                rows.append([InlineKeyboardButton(
                    text=f"🧪 {name}", callback_data=f"use_item_{name}")])
            else:
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                suffix = f" (+{lvl})" if lvl else ""
                lines.append(f"• {g_icon} {name}{suffix} — {bonus_str}")
                # Доступен классу?
                if can_use_item(u["class"], name):
                    rows.append([
                        InlineKeyboardButton(text=f"⚔️ Надеть {name[:12]}",
                                             callback_data=f"equip_item_{it['item_name']}"),
                        InlineKeyboardButton(text="💰",
                                             callback_data=f"sell_item_{it['item_name']}"),
                    ])
                else:
                    rows.append([
                        InlineKeyboardButton(text=f"❌ {name[:12]} (не твой класс)",
                                             callback_data="inv_noop"),
                        InlineKeyboardButton(text="💰",
                                             callback_data=f"sell_item_{it['item_name']}"),
                    ])
        else:
            lines.append(f"• {it['item_name']}")

    # Экипировано
    lines.append("\n<b>Экипировано:</b>")
    for slot in SLOTS:
        val = u.get(f"equipped_{slot}") or "—"
        lines.append(f"{SLOT_NAMES[slot]}: {val}")

    # Сетовый бонус?
    from core.equipment import get_set_bonus
    set_b = get_set_bonus(u)
    if set_b:
        lines.append(f"\n🎁 <b>Сетовый бонус:</b> {set_b['desc']}")

    lines.append("\n<i>/equip · /use · /sell · /drop</i>")

    rows.append([InlineKeyboardButton(text="❌ Закрыть",
                                      callback_data="inv_close")])
    await m.answer("\n".join(lines),
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "inv_noop")
async def inv_noop(c: CallbackQuery):
    await c.answer("Твой класс не может это носить", show_alert=True)


@router.callback_query(F.data == "inv_close")
async def inv_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
