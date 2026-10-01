"""Кузница: крафт, разбор, улучшение, рецепты."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.equipment import SHOP
from core.crafting import RECIPES, get_recipe
from core.formulas import parse_item
from core.keyboards import main_kb


router = Router()


# ================= МЕНЮ КУЗНИЦЫ =================
@router.message(Command("craft"))
@router.message(F.text == "⚒️ Кузница")
async def craft_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return

    rare = await g.db.get_rare_materials(m.from_user.id)
    rare_str = " · ".join(f"{k}: {v}" for k, v in rare.items()) if rare else "<i>пусто</i>"

    text = (f"⚒️ <b>Кузница</b>\n\n"
            f"<b>Обычные материалы:</b>\n"
            f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · ✨ {u['mat_dust']} · 💎 {u['mat_crystal']}\n\n"
            f"<b>Редкие материалы:</b>\n{rare_str}\n\n"
            f"<b>Разделы:</b>")

    rows = [
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="craft_recipes")],
        [InlineKeyboardButton(text="🔨 Разобрать", callback_data="craft_dismantle_menu")],
        [InlineKeyboardButton(text="⬆️ Улучшить (+1..+3)",
                              callback_data="craft_upgrade_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="craft_close")],
    ]
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "craft_close")
async def craft_close(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


# ================= РЕЦЕПТЫ =================
@router.callback_query(F.data == "craft_recipes")
async def craft_recipes(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    inv = await g.db.get_inventory(c.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    rare = await g.db.get_rare_materials(c.from_user.id)

    text = "📜 <b>Рецепты</b>\n\n"
    rows = []

    # Сортируем по грейду
    for result, r in sorted(RECIPES.items(), key=lambda x: x[1].get("grade", "Z")):
        base = r["base"]
        cnt_base = r.get("count_base", 1)
        have_base = inv_names.count(base)

        mats = r.get("materials", {})
        rare_mats = r.get("rare", {})

        # Проверка
        can_craft = have_base >= cnt_base
        for mat, amt in mats.items():
            if u.get(f"mat_{mat}", 0) < amt:
                can_craft = False
        for mat, amt in rare_mats.items():
            if rare.get(mat, 0) < amt:
                can_craft = False

        mark = "✅" if can_craft else "🔒"
        grade = r.get("grade", "?")
        chance = int(r.get("chance", 1.0) * 100)

        text += f"{mark} <b>{result}</b> [{grade}] ({chance}%)\n"
        text += f"   📦 {cnt_base}× {base} (у тебя {have_base})\n"
        for mat, amt in mats.items():
            have = u.get(f"mat_{mat}", 0)
            text += f"   🔩 {mat}: {have}/{amt}\n"
        for mat, amt in rare_mats.items():
            have = rare.get(mat, 0)
            text += f"   💠 {mat}: {have}/{amt}\n"
        text += "\n"

        if can_craft:
            rows.append([InlineKeyboardButton(
                text=f"⚒️ Создать: {result} ({chance}%)",
                callback_data=f"craft_do_{result}"
            )])

    if not rows:
        text += "<i>Пока ни один рецепт не доступен.</i>"
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="craft_back")])

    if len(text) > 3500:
        text = text[:3500] + "\n<i>...обрезано</i>"

    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data == "craft_back")
async def craft_back(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    rare = await g.db.get_rare_materials(c.from_user.id)
    rare_str = " · ".join(f"{k}: {v}" for k, v in rare.items()) if rare else "<i>пусто</i>"

    text = (f"⚒️ <b>Кузница</b>\n\n"
            f"<b>Обычные материалы:</b>\n"
            f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · ✨ {u['mat_dust']} · 💎 {u['mat_crystal']}\n\n"
            f"<b>Редкие материалы:</b>\n{rare_str}\n\n"
            f"<b>Разделы:</b>")
    rows = [
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="craft_recipes")],
        [InlineKeyboardButton(text="🔨 Разобрать", callback_data="craft_dismantle_menu")],
        [InlineKeyboardButton(text="⬆️ Улучшить (+1..+3)",
                              callback_data="craft_upgrade_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="craft_close")],
    ]
    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("craft_do_"))
async def craft_do(c: CallbackQuery):
    import random
    result = c.data.replace("craft_do_", "")
    r = get_recipe(result)
    if not r:
        await c.answer("Рецепт не найден"); return

    u = await g.db.get_user(c.from_user.id)
    inv = await g.db.get_inventory(c.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    rare = await g.db.get_rare_materials(c.from_user.id)

    # Проверки
    base = r["base"]
    cnt_base = r.get("count_base", 1)
    if inv_names.count(base) < cnt_base:
        await c.answer(f"❌ Нужно {cnt_base}× {base}", show_alert=True); return
    for mat, amt in r.get("materials", {}).items():
        if u.get(f"mat_{mat}", 0) < amt:
            await c.answer(f"❌ Нужно {mat}: {amt}", show_alert=True); return
    for mat, amt in r.get("rare", {}).items():
        if rare.get(mat, 0) < amt:
            await c.answer(f"❌ Нужно редких: {mat}: {amt}", show_alert=True); return

    # Забираем
    for _ in range(cnt_base):
        await g.db.remove_item(c.from_user.id, base)
    for mat, amt in r.get("materials", {}).items():
        await g.db.spend_material(c.from_user.id, mat, amt)
    for mat, amt in r.get("rare", {}).items():
        await g.db.spend_rare_material(c.from_user.id, mat, amt)

    # Попытка
    if random.random() <= r.get("chance", 1.0):
        await g.db.add_item(c.from_user.id, result)
        await c.answer("✅ Успех!")
        await c.message.answer(
            f"⚒️ <b>Крафт успешен!</b>\n\nПолучено: <b>{result}</b>",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    else:
        await c.answer("❌ Провал!")
        await c.message.answer(
            f"💔 <b>Крафт провалился!</b>\n\n"
            f"Рецепт сгорел: <b>{result}</b>\n"
            f"Материалы потрачены.",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)

    await craft_back(c)


# ================= РАЗБОР =================
@router.callback_query(F.data == "craft_dismantle_menu")
async def craft_dismantle_menu(c: CallbackQuery):
    inv = await g.db.get_inventory(c.from_user.id)
    items_to_show = []
    for it in inv:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP and SHOP[name].get("type") != "potion":
            if SHOP[name].get("premium"):
                continue
            items_to_show.append(it["item_name"])

    text = "🔨 <b>Разобрать предмет</b>\n\n"
    rows = []
    if not items_to_show:
        text += "<i>Нечего разбирать.</i>"
    else:
        text += "Выбери предмет:"
        for n in items_to_show[:12]:
            rows.append([InlineKeyboardButton(
                text=f"🔨 {n}",
                callback_data=f"disasm_{n}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="craft_back")])

    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("disasm_"))
async def disasm_cb(c: CallbackQuery):
    item_name = c.data.replace("disasm_", "")
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await c.answer("Нельзя разобрать"); return
    inv = await g.db.get_inventory(c.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await c.answer("Нет в инвентаре"); return
    await g.db.remove_item(c.from_user.id, item_name)
    itype = SHOP[base_name].get("type", "weapon")
    yields_map = {
        "weapon": [("iron", 2), ("crystal", 1)],
        "armor": [("leather", 2), ("iron", 1)],
        "shield": [("iron", 2), ("crystal", 1)],
        "accessory": [("dust", 2), ("crystal", 1)],
    }
    yields = yields_map.get(itype, [("iron", 1)])
    lines = []
    for mat, amt in yields:
        amt += lvl
        await g.db.add_material(c.from_user.id, mat, amt)
        lines.append(f"• {mat}: +{amt}")
    await c.answer("Разобрано")
    await c.message.answer(
        f"⚒️ <b>Разобрано:</b> {item_name}\n\n" + "\n".join(lines),
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)


# ================= УЛУЧШЕНИЕ =================
@router.callback_query(F.data == "craft_upgrade_menu")
async def craft_upgrade_menu(c: CallbackQuery):
    inv = await g.db.get_inventory(c.from_user.id)
    items = []
    for it in inv:
        name, lvl = parse_item(it["item_name"])
        if name in SHOP and SHOP[name].get("type") != "potion" and lvl < 3:
            if SHOP[name].get("premium"):
                continue
            items.append(it["item_name"])

    text = "⬆️ <b>Улучшить предмет</b> (+1..+3)\n\n"
    rows = []
    if not items:
        text += "<i>Нечего улучшать.</i>"
    else:
        text += "Выбери предмет:"
        for n in items[:12]:
            rows.append([InlineKeyboardButton(
                text=f"⬆️ {n}",
                callback_data=f"upgrade_{n}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="craft_back")])

    try:
        await c.message.edit_text(text,
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode=ParseMode.HTML)
    await c.answer()


@router.callback_query(F.data.startswith("upgrade_"))
async def upgrade_cb(c: CallbackQuery):
    item_name = c.data.replace("upgrade_", "")
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await c.answer("Нельзя улучшить"); return
    if lvl >= 3:
        await c.answer("Максимум +3"); return
    inv = await g.db.get_inventory(c.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await c.answer("Нет в инвентаре"); return
    mat_needed = (lvl + 1) * 3
    gold_needed = (lvl + 1) * 100
    itype = SHOP[base_name].get("type", "weapon")
    mat = {"weapon": "iron", "armor": "leather", "shield": "iron",
           "accessory": "crystal"}.get(itype, "iron")
    u = await g.db.get_user(c.from_user.id)
    if u.get(f"mat_{mat}", 0) < mat_needed:
        await c.answer(f"❌ Нужно {mat_needed}× {mat}", show_alert=True); return
    if u["gold"] < gold_needed:
        await c.answer(f"❌ Нужно {gold_needed}💰", show_alert=True); return
    await g.db.spend_material(c.from_user.id, mat, mat_needed)
    await g.db.spend_gold(c.from_user.id, gold_needed)
    await g.db.remove_item(c.from_user.id, item_name)
    new_name = f"{base_name}+{lvl + 1}"
    await g.db.add_item(c.from_user.id, new_name)
    await c.answer("Улучшено!")
    await c.message.answer(
        f"🔨 <b>{item_name}</b> → <b>{new_name}</b>",
        reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(c.from_user.id, "upgrader"):
        await c.message.answer("🏆 Достижение: 🔨 Улучшатель",
                                parse_mode=ParseMode.HTML)


# ================= СТАРЫЕ КОМАНДЫ (совместимость) =================
@router.message(Command("dismantle"))
async def dismantle_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /dismantle Название"); return
    item_name = parts[1].strip()
    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    from core.fuzzy import find_inventory_item
    exact, _ = find_inventory_item(item_name, inv_names)
    item_name = exact if exact else item_name
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя разобрать."); return
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    await g.db.remove_item(m.from_user.id, item_name)
    itype = SHOP[base_name].get("type", "weapon")
    yields_map = {
        "weapon": [("iron", 2), ("crystal", 1)],
        "armor": [("leather", 2), ("iron", 1)],
        "shield": [("iron", 2), ("crystal", 1)],
        "accessory": [("dust", 2), ("crystal", 1)],
    }
    yields = yields_map.get(itype, [("iron", 1)])
    lines = []
    for mat, amt in yields:
        amt += lvl
        await g.db.add_material(m.from_user.id, mat, amt)
        lines.append(f"• {mat}: +{amt}")
    await m.answer(f"⚒️ Разобрано: <b>{item_name}</b>\n\n" + "\n".join(lines),
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("upgrade"))
async def upgrade_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /upgrade Название"); return
    item_name = parts[1].strip()
    inv = await g.db.get_inventory(m.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    from core.fuzzy import find_inventory_item
    exact, _ = find_inventory_item(item_name, inv_names)
    item_name = exact if exact else item_name
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя улучшить."); return
    if lvl >= 3:
        await m.answer("❌ Максимум +3."); return
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    mat_needed = (lvl + 1) * 3
    gold_needed = (lvl + 1) * 100
    itype = SHOP[base_name].get("type", "weapon")
    mat = {"weapon": "iron", "armor": "leather", "shield": "iron",
           "accessory": "crystal"}.get(itype, "iron")
    u = await g.db.get_user(m.from_user.id)
    if u.get(f"mat_{mat}", 0) < mat_needed:
        await m.answer(f"❌ Нужно {mat_needed}× {mat}"); return
    if u["gold"] < gold_needed:
        await m.answer(f"❌ Нужно {gold_needed}💰"); return
    await g.db.spend_material(m.from_user.id, mat, mat_needed)
    await g.db.spend_gold(m.from_user.id, gold_needed)
    await g.db.remove_item(m.from_user.id, item_name)
    new_name = f"{base_name}+{lvl + 1}"
    await g.db.add_item(m.from_user.id, new_name)
    await m.answer(f"🔨 <b>{item_name}</b> → <b>{new_name}</b>",
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(m.from_user.id, "upgrader"):
        await m.answer("🏆 Достижение: 🔨 Улучшатель", parse_mode=ParseMode.HTML)
