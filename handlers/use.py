"""Использование зелий вне боя: команда /use + кнопка в инвентаре."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.keyboards import main_kb

router = Router()


def _apply_potion(u, data):
    """Возвращает (msg, new_hp, new_mp) — что изменилось."""
    heal_hp = data.get("heal_hp", 0)
    heal_mp = data.get("heal_mp", 0)
    new_hp = u["hp"]
    new_mp = u["mp"]
    parts = []
    if heal_hp:
        new_hp = min(u["max_hp"], u["hp"] + heal_hp)
        parts.append(f"❤️ +{heal_hp} HP → {new_hp}/{u['max_hp']}")
    if heal_mp:
        new_mp = min(u["max_mp"], u["mp"] + heal_mp)
        parts.append(f"💧 +{heal_mp} MP → {new_mp}/{u['max_mp']}")
    return parts, new_hp, new_mp


async def _do_use(uid, item_name):
    """Общая логика. Возвращает (ok, message)."""
    if item_name not in SHOP or SHOP[item_name].get("type") != "potion":
        return False, "❌ Это не зелье."
    u = await g.db.get_user(uid)
    inv = await g.db.get_inventory(uid)
    inv_names = [i["item_name"] for i in inv]
    if item_name not in inv_names:
        return False, "❌ Нет в инвентаре. Купи в 🛒 Магазине."
    data = SHOP[item_name]
    heal_hp = data.get("heal_hp", 0)
    heal_mp = data.get("heal_mp", 0)
    if heal_hp and u["hp"] >= u["max_hp"] and not heal_mp:
        return False, "❤️ HP уже полное."
    if heal_mp and u["mp"] >= u["max_mp"] and not heal_hp:
        return False, "💧 MP уже полное."
    if heal_hp and heal_mp and u["hp"] >= u["max_hp"] and u["mp"] >= u["max_mp"]:
        return False, "❤️💧 HP и MP уже полные."

    parts, new_hp, new_mp = _apply_potion(u, data)
    if new_hp != u["hp"]:
        await g.db.update_hp(uid, new_hp)
    if new_mp != u["mp"]:
        await g.db.update_mp(uid, new_mp)
    await g.db.remove_item(uid, item_name)
    msg = f"🧪 <b>{item_name}</b> использован.\n\n" + "\n".join(parts)
    return True, msg


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

    item_query = parts[1].strip()
    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    if not inv_names:
        await m.answer("🎒 Инвентарь пуст."); return

    from core.fuzzy import find_inventory_item
    exact, suggestions = find_inventory_item(item_query, inv_names)

    if exact:
        item_name = exact
    elif suggestions:
        # Оставляем только зелья
        potion_sugg = [s for s in suggestions
                       if s in SHOP and SHOP[s].get("type") == "potion"]
        if not potion_sugg:
            await m.answer(f"❌ Среди найденных нет зелий.")
            return
        rows = []
        for s in potion_sugg[:10]:
            rows.append([InlineKeyboardButton(
                text=f"🧪 Использовать {s}",
                callback_data=f"use_item_{s}"
            )])
        rows.append([InlineKeyboardButton(text="❌ Отмена",
                                          callback_data="fuzzy_cancel")])
        await m.answer(
            f"🔍 Нашёл несколько, уточни:\n\n<code>{item_query}</code>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode=ParseMode.HTML)
        return
    else:
        await m.answer(f"❌ Не нашёл «{item_query}».")
        return

    ok, msg = await _do_use(m.from_user.id, item_name)
    await m.answer(msg, reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("use_item_"))
async def use_item_cb(c):
    item_name = c.data.replace("use_item_", "", 1)
    if await g.db.get_combat(c.from_user.id):
        await c.answer("⚔️ Используй кнопками в бою", show_alert=True); return
    ok, msg = await _do_use(c.from_user.id, item_name)
    if not ok:
        await c.answer(msg, show_alert=True); return
    await c.answer("✅ Использовано")
    await c.message.answer(msg, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
