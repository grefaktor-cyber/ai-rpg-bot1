"""Торговля: /sell (NPC), /pay (золото), /drop, /pickup, /trade (обмен)."""
import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from core.game_data import SHOP
from core.formulas import parse_item
from core.keyboards import main_kb
import world as W

router = Router()


class TradeStates(StatesGroup):
    choosing_mine = State()


# ================= SELL =================
SELL_RATE = 0.6  # 60% от цены


def _sell_price(item_name):
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        return 0
    # Эксклюзивные за Stars — нельзя продать
    if SHOP[base_name].get("premium"):
        return 0
    base = SHOP[base_name]["price"]
    return int(base * (1 + lvl * 0.2) * SELL_RATE)


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
            f"Продажа NPC: <b>{int(SELL_RATE*100)}%</b> цены.\n"
            f"Улучшенные предметы дороже: <b>+20%</b> за каждый +1.",
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
    if price == 0:
        await m.answer("❌ Эксклюзивные предметы нельзя продать.")
        return
    ok = await g.db.sell_item(m.from_user.id, item_name, price)
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    u = await g.db.get_user(c.from_user.id)
    await c.answer(f"✅ +{price}💰")
    await c.message.answer(
        f"💰 <b>{item_name}</b> продан за <b>{price}</b>.\n"
        f"Всего: {u['gold']}💰",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= PAY (в любую локацию) =================
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
    # НЕТ проверки локации — можно передавать куда угодно

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


# ================= DROP =================
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


# ================= PICKUP =================
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


# ================= TRADE (обмен предметами) =================
@router.message(Command("trade"))
async def trade_cmd(m: Message, state: FSMContext):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ В бою нельзя обмениваться."); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: <code>/trade Имя</code>\n\n"
                       "Открывает меню обмена. Ты выбираешь свои предметы, "
                       "соперник — свои. Потом оба подтверждают.",
                       parse_mode=ParseMode.HTML)
        return
    target = await g.db.get_user_by_char_name(parts[1].strip())
    if not target:
        await m.answer(f"❌ «{parts[1]}» не найден."); return
    if target["user_id"] == u["user_id"]:
        await m.answer("❌ Нельзя себе."); return
    if await g.db.get_combat(target["user_id"]):
        await m.answer(f"❌ {target['char_name']} в бою."); return

    oid = await g.db.create_trade_offer(u["user_id"], u["char_name"],
                                        target["user_id"], target["char_name"])
    await state.set_state(TradeStates.choosing_mine)
    await state.update_data(trade_id=oid, my_items=[], my_gold=0)

    await _show_trade_menu(m.chat.id, u["user_id"], oid, state)


@router.callback_query(F.data.startswith("trade_"))
async def trade_callbacks(c: CallbackQuery, state: FSMContext):
    data = c.data
    if data == "trade_cancel_all":
        await state.clear()
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await c.answer("Отменено")
        return

    # Формат: trade_<action>_<oid>[_<param>]
    parts = data.split("_", 3)
    if len(parts) < 3:
        await c.answer("Ошибка"); return
    action = parts[1]
    try:
        oid = int(parts[2])
    except ValueError:
        await c.answer("Ошибка"); return

    offer = await g.db.get_trade_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Обмен неактивен", show_alert=True); return
    if c.from_user.id not in (offer["from_id"], offer["to_id"]):
        await c.answer("Не твой обмен", show_alert=True); return

    is_sender = c.from_user.id == offer["from_id"]
    my_field = "from_items" if is_sender else "to_items"
    my_gold_field = "from_gold" if is_sender else "to_gold"
    my_confirmed_field = "from_confirmed" if is_sender else "to_confirmed"

    if action == "add":
        item_name = parts[3] if len(parts) > 3 else ""
        if not item_name:
            await c.answer("Ошибка"); return
        inv = await g.db.get_inventory(c.from_user.id)
        if not any(i["item_name"] == item_name for i in inv):
            await c.answer("Нет в инвентаре", show_alert=True); return
        try:
            current = json.loads(offer[my_field] or "[]")
        except Exception:
            current = []
        if item_name in current:
            await c.answer("Уже добавлен", show_alert=True); return
        current.append(item_name)
        await g.db.update_trade_field(oid, my_field, json.dumps(current))
        # Сброс подтверждений — состав изменился
        await g.db.update_trade_field(oid, "from_confirmed", "0")
        await g.db.update_trade_field(oid, "to_confirmed", "0")
        await c.answer(f"✅ +{item_name}")
        await _refresh_trade_menu(c.from_user.id, oid, is_sender)
        return

    if action == "remove":
        item_name = parts[3] if len(parts) > 3 else ""
        try:
            current = json.loads(offer[my_field] or "[]")
        except Exception:
            current = []
        if item_name in current:
            current.remove(item_name)
        await g.db.update_trade_field(oid, my_field, json.dumps(current))
        await g.db.update_trade_field(oid, "from_confirmed", "0")
        await g.db.update_trade_field(oid, "to_confirmed", "0")
        await c.answer(f"−{item_name}")
        await _refresh_trade_menu(c.from_user.id, oid, is_sender)
        return

    if action == "gold":
        # parts[3] — сумма
        try:
            amount = int(parts[3]) if len(parts) > 3 else 0
        except ValueError:
            amount = 0
        u = await g.db.get_user(c.from_user.id)
        if amount < 0 or amount > u["gold"]:
            await c.answer("Неверная сумма", show_alert=True); return
        await g.db.update_trade_field(oid, my_gold_field, str(amount))
        await g.db.update_trade_field(oid, "from_confirmed", "0")
        await g.db.update_trade_field(oid, "to_confirmed", "0")
        await c.answer(f"💰 {amount} золота")
        await _refresh_trade_menu(c.from_user.id, oid, is_sender)
        return

    if action == "goldprompt":
        await state.update_data(pending_gold_oid=oid)
        await c.answer()
        await c.message.answer("💰 Введи сумму золота числом. 0 — без золота.")
        return

    if action == "confirm":
        # Проверяем что предметы ещё в инвентаре
        try:
            my_items = json.loads(offer[my_field] or "[]")
        except Exception:
            my_items = []
        inv = await g.db.get_inventory(c.from_user.id)
        inv_names = [i["item_name"] for i in inv]
        for it in my_items:
            if it not in inv_names:
                await c.answer(f"❌ {it} больше нет в инвентаре", show_alert=True)
                return
        my_gold = offer[my_gold_field] or 0
        u = await g.db.get_user(c.from_user.id)
        if my_gold > u["gold"]:
            await c.answer("❌ Не хватает золота", show_alert=True); return

        await g.db.update_trade_field(oid, my_confirmed_field, "1")
        await c.answer("✅ Подтверждено")

        # Проверяем оба
        fresh = await g.db.get_trade_offer(oid)
        if fresh["from_confirmed"] and fresh["to_confirmed"]:
            await _execute_trade(oid)
        else:
            await _refresh_trade_menu(c.from_user.id, oid, is_sender)
            # Уведомить соперника
            try:
                other_id = fresh["to_id"] if is_sender else fresh["from_id"]
                await g.bot.send_message(other_id,
                    "🤝 Соперник подтвердил обмен. Твой ход!")
            except Exception:
                pass
        return

    await c.answer()


@router.message(TradeStates.choosing_mine, F.text.regexp(r"^\d+$"))
async def trade_gold_input(m: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("pending_gold_oid")
    if not oid:
        return
    offer = await g.db.get_trade_offer(oid)
    if not offer or offer["status"] != "pending":
        await m.answer("Обмен неактивен.")
        await state.update_data(pending_gold_oid=None)
        return
    is_sender = m.from_user.id == offer["from_id"]
    my_gold_field = "from_gold" if is_sender else "to_gold"
    try:
        amount = int(m.text.strip())
    except ValueError:
        await m.answer("Число нужно."); return
    u = await g.db.get_user(m.from_user.id)
    if amount < 0 or amount > u["gold"]:
        await m.answer(f"❌ У тебя {u['gold']}💰"); return
    await g.db.update_trade_field(oid, my_gold_field, str(amount))
    await g.db.update_trade_field(oid, "from_confirmed", "0")
    await g.db.update_trade_field(oid, "to_confirmed", "0")
    await state.update_data(pending_gold_oid=None)
    await m.answer(f"💰 Золото: {amount}")
    await _refresh_trade_menu(m.from_user.id, oid, is_sender)


async def _show_trade_menu(chat_id, uid, oid, state):
    offer = await g.db.get_trade_offer(oid)
    is_sender = uid == offer["from_id"]
    text = _trade_text(offer, is_sender)
    kb = _trade_kb(offer, is_sender, uid)
    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)
    # Уведомить второго
    other_id = offer["to_id"] if is_sender else offer["from_id"]
    if other_id != uid:
        try:
            other_is_sender = other_id == offer["from_id"]
            o_text = _trade_text(offer, other_is_sender)
            o_kb = _trade_kb(offer, other_is_sender, other_id)
            await g.bot.send_message(other_id, o_text, reply_markup=o_kb,
                                     parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def _refresh_trade_menu(uid, oid, is_sender):
    offer = await g.db.get_trade_offer(oid)
    text = _trade_text(offer, is_sender)
    kb = _trade_kb(offer, is_sender, uid)
    try:
        # Просто шлём новое сообщение — старые не редактируем
        await g.bot.send_message(uid, text, reply_markup=kb,
                                 parse_mode=ParseMode.HTML)
    except Exception:
        pass
    # Уведомить соперника
    try:
        other_id = offer["to_id"] if is_sender else offer["from_id"]
        other_is_sender = other_id == offer["from_id"]
        o_text = _trade_text(offer, other_is_sender)
        o_kb = _trade_kb(offer, other_is_sender, other_id)
        await g.bot.send_message(other_id,
            f"🔔 <b>Обмен обновлён.</b>\n\n" + o_text,
            reply_markup=o_kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass


def _trade_text(offer, is_sender):
    try:
        mine = json.loads((offer["from_items"] if is_sender else offer["to_items"]) or "[]")
    except Exception:
        mine = []
    try:
        theirs = json.loads((offer["to_items"] if is_sender else offer["from_items"]) or "[]")
    except Exception:
        theirs = []
    my_gold = offer["from_gold"] if is_sender else offer["to_gold"]
    their_gold = offer["to_gold"] if is_sender else offer["from_gold"]
    my_confirmed = bool(offer["from_confirmed"] if is_sender else offer["to_confirmed"])
    their_confirmed = bool(offer["to_confirmed"] if is_sender else offer["from_confirmed"])

    me_name = offer["from_name"] if is_sender else offer["to_name"]
    them_name = offer["to_name"] if is_sender else offer["from_name"]

    text = f"🤝 <b>Обмен</b> [{offer['id']}]\n\n"
    text += f"<b>Ты ({me_name}):</b> {'✅ подтвердил' if my_confirmed else '⏳ выбирает'}\n"
    if mine:
        for it in mine:
            text += f"  • {it}\n"
    else:
        text += "  <i>— пусто —</i>\n"
    if my_gold:
        text += f"  💰 {my_gold} золота\n"
    text += f"\n<b>{them_name}:</b> {'✅ подтвердил' if their_confirmed else '⏳ выбирает'}\n"
    if theirs:
        for it in theirs:
            text += f"  • {it}\n"
    else:
        text += "  <i>— пусто —</i>\n"
    if their_gold:
        text += f"  💰 {their_gold} золота\n"
    return text


def _trade_kb(offer, is_sender, uid):
    oid = offer["id"]
    my_field = "from_items" if is_sender else "to_items"
    try:
        mine = json.loads(offer[my_field] or "[]")
    except Exception:
        mine = []

    rows = []
    # Кнопка добавить предмет
    rows.append([InlineKeyboardButton(
        text="➕ Добавить предмет", callback_data=f"trade_addprompt_{oid}")])
    rows.append([InlineKeyboardButton(
        text="💰 Задать золото", callback_data=f"trade_goldprompt_{oid}")])
    # Убрать предметы
    for it in mine:
        rows.append([InlineKeyboardButton(
            text=f"➖ {it}", callback_data=f"trade_remove_{oid}_{it}")])
    # Подтвердить
    rows.append([InlineKeyboardButton(
        text="✅ Подтвердить", callback_data=f"trade_confirm_{oid}")])
    rows.append([InlineKeyboardButton(
        text="❌ Отменить", callback_data=f"trade_cancel_all")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("trade_addprompt_"))
async def trade_addprompt(c: CallbackQuery, state: FSMContext):
    oid = int(c.data.replace("trade_addprompt_", ""))
    offer = await g.db.get_trade_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Неактивно", show_alert=True); return
    if c.from_user.id not in (offer["from_id"], offer["to_id"]):
        await c.answer("Не твой", show_alert=True); return
    inv = await g.db.get_inventory(c.from_user.id)
    if not inv:
        await c.answer("Инвентарь пуст", show_alert=True); return
    is_sender = c.from_user.id == offer["from_id"]
    my_field = "from_items" if is_sender else "to_items"
    try:
        mine = json.loads(offer[my_field] or "[]")
    except Exception:
        mine = []
    rows = []
    for it in inv:
        n = it["item_name"]
        if n in mine:
            continue
        rows.append([InlineKeyboardButton(
            text=f"+ {n}", callback_data=f"trade_add_{oid}_{n}")])
    rows.append([InlineKeyboardButton(
        text="⬅️ Назад", callback_data=f"trade_back_{oid}")])
    await c.message.answer("Выбери предмет для добавления:",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await c.answer()


@router.callback_query(F.data.startswith("trade_back_"))
async def trade_back(c: CallbackQuery):
    oid = int(c.data.replace("trade_back_", ""))
    offer = await g.db.get_trade_offer(oid)
    if not offer:
        await c.answer("Нет"); return
    is_sender = c.from_user.id == offer["from_id"]
    text = _trade_text(offer, is_sender)
    kb = _trade_kb(offer, is_sender, c.from_user.id)
    await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


async def _execute_trade(oid):
    offer = await g.db.get_trade_offer(oid)
    try:
        from_items = json.loads(offer["from_items"] or "[]")
    except Exception:
        from_items = []
    try:
        to_items = json.loads(offer["to_items"] or "[]")
    except Exception:
        to_items = []
    from_gold = offer["from_gold"] or 0
    to_gold = offer["to_gold"] or 0

    # Проверки
    f_inv = await g.db.get_inventory(offer["from_id"])
    t_inv = await g.db.get_inventory(offer["to_id"])
    f_names = [i["item_name"] for i in f_inv]
    t_names = [i["item_name"] for i in t_inv]
    for it in from_items:
        if it not in f_names:
            await g.db.set_trade_status(oid, "cancelled")
            return
    for it in to_items:
        if it not in t_names:
            await g.db.set_trade_status(oid, "cancelled")
            return
    f = await g.db.get_user(offer["from_id"])
    t = await g.db.get_user(offer["to_id"])
    if from_gold > f["gold"] or to_gold > t["gold"]:
        await g.db.set_trade_status(oid, "cancelled")
        return

    # Убираем предметы
    for it in from_items:
        await g.db.remove_item(offer["from_id"], it)
    for it in to_items:
        await g.db.remove_item(offer["to_id"], it)
    # Добавляем друг другу
    for it in from_items:
        await g.db.add_item(offer["to_id"], it)
    for it in to_items:
        await g.db.add_item(offer["from_id"], it)
    # Золото
    if from_gold:
        await g.db.spend_gold(offer["from_id"], from_gold)
        await g.db.add_gold(offer["to_id"], from_gold)
    if to_gold:
        await g.db.spend_gold(offer["to_id"], to_gold)
        await g.db.add_gold(offer["from_id"], to_gold)

    await g.db.set_trade_status(oid, "completed")

    # Уведомить
    for uid, name in [(offer["from_id"], offer["from_name"]),
                      (offer["to_id"], offer["to_name"])]:
        try:
            await g.bot.send_message(uid,
                "✅ <b>Обмен завершён!</b>\n\n"
                f"Предметы и золото перешли. Проверь 🎒 Инвентарь.",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass
