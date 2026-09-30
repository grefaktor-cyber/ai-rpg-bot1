"""Кузница: крафт, разбор, улучшение."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import SHOP, CRAFT_RECIPES, MATERIAL_NAMES
from core.formulas import parse_item
from core.keyboards import main_kb, craft_kb


router = Router()


@router.message(Command("craft"))
@router.message(F.text == "⚒️ Кузница")
async def craft_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    text = (f"⚒️ <b>Кузница</b>\n\n"
            f"🔩 {u['mat_iron']} · 🧵 {u['mat_leather']} · ✨ {u['mat_dust']} · 💎 {u['mat_crystal']}\n\n"
            f"<b>Действия:</b>\n"
            f"/dismantle Название — разобрать\n"
            f"/upgrade Название — улучшить (+1..+3)\n\n"
            f"<b>Рецепты:</b>\n")
    for result, r in CRAFT_RECIPES.items():
        text += (f"• <b>{result}</b> ← {r['count']}× {r['base']} + "
                 f"{r['mat_count']}× {MATERIAL_NAMES[r['mat']]}\n")
    await m.answer(text, reply_markup=craft_kb(CRAFT_RECIPES),
                   parse_mode=ParseMode.HTML)


@router.message(Command("dismantle"))
async def dismantle_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /dismantle Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя разобрать."); return
    inv = await g.db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    await g.db.remove_item(m.from_user.id, item_name)
    itype = SHOP[base_name]["type"]
    yields = {"weapon": [("iron", 2), ("crystal", 1)],
              "armor": [("leather", 2), ("iron", 1)],
              "accessory": [("dust", 2), ("crystal", 1)]}[itype]
    lines = []
    for mat, amt in yields:
        amt += lvl
        await g.db.add_material(m.from_user.id, mat, amt)
        lines.append(f"• {MATERIAL_NAMES[mat]}: +{amt}")
    await m.answer(f"⚒️ Разобрано: <b>{item_name}</b>\n\n" + "\n".join(lines),
                   reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("upgrade"))
async def upgrade_cmd(m: Message):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /upgrade Название"); return
    item_name = parts[1].strip()
    base_name, lvl = parse_item(item_name)
    if base_name not in SHOP:
        await m.answer("❌ Нельзя улучшить."); return
    if lvl >= 3:
        await m.answer("❌ Максимум +3."); return
    inv = await g.db.get_inventory(m.from_user.id)
    if not any(i["item_name"] == item_name for i in inv):
        await m.answer("❌ Нет в инвентаре."); return
    mat_needed = (lvl + 1) * 3
    gold_needed = (lvl + 1) * 100
    itype = SHOP[base_name]["type"]
    mat = {"weapon": "iron", "armor": "leather", "accessory": "crystal"}[itype]
    u = await g.db.get_user(m.from_user.id)
    if u[f"mat_{mat}"] < mat_needed:
        await m.answer(f"❌ Нужно {mat_needed}× {MATERIAL_NAMES[mat]}"); return
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


@router.callback_query(F.data.startswith("craft_"))
async def craft_cb(c: CallbackQuery):
    result = c.data.replace("craft_", "")
    if result not in CRAFT_RECIPES:
        await c.answer("Нет"); return
    r = CRAFT_RECIPES[result]
    u = await g.db.get_user(c.from_user.id)
    inv = await g.db.get_inventory(c.from_user.id)
    inv_names = [i["item_name"] for i in inv]
    have_base = inv_names.count(r["base"])
    have_mat = u[f"mat_{r['mat']}"]
    if have_base < r["count"]:
        await c.answer(f"Нужно {r['count']}× {r['base']} (есть {have_base})",
                       show_alert=True); return
    if have_mat < r["mat_count"]:
        await c.answer(f"Нужно {r['mat_count']}× {MATERIAL_NAMES[r['mat']]}",
                       show_alert=True); return
    for _ in range(r["count"]):
        await g.db.remove_item(c.from_user.id, r["base"])
    await g.db.spend_material(c.from_user.id, r["mat"], r["mat_count"])
    await g.db.add_item(c.from_user.id, result)
    await c.answer(f"✅ Создано: {result}")
    await c.message.answer(f"⚒️ Ты создал <b>{result}</b>!", parse_mode=ParseMode.HTML)
    if await g.db.add_achievement(c.from_user.id, "crafter"):
        await c.message.answer("🏆 Достижение: ⚒️ Кузнец", parse_mode=ParseMode.HTML)
    await g.db.progress_quest(c.from_user.id, "craft_items", 1)
