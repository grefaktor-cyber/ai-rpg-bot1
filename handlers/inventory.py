"""Инвентарь 2.0: 5 категорий, пагинация, сортировка, фильтр."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP
from core.equipment import SLOTS, SLOT_NAMES, can_use_item, get_set_bonus
from core.formulas import parse_item
from core.keyboards import main_kb


router = Router()

PAGE_SIZE = 8

# Сортировка грейдов: C (лучший) → D → common
GRADE_ORDER = {"C": 0, "D": 1, "common": 2}

# Настройки пользователя в памяти (сброс при рестарте)
_USER_PREFS = {}  # uid -> {"sort": "grade"|"name"|"level", "filter": bool}


def _get_prefs(uid):
    if uid not in _USER_PREFS:
        _USER_PREFS[uid] = {"sort": "grade", "filter": False}
    return _USER_PREFS[uid]


def _set_pref(uid, key, value):
    _get_prefs(uid)[key] = value


# ================= КАТЕГОРИИ =================
CATEGORIES = {
    "weapon":    ("⚔️ Оружие", "⚔️"),
    "armor":     ("🛡 Броня", "🛡"),
    "accessory": ("💍 Аксессуары", "💍"),
    "potion":    ("🧪 Зелья", "🧪"),
    "other":     ("📦 Прочее", "📦"),
}


def _grade_icon(grade):
    return {"common": "⚪", "D": "🔷", "C": "🔶"}.get(grade, "⚪")


def _categorize(items):
    """Разбить предметы по 5 категориям."""
    groups = {k: [] for k in CATEGORIES}
    for it in items:
        name, lvl = parse_item(it["item_name"])
        data = SHOP.get(name)
        if not data:
            groups["other"].append(it)
            continue
        item_type = data.get("type")

        if item_type == "weapon":
            groups["weapon"].append(it)
        elif item_type in ("armor", "shield"):
            groups["armor"].append(it)
        elif item_type == "accessory":
            groups["accessory"].append(it)
        elif item_type == "potion":
            groups["potion"].append(it)
        else:
            groups["other"].append(it)
    return groups


def _sort_items(items, mode):
    """Сортировать предметы по режиму."""
    def key_grade(it):
        name, lvl = parse_item(it["item_name"])
        data = SHOP.get(name, {})
        grade = data.get("grade", "common")
        return (GRADE_ORDER.get(grade, 3), -lvl, name.lower())

    def key_name(it):
        name, _ = parse_item(it["item_name"])
        return name.lower()

    def key_level(it):
        name, lvl = parse_item(it["item_name"])
        data = SHOP.get(name, {})
        level_req = data.get("level_req", 1)
        return (-level_req, -lvl, name.lower())

    if mode == "name":
        return sorted(items, key=key_name)
    if mode == "level":
        return sorted(items, key=key_level)
    return sorted(items, key=key_grade)


def _filter_items(items, user_class, only_usable):
    """Фильтр 'только доступные'."""
    if not only_usable:
        return items
    result = []
    for it in items:
        name, _ = parse_item(it["item_name"])
        data = SHOP.get(name, {})
        if data.get("type") == "potion":
            result.append(it)
            continue
        if can_use_item(user_class, name):
            result.append(it)
    return result


def _count_usable(items, user_class):
    """Сколько из items доступны классу."""
    cnt = 0
    for it in items:
        name, _ = parse_item(it["item_name"])
        data = SHOP.get(name, {})
        if data.get("type") == "potion":
            cnt += 1
            continue
        if can_use_item(user_class, name):
            cnt += 1
    return cnt


# ================= ГЛАВНОЕ МЕНЮ =================
@router.message(Command("inv"))
@router.message(Command("inventory"))
@router.message(F.text == "🎒 Инвентарь")
async def inventory_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    items = await g.db.get_inventory(m.from_user.id)
    await _show_main(m.chat.id, u, items)


async def _show_main(chat_id, u, items, edit_message=None):
    groups = _categorize(items)
    prefs = _get_prefs(u["user_id"])
    my_class = u["class"]

    text = "🎒 <b>Инвентарь</b>\n\n"
    text += f"💰 Золото: <b>{u['gold']}</b>\n"
    text += f"📦 Предметов: <b>{len(items)}</b>\n\n"

    # Легенда сортировки
    sort_label = {"grade": "по грейду", "name": "по имени", "level": "по уровню"}[prefs["sort"]]
    text += f"🔀 Сортировка: <b>{sort_label}</b>\n"
    if prefs["filter"]:
        text += "👁 Фильтр: <b>только доступные</b>\n"
    text += "\nВыбери категорию:"

    rows = []

    def cat_btn(cat):
        cnt_all = len(groups[cat])
        cnt_usable = _count_usable(groups[cat], my_class)
        icon = CATEGORIES[cat][1]
        if cat == "potion":
            label = f"{icon} Зелья ({cnt_all})"
        else:
            label = f"{icon} {CATEGORIES[cat][0].split(' ', 1)[1]} ({cnt_usable}/{cnt_all})"
        return InlineKeyboardButton(text=label, callback_data=f"inv_cat_{cat}_0")

    rows.append([cat_btn("weapon"), cat_btn("armor")])
    rows.append([cat_btn("accessory"), cat_btn("potion")])
    if groups["other"]:
        rows.append([cat_btn("other")])

    # Кнопки сортировки
    rows.append([
        InlineKeyboardButton(text="🔀 Грейд",
                             callback_data="inv_sort_grade"),
        InlineKeyboardButton(text="🔤 Имя",
                             callback_data="inv_sort_name"),
        InlineKeyboardButton(text="⭐ Уровень",
                             callback_data="inv_sort_level"),
    ])
    # Фильтр
    filter_text = "👁 Фильтр: ВКЛ" if prefs["filter"] else "👁 Фильтр: ВЫКЛ"
    rows.append([InlineKeyboardButton(text=filter_text,
                                       callback_data="inv_toggle_filter")])
    # Экипировано + Материалы
    rows.append([
        InlineKeyboardButton(text="👑 Экипировано", callback_data="inv_equipped"),
        InlineKeyboardButton(text="📦 Материалы", callback_data="inv_materials"),
    ])
    rows.append([InlineKeyboardButton(text="❌ Закрыть",
                                       callback_data="inv_close")])

    text += "\n\n⚪ Обычный · 🔷 D · 🔶 C"

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


# ================= СОРТИРОВКА / ФИЛЬТР =================
@router.callback_query(F.data.startswith("inv_sort_"))
async def inv_sort_cb(c: CallbackQuery):
    mode = c.data.replace("inv_sort_", "")
    if mode not in ("grade", "name", "level"):
        await c.answer("Ошибка"); return
    _set_pref(c.from_user.id, "sort", mode)
    await c.answer(f"🔀 Сортировка: {mode}")
    await inv_menu_cb(c)


@router.callback_query(F.data == "inv_toggle_filter")
async def inv_toggle_filter_cb(c: CallbackQuery):
    prefs = _get_prefs(c.from_user.id)
    prefs["filter"] = not prefs["filter"]
    state = "ВКЛ" if prefs["filter"] else "ВЫКЛ"
    await c.answer(f"👁 Фильтр: {state}")
    await inv_menu_cb(c)


# ================= КАТЕГОРИЯ =================
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
    cat_items = list(groups[cat])

    # Фильтр
    prefs = _get_prefs(c.from_user.id)
    if prefs["filter"] and cat != "potion":
        cat_items = _filter_items(cat_items, u["class"], True)

    # Сортировка
    cat_items = _sort_items(cat_items, prefs["sort"])

    label, icon = CATEGORIES[cat]
    text = f"{icon} <b>{label}</b>"
    if prefs["filter"] and cat != "potion":
        text += " · <i>только доступные</i>"
    text += "\n\n"

    if not cat_items:
        text += "<i>Пусто.</i>"
        rows = [
            [InlineKeyboardButton(text="👁 Фильтр: ВЫКЛ",
                                   callback_data="inv_toggle_filter")],
            [InlineKeyboardButton(text="⬅️ В инвентарь",
                                   callback_data="inv_menu")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        try:
            await c.message.edit_text(text, reply_markup=kb,
                                      parse_mode=ParseMode.HTML)
        except Exception:
            await c.message.answer(text, reply_markup=kb,
                                   parse_mode=ParseMode.HTML)
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

    rows.append([InlineKeyboardButton(text="⬅️ В инвентарь",
                                       callback_data="inv_menu")])

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


# ================= ПРЕДМЕТ =================
@router.callback_query(F.data.startswith("inv_item_"))
async def inv_item_cb(c: CallbackQuery):
    item_name = c.data.replace("inv_item_", "", 1)
    u = await g.db.get_user(c.from_user.id)

    base_name, lvl = parse_item(item_name)
    data = SHOP.get(base_name)
    if not data:
        await c.answer("Не найдено", show_alert=True); return

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
        heal_hp = data.get("heal_hp", 0)
        heal_mp = data.get("heal_mp", 0)
        if heal_hp:
            text += f"💚 Восстанавливает: {heal_hp} HP\n"
        if heal_mp:
            text += f"💧 Восстанавливает: {heal_mp} MP\n"
    else:
        can_use = can_use_item(u["class"], base_name)
        if not can_use:
            text += f"\n⚠️ <b>Твой класс ({u['class']}) не может носить</b>\n"
        elif u["level"] < level_req:
            text += f"\n⚠️ <b>Нужен {level_req} уровень</b>\n"

    rows = []
    if item_type == "potion":
        rows.append([InlineKeyboardButton(
            text="🧪 Использовать",
            callback_data=f"use_item_{item_name}")])
    elif item_type in ("weapon", "armor", "shield", "accessory"):
        if can_use_item(u["class"], base_name) and u["level"] >= level_req:
            rows.append([InlineKeyboardButton(
                text="⚔️ Надеть",
                callback_data=f"equip_item_{item_name}")])
        else:
            rows.append([InlineKeyboardButton(
                text="❌ Нельзя надеть (класс/уровень)",
                callback_data="inv_noop")])

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
            text="🗑 Выбросить",
            callback_data=f"drop_item_{item_name}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад",
                                       callback_data="inv_menu")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "inv_noop")
async def inv_noop(c: CallbackQuery):
    await c.answer("Действие недоступно", show_alert=True)


# ================= ЭКИПИРОВАНО =================
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
    rows.append([InlineKeyboardButton(text="⬅️ В инвентарь",
                                       callback_data="inv_menu")])

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


# ================= МАТЕРИАЛЫ =================
@router.callback_query(F.data == "inv_materials")
async def inv_materials_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    text = "📦 <b>Материалы</b>\n\n"
    text += f"🔩 Железо: <b>{u.get('mat_iron', 0)}</b>\n"
    text += f"🧵 Кожа: <b>{u.get('mat_leather', 0)}</b>\n"
    text += f"✨ Магическая пыль: <b>{u.get('mat_dust', 0)}</b>\n"
    text += f"💎 Кристалл: <b>{u.get('mat_crystal', 0)}</b>\n\n"
    text += "<i>Используются в /craft (кузница).</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚒️ Кузница", callback_data="craft_open")],
        [InlineKeyboardButton(text="⬅️ В инвентарь", callback_data="inv_menu")],
    ])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


# ================= ЗАКРЫТЬ =================
@router.callback_query(F.data == "inv_close")
async def inv_close_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()
