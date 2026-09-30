"""Использование зелий вне боя (только через /use)."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.keyboards import main_kb

router = Router()


@router.message(Command("use"))
async def use_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Используй зелья в бою кнопками."); return

    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /use Зелье HP"); return
    item_name = parts[1].strip()
    if item_name not in SHOP or SHOP[item_name].get("type") != "potion":
        await m.answer("❌ Это не зелье."); return

    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    if item_name not in inv_names:
        await m.answer("❌ Нет в инвентаре. Купи в 🛒 Магазине."); return

    data = SHOP[item_name]
    heal_hp = data.get("heal_hp", 0)
    heal_mp = data.get("heal_mp", 0)
    if heal_hp and u["hp"] >= u["max_hp"]:
        await m.answer("❤️ HP уже полное."); return
    if heal_mp and u["mp"] >= u["max_mp"]:
        await m.answer("💧 MP уже полное."); return

    msg = f"🧪 <b>{item_name}</b> использован.\n\n"
    if heal_hp:
        new_hp = min(u["max_hp"], u["hp"] + heal_hp)
        await g.db.update_hp(m.from_user.id, new_hp)
        msg += f"❤️ +{heal_hp} HP → {new_hp}/{u['max_hp']}\n"
    if heal_mp:
        new_mp = min(u["max_mp"], u["mp"] + heal_mp)
        await g.db.update_mp(m.from_user.id, new_mp)
        msg += f"💧 +{heal_mp} MP → {new_mp}/{u['max_mp']}\n"

    await g.db.remove_item(m.from_user.id, item_name)
    await m.answer(msg, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
