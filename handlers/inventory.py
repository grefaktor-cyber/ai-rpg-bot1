"""Инвентарь 4.0: 5 категорий, 8 слотов, редкие материалы, поиск."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from core.equipment import (
    SHOP, SLOTS, SLOT_NAMES, can_use_item, get_set_bonus,
)
from core.formulas import parse_item
from core.keyboards import main_kb, inv_search_cancel_kb

router = Router()

PAGE_SIZE = 8

CATEGORIES = {
    "weapon":    ("⚔️ Оружие", "⚔️"),
    "armor":     ("🛡 Броня", "🛡"),
    "accessory": ("💍 Аксессуары", "💍"),
    "potion":    ("🧪 Зелья", "🧪"),
    "other":     ("📦 Прочее", "📦"),
}


class InvSearchState(StatesGroup):
    waiting_query = State()


def _grade_icon(grade):
    return {"common": "⚪", "D": "🔷", "C": "🔶", "B": "💎"}.get(grade, "⚪")


def _categorize(items):
    groups = {k: [] for k in CATEGORIES}
    for it in items:
        name, lvl = parse_item(it["item_name"])
        data = SHOP.get(name)
        if not data:
            groups["other"].append(it)
            continue
        it_t = data.get("type")
        if it_t == "weapon":
            groups["weapon"].append(it)
        elif it_t in ("armor", "shield"):
            groups["armor"].append(it)
        elif it_t == "accessory":
            groups["accessory"].append(it)
        elif it_t == "potion":
            groups["potion"].append(it)
        else:
            groups["other"].append(it)
    return groups


@router.message(Command("inv"))
@router.message(Command("inventory"))
@router.message(F.text == "🎒 Инвентарь")
async def inventory_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    items = await g.db.get_inventory(m.from_user.id)
    await _show_main(m.chat.id, u, items)


async def _show_main(chat_id, u, items, edit_message=None):
    groups = _categorize(items)
    text = "🎒 <b>Инвентарь</b>\n\n"
    text += f"💰 Золото: <b>{u['gold']}</b>\n"
    text += f"📦 Предметов: <b>{len(items)}</b>\n\n"
    text += "Выбери категорию:"
    rows = []
    rows.append([
        InlineKeyboardButton(text=f"⚔️ Оружие ({len(groups['weapon'])})",
                             callback_data="inv_cat_weapon_0"),
        InlineKeyboardButton(text=f"🛡 Броня ({len(groups['armor'])})",
                             callback_data="inv_cat_armor_0"),
    ])
    rows.append([
        InlineKeyboardButton(text=f"💍 Аксессуары ({len(groups['accessory'])})",
                             callback_data="inv_cat_accessory_0"),
        InlineKeyboardButton(text=f"🧪 Зелья ({len(groups['potion'])})",
                             callback_data="inv_cat_potion_0"),
    ])
    if groups["other"]:
        rows.append([InlineKeyboardButton(
            text=f"📦 Прочее ({len(groups['other'])})",
            callback_data="inv_cat_other_0")])
    rows.append([
        InlineKeyboardButton(text="👑 Экипировано", callback_data="inv_equipped"),
        InlineKeyboardButton(text="📦 Материалы", callback_data="inv_materials"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔍 Поиск", callback_data="inv_search_start"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="inv_close"),
    ])
    text += "\n\n⚪ Обычный · 🔷 D · 🔶 C · 💎 B"
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=kb,
                                          parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass
    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("inv_cat_"))
async def inv_cat_cb(c: CallbackQuery):
    parts = c.data.split("_")
    if len(parts) < 4:
        await c.answer("Ошибка"); return
    cat = parts[2]
    try:
        page = int(parts[3])
    except ValueError:
        page = 0
    if cat not in CATEGORIES:
        await c.answer("Неизвестно"); return
    u = await g.db.get_user(c.from_user.id)
    items = await g.db.get_inventory(c.from_user.id)
    groups = _categorize(items)
    cat_items = groups[cat]
    label, icon = CATEGORIES[cat]
    text = f"{icon} <b>{label}</b>\n\n"
    if not cat_items:
        text += "<i>Пусто.</i>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В инвентарь", callback_data="inv_menu")],
        ])
        try:
            await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        await c.answer()
        return
    total = len(cat_items)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = cat_items[start:end]
    rows = []
    for it in page_items:
        name, lvl = parse_item(it["item_name"])
        data = SHOP.get(name, {})
        grade = data.get("grade", "common")
        g_icon = _grade_icon(grade)
        suffix = f" +{lvl}" if lvl else ""
        if data.get("type") == "potion":
            action = "🧪"
        elif can_use_item(u["class"], name):
            action = "⚔️"
        else:
            action = "❌"
        text += f"{g_icon} {action} {it['item_name']}{suffix}\n"
        rows.append([InlineKeyboardButton(
            text=f"{g_icon} {action} {it['item_name']}{suffix}",
            callback_data=f"inv_item_{it['item_name']}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Стр.", callback_data=f"inv_cat_{cat}_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(
            text="Стр. ➡️", callback_data=f"inv_cat_{cat}_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ В инвентарь", callback_data="inv_menu")])
    text += f"\n<i>Страница {page+1} из {(total + PAGE_SIZE - 1) // PAGE_SIZE}</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "inv_menu")
async def inv_menu_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    items = await g.db.get_inventory(c.from_user.id)
    await _show_main(c.message.chat.id, u, items, edit_message=c.message)
    await c.answer()


@router.callback_query(F.data.startswith("inv_item_"))
async def inv_item_cb(c: CallbackQuery):
    item_name = c.data.replace("inv_item_", "", 1)
    u = await g.db.get_user(c.from_user.id)
    base_name, lvl = parse_item(item_name)
    data = SHOP.get(base_name)
    if not data:
        await c.answer("Это не обычный предмет", show_alert=True); return
    grade = data.get("grade", "common")
    g_icon = _grade_icon(grade)
    item_type = data.get("type")
    slot = data.get("slot", "")
    level_req = data.get("level_req", 1)
    text = f"{g_icon} <b>{item_name}</b>\n\n"
    text += f"📦 Тип: {item_type}\n"
    if slot:
        text += f"🎯 Слот: {SLOT_NAMES.get(slot, slot)}\n"
    text += f"⭐ Грейд: {grade.upper()}\n"
    text += f"📊 Треб. уровень: {level_req}\n"
    if data.get("bonus"):
        bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in data["bonus"].items())
        text += f"✨ Бонусы: {bonus_str}\n"
    if data.get("extra"):
        text += f"💫 Эффект: {data['extra']}\n"
    if lvl:
        text += f"🔨 Улучшение: +{lvl}\n"
    if item_type == "potion":
        hp = data.get("heal_hp", 0)
        mp = data.get("heal_mp", 0)
        if hp:
            text += f"💚 Восстанавливает: {hp} HP\n"
        if mp:
            text += f"💧 Восстанавливает: {mp} MP\n"
    else:
        if not can_use_item(u["class"], base_name):
            text += f"\n⚠️ <b>Твой класс не может носить</b>\n"
        elif u["level"] < level_req:
            text += f"\n⚠️ <b>Нужен {level_req} уровень</b>\n"
    rows = []
    if item_type == "potion":
        rows.append([InlineKeyboardButton(
            text="🧪 Использовать", callback_data=f"use_item_{item_name}")])
    elif item_type in ("weapon", "armor", "shield", "accessory"):
        if can_use_item(u["class"], base_name) and u["level"] >= level_req:
            rows.append([InlineKeyboardButton(
                text="⚔️ Надеть", callback_data=f"equip_item_{item_name}")])
        else:
            rows.append([InlineKeyboardButton(
                text="❌ Нельзя надеть", callback_data="inv_noop")])
    if not data.get("premium"):
        sell_price = int(data.get("price", 0) * 0.6 * (1 + lvl * 0.2))
        if sell_price > 0:
            rows.append([InlineKeyboardButton(
                text=f"💰 Продать за {sell_price}",
                callback_data=f"sell_item_{item_name}")])
    else:
        rows.append([InlineKeyboardButton(
            text="💎 Эксклюзив — нельзя продать",
            callback_data="inv_noop")])
    if not data.get("premium"):
        rows.append([InlineKeyboardButton(
            text="🗑 Выбросить", callback_data=f"drop_item_{item_name}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="inv_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "inv_noop")
async def inv_noop(c: CallbackQuery):
    await c.answer("Действие недоступно", show_alert=True)


@router.callback_query(F.data == "inv_equipped")
async def inv_equipped_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    text = "👑 <b>Экипировано</b>\n\n"
    for slot in SLOTS:
        val = u.get(f"equipped_{slot}") or "—"
        text += f"{SLOT_NAMES[slot]}: <b>{val}</b>\n"
    set_b = get_set_bonus(u)
    if set_b:
        text += f"\n🎁 <b>Сетовый бонус:</b> {set_b['desc']}\n"
    rows = []
    for slot in SLOTS:
        val = u.get(f"equipped_{slot}")
        if val:
            rows.append([InlineKeyboardButton(
                text=f"➖ Снять {SLOT_NAMES[slot]}",
                callback_data=f"inv_unequip_{slot}")])
    rows.append([InlineKeyboardButton(text="⬅️ В инвентарь", callback_data="inv_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("inv_unequip_"))
async def inv_unequip_cb(c: CallbackQuery):
    slot = c.data.replace("inv_unequip_", "")
    if slot not in SLOTS:
        await c.answer("Слот не найден"); return
    item = await g.db.unequip_item(c.from_user.id, slot)
    if not item:
        await c.answer("Слот пуст"); return
    await g.db.add_item(c.from_user.id, item)
    from core.formulas import calc_max_hp, calc_max_mp
    u = await g.db.get_user(c.from_user.id)
    new_max_hp = calc_max_hp(u)
    new_max_mp = calc_max_mp(u)
    await g.db.update_hp_max(c.from_user.id, min(u["hp"], new_max_hp), new_max_hp)
    await g.db.update_mp(c.from_user.id, min(u.get("mp", 0), new_max_mp))
    await c.answer(f"✅ Снято: {item}")
    await inv_equipped_cb(c)


@router.callback_query(F.data == "inv_materials")
async def inv_materials_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    rare = await g.db.get_rare_materials(c.from_user.id)
    text = "📦 <b>Материалы</b>\n\n"
    text += "<b>Обычные:</b>\n"
    text += f"🔩 Железо: <b>{u.get('mat_iron', 0)}</b>\n"
    text += f"🧵 Кожа: <b>{u.get('mat_leather', 0)}</b>\n"
    text += f"✨ Пыль: <b>{u.get('mat_dust', 0)}</b>\n"
    text += f"💎 Кристалл: <b>{u.get('mat_crystal', 0)}</b>\n\n"
    text += "<b>Редкие (спойл):</b>\n"
    if rare:
        for code, amt in rare.items():
            from core.materials import RARE_MATERIALS
            mat_name = RARE_MATERIALS.get(code, {}).get("name", code)
            text += f"{mat_name}: <b>{amt}</b>\n"
    else:
        text += "<i>Пока нет</i>\n"
    text += "\n<i>Используются в /craft</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚒️ Кузница", callback_data="craft_recipes")],
        [InlineKeyboardButton(text="⬅️ В инвентарь", callback_data="inv_menu")],
    ])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "inv_close")
async def inv_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


# ================= ПОИСК В ИНВЕНТАРЕ =================
@router.callback_query(F.data == "inv_search_start")
async def inv_search_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(InvSearchState.waiting_query)
    await c.answer()
    await c.message.answer(
        "🔍 <b>Поиск по инвентарю</b>\n\n"
        "Введи название предмета (можно частично):\n"
        "<i>Например: «клинок», «зелье», «меч»</i>",
        reply_markup=inv_search_cancel_kb(),
        parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "inv_search_cancel")
async def inv_search_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer("Отменено")


@router.message(InvSearchState.waiting_query, F.text)
async def inv_search_process(m: Message, state: FSMContext):
    await state.clear()
    query = m.text.strip().lower()
    if len(query) < 2:
        await m.answer("Слишком коротко. Введи хотя бы 2 символа."); return
    inv = await g.db.get_inventory(m.from_user.id)
    if not inv:
        await m.answer("🎒 Инвентарь пуст.", reply_markup=main_kb()); return
    matches = [it for it in inv if query in it["item_name"].lower()]
    if not matches:
        await m.answer(
            f"❌ Ничего не найдено по запросу: <code>{query}</code>",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return
    text = f"🔍 <b>Найдено {len(matches)}:</b>\n\n"
    rows = []
    for it in matches[:20]:
        text += f"• {it['item_name']}\n"
        rows.append([InlineKeyboardButton(
            text=f"📦 {it['item_name']}",
            callback_data=f"inv_item_{it['item_name']}")])
    rows.append([InlineKeyboardButton(text="⬅️ В инвентарь",
                                       callback_data="inv_menu")])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)
