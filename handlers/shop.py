"""Магазин, инвентарь, экипировка."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.formulas import faction_mult, calc_max_hp, parse_item
from core.keyboards import main_kb, shop_kb
from config import ADMIN_IDS


router = Router()


# ================= МАГАЗИН =================
@router.message(Command("shop"))
@router.message(F.text == "🛒 Магазин")
async def shop(m: Message):
    u = await g.db.get_user(m.from_user.id)
    shop_mult = faction_mult(u, "shop_mult")
    text = f"🛒 <b>Магазин</b>\n\n💰 Золото: <b>{u['gold']}</b>"
    if shop_mult < 1:
        text += f" (−{int((1-shop_mult)*100)}% фракция)"
    text += "\n\n"
    for category, label in [("weapon", "🗡 Оружие"), ("armor", "🛡 Броня"),
                            ("accessory", "💍 Аксессуары"), ("potion", "🧪 Зелья")]:
        text += f"<b>{label}:</b>\n"
        for name, data in SHOP.items():
            if data["type"] != category:
                continue
            price = int(data["price"] * shop_mult)
            if category == "potion":
                hp = data.get("heal_hp", 0)
                mp = data.get("heal_mp", 0)
                effect = f"+{hp} HP" if hp else f"+{mp} MP"
                text += f"• {name} ({price}💰) — {effect}\n"
            else:
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                text += f"• {name} ({price}💰) — {bonus_str}\n"
        text += "\n"
    # Кнопки
    rows = []
    for name, data in SHOP.items():
        price = int(data["price"] * shop_mult)
        rows.append([InlineKeyboardButton(
            text=f"{name} — {price}💰",
            callback_data=f"shop_buy_{name}"
        )])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery):
    item_name = c.data.replace("shop_buy_", "")
    if item_name not in SHOP:
        await c.answer("Не найдено"); return
    data = SHOP[item_name]
    user = await g.db.get_user(c.from_user.id)
    price = int(data["price"] * faction_mult(user, "shop_mult"))
    is_admin = c.from_user.id in ADMIN_IDS
    if not is_admin:
        ok = await g.db.spend_gold(c.from_user.id, price)
        if not ok:
            await c.answer(f"❌ Нужно {price}💰", show_alert=True); return
    await g.db.add_item(c.from_user.id, item_name)
    await c.answer(f"✅ Куплено: {item_name}")
    if data["type"] == "potion":
        await c.message.answer(
            f"✅ <b>{item_name}</b> куплен!\nИспользуй: /use {item_name}",
            parse_mode=ParseMode.HTML)
    else:
        await c.message.answer(
            f"✅ <b>{item_name}</b> куплен!\n/equip {item_name}",
            parse_mode=ParseMode.HTML)


# ================= ЭКИПИРОВКА =================
@router.message(Command("equip"))
async def equip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /equip Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя экипировать."); return
    if SHOP[base_name]["type"] == "potion":
        await m.answer("❌ Зелья не экипируются. /use Название"); return
    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    if item_name not in inv_names:
        await m.answer("❌ Нет в инвентаре."); return
    slot = SHOP[base_name]["type"]
    old = await g.db.equip_item(m.from_user.id, slot, item_name)
    await g.db.remove_item(m.from_user.id, item_name)
    if old:
        await g.db.add_item(m.from_user.id, old)
        await m.answer(f"⚔️ Экипировано: <b>{item_name}</b>\nСнято: {old}",
                       reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    else:
        await m.answer(f"⚔️ Экипировано: <b>{item_name}</b>",
                       reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    u = await g.db.get_user(m.from_user.id)
    new_max = calc_max_hp(u)
    await g.db.update_hp_max(m.from_user.id, min(u["hp"], new_max), new_max)
    if await g.db.add_achievement(m.from_user.id, "equipped"):
        await m.answer("🏆 Достижение: ⚔️ Снаряжён", parse_mode=ParseMode.HTML)


@router.message(Command("unequip"))
async def unequip(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /unequip weapon|armor|accessory"); return
    slot = parts[1].strip().lower()
    if slot not in ("weapon", "armor", "accessory"):
        await m.answer("Слоты: weapon, armor, accessory"); return
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
    potion_buttons = []
    for it in items:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP:
            data = SHOP[name]
            if data["type"] == "potion":
                hp = data.get("heal_hp", 0)
                mp = data.get("heal_mp", 0)
                effect = f"+{hp} HP" if hp else f"+{mp} MP"
                lines.append(f"• 🧪 {name} — {effect}")
                potion_buttons.append([InlineKeyboardButton(
                    text=f"🧪 Использовать {name}",
                    callback_data=f"use_item_{name}"
                )])
            else:
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                suffix = f" (+{lvl})" if lvl else ""
                lines.append(f"• {name}{suffix} — {bonus_str}")
        else:
            lines.append(f"• {it['item_name']}")

    # Экипированное
    eq_lines = []
    for slot, label in [("equipped_weapon", "🗡 Оружие"),
                        ("equipped_armor", "🛡 Броня"),
                        ("equipped_accessory", "💍 Аксессуар")]:
        val = u.get(slot) or "—"
        eq_lines.append(f"{label}: {val}")

    lines.append("\n<b>Экипировано:</b>")
    lines.extend(eq_lines)
    lines.append("\n<i>/equip Название+N · /use Зелье</i>")

    kb = InlineKeyboardMarkup(inline_keyboard=potion_buttons) if potion_buttons else main_kb()
    await m.answer("\n".join(lines), reply_markup=kb,
                   parse_mode=ParseMode.HTML)
