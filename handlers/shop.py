"""Магазин, инвентарь, экипировка."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
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
                            ("accessory", "💍 Аксессуары")]:
        text += f"<b>{label}:</b>\n"
        for name, data in SHOP.items():
            if data["type"] == category:
                price = int(data["price"] * shop_mult)
                bonus_str = ", ".join(f"+{v} {k.upper()}"
                                      for k, v in data["bonus"].items())
                text += f"• {name} ({price}💰) — {bonus_str}\n"
        text += "\n"
    await m.answer(text, reply_markup=shop_kb(SHOP, shop_mult),
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
    await c.message.answer(f"✅ <b>{item_name}</b> куплен!\n/equip {item_name}",
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
    items = await g.db.get_inventory(m.from_user.id)
    if not items:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=main_kb()); return
    lines = []
    for it in items:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP:
            bonus_str = ", ".join(f"+{v} {k.upper()}"
                                  for k, v in SHOP[name]["bonus"].items())
            suffix = f" (+{lvl})" if lvl else ""
            lines.append(f"• {name}{suffix} — {bonus_str}")
        else:
            lines.append(f"• {it['item_name']}")
    text = "🎒 <b>Инвентарь</b>\n\n" + "\n".join(lines) + "\n\n<i>/equip Название+N</i>"
    await m.answer(text, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
