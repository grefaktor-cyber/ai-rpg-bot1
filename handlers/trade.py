"""Торговля: /sell (NPC), /pay (золото), /drop, /pickup."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.formulas import parse_item
from core.keyboards import main_kb
import world as W

router = Router()


# ================= КОМИССИЯ =================
SELL_RATE = 0.5  # 50% от цены


def _sell_price(item_name):
    """Цена продажи с учётом улучшений."""
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        return 0
    base = SHOP[base_name]["price"]
    # +20% за каждый +1
    return int(base * (1 + lvl * 0.2) * SELL_RATE)


# ================= /sell =================
@router.message(Command("sell"))
async def sell_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ В бою нельзя продавать."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer(
            "Использование: <code>/sell Название</code>\n\n"
            "Продажа NPC: <b>50%</b> цены.\n"
            "Улучшенные предметы дороже: <b>+20%</b> за каждый +1.",
            parse_mode=ParseMode.HTML)
        return
    item_name = parts[1].strip()
    base_name, _ = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Этот предмет нельзя продать."); return
    inv = await g.db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    price = _sell_price(item_name)
    ok = await g.db.sell_item(m.from_user.id, item_name, price)
    if not ok:
        await m.answer("❌ Не удалось продать."); return
    await m.answer(
        f"💰 <b>{item_name}</b> продан за <b>{price}</b>.\n"
        f"Всего золота: {u['gold'] + price}",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("sell_item_"))
async def sell_item_cb(c: CallbackQuery):
    item_name = c.data.replace("sell_item_", "", 1)
    if await g.db.get_combat(c.from_user.id):
        await c.answer("⚔️ В бою нельзя", show_alert=True); return
    inv = await g.db.get_inventory(c.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await c.answer("Нет в инвентаре", show_alert=True); return
    base_name, _ = parse_item(item_name)
    if base_name not in SHOP:
        await c.answer("Нельзя продать", show_alert=True); return
    price = _sell_price(item_name)
    ok = await g.db.sell_item(c.from_user.id, item_name, price)
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    u = await g.db.get_user(c.from_user.id)
    await c.answer(f"✅ +{price}💰")
    await c.message.answer(
        f"💰 <b>{item_name}</b> продан за <b>{price}</b>.\n"
        f"Всего: {u['gold']}💰",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= /pay =================
@router.message(Command("pay"))
async def pay_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    parts = m.text.split()
    if len(parts) < 3:
        await m.answer("Использование: <code>/pay Имя Сумма</code>",
                       parse_mode=ParseMode.HTML); return
    target_name = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await m.answer("Сумма — число."); return
    if amount < 1:
        await m.answer("Минимум 1💰"); return
    if amount > u["gold"]:
        await m.answer(f"❌ У тебя только {u['gold']}💰"); return
    target = await g.db.get_user_by_char_name(target_name)
    if not target:
        await m.answer(f"❌ «{target_name}» не найден."); return
    if target["user_id"] == u["user_id"]:
        await m.answer("❌ Нельзя себе."); return
    if target.get("location_code") != u.get("location_code"):
        await m.answer(f"❌ {target['char_name']} в другой локации."); return

    ok = await g.db.spend_gold(m.from_user.id, amount)
    if not ok:
        await m.answer("❌ Не хватает золота."); return
    await g.db.add_gold(target["user_id"], amount)

    await m.answer(
        f"💸 Передано <b>{amount}💰</b> → <b>{target['char_name']}</b>",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    try:
        await g.bot.send_message(target["user_id"],
            f"💰 <b>{u['char_name']}</b> передал тебе <b>{amount}💰</b>!",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= /drop =================
@router.message(Command("drop"))
async def drop_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ В бою нельзя выбрасывать."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: <code>/drop Название</code>",
                       parse_mode=ParseMode.HTML); return
    item_name = parts[1].strip()
    inv = await g.db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    base_name, lvl = parse_item(item_name)
    loc_code = u.get("location_code", "village")
    loc_name = W.get_location(loc_code).get("name", "?")
    ok = await g.db.drop_item(m.from_user.id, u["char_name"], loc_code,
                              item_name, lvl)
    if not ok:
        await m.answer("❌ Не удалось выбросить."); return
    await m.answer(
        f"🗑 <b>{item_name}</b> выброшен в «{loc_name}».\n\n"
        f"<i>Другие игроки могут подобрать через /pickup.</i>\n"
        f"<i>Исчезнет через 30 минут.</i>",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("drop_item_"))
async def drop_item_cb(c: CallbackQuery):
    item_name = c.data.replace("drop_item_", "", 1)
    if await g.db.get_combat(c.from_user.id):
        await c.answer("⚔️ В бою нельзя", show_alert=True); return
    u = await g.db.get_user(c.from_user.id)
    inv = await g.db.get_inventory(c.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await c.answer("Нет в инвентаре", show_alert=True); return
    base_name, lvl = parse_item(item_name)
    loc_code = u.get("location_code", "village")
    loc_name = W.get_location(loc_code).get("name", "?")
    ok = await g.db.drop_item(c.from_user.id, u["char_name"], loc_code,
                              item_name, lvl)
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer("🗑 Выброшено")
    await c.message.answer(
        f"🗑 <b>{item_name}</b> выброшен в «{loc_name}».",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= /pickup =================
@router.message(Command("pickup"))
async def pickup_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ В бою нельзя подбирать."); return
    loc_code = u.get("location_code", "village")
    loc_name = W.get_location(loc_code).get("name", "?")
    drops = await g.db.get_dropped_items(loc_code)
    if not drops:
        await m.answer(f"📭 В «{loc_name}» ничего не валяется.",
                       reply_markup=main_kb()); return
    text = f"🎁 <b>Предметы в «{loc_name}»:</b>\n\n"
    rows = []
    for d in drops:
        mins = d["age_sec"] // 60
        text += (f"• <b>{d['item_name']}</b> "
                 f"(от {d['char_name']}, {mins} мин назад)\n")
        rows.append([InlineKeyboardButton(
            text=f"🎒 Взять {d['item_name']}",
            callback_data=f"pickup_{d['id']}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Закрыть",
                                      callback_data="pickup_close")])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("pickup_"))
async def pickup_cb(c: CallbackQuery):
    if c.data == "pickup_close":
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await c.answer(); return
    try:
        drop_id = int(c.data.replace("pickup_", ""))
    except ValueError:
        await c.answer("Ошибка"); return
    if await g.db.get_combat(c.from_user.id):
        await c.answer("⚔️ В бою нельзя", show_alert=True); return
    item = await g.db.pickup_item(drop_id, c.from_user.id)
    if not item:
        await c.answer("Уже подобрали", show_alert=True); return
    await c.answer(f"✅ {item}")
    await c.message.answer(f"🎒 Получено: <b>{item}</b>",
                           reply_markup=main_kb(), parse_mode=ParseMode.HTML)
