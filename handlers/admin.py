"""Админ-команды."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.formulas import calc_max_hp
from core.texts import ADMIN_HELP_TEXT
from config import ADMIN_IDS
import world as W

router = Router()


def _is_admin(uid):
    return uid in ADMIN_IDS


@router.message(Command("admin_help"))
async def admin_help(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    await m.answer(ADMIN_HELP_TEXT, parse_mode=ParseMode.HTML)


@router.message(Command("admin_reset"))
async def admin_reset(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    u = await g.db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await g.db.update_hp_max(m.from_user.id, nm, nm)
    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET requests_today=0, energy=energy_max, "
            "last_energy_regen=NOW() WHERE user_id=$1",
            m.from_user.id
        )
    await m.answer(f"🛠 HP: {nm}/{nm} · Энергия: {u.get('energy_max', 20)}",
                   parse_mode=ParseMode.HTML)


@router.message(Command("admin_gold"))
async def admin_gold(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("Использование: /admin_gold 5000"); return
    try:
        amount = int(parts[1])
    except ValueError:
        await m.answer("Число."); return
    await g.db.add_gold(m.from_user.id, amount)
    u = await g.db.get_user(m.from_user.id)
    await m.answer(f"🛠 {amount:+d}. Теперь: {u['gold']}💰")


@router.message(Command("admin_hp"))
async def admin_hp(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    u = await g.db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await g.db.update_hp_max(m.from_user.id, nm, nm)
    await m.answer(f"🛠 HP: {nm}/{nm}")


@router.message(Command("admin_levelup"))
async def admin_levelup(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    await g.db.add_xp(m.from_user.id, 999999)
    u = await g.db.get_user(m.from_user.id)
    nm = calc_max_hp(u)
    await g.db.update_hp_max(m.from_user.id, nm, nm)
    await m.answer(f"🛠 Ур.: {u['level']}. HP: {nm}/{nm}")


@router.message(Command("admin_endcombat"))
async def admin_endcombat(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    combat = await g.db.get_combat(m.from_user.id)
    if combat and combat.get("is_pvp"):
        opp = combat["opponent_id"]
        await g.db.end_combat(opp)
        try:
            await g.bot.send_message(opp, "⚔️ Дуэль отменена.")
        except Exception:
            pass
    await g.db.end_combat(m.from_user.id)
    u = await g.db.get_user(m.from_user.id)
    if u.get("dungeon_id"):
        await g.db.exit_dungeon(m.from_user.id)
    await m.answer("🛠 Бой завершён.")


@router.message(Command("admin_stats"))
async def admin_stats(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    u = await g.db.get_user(m.from_user.id)
    text = "\n".join(f"<code>{k}</code> = {v}" for k, v in u.items())
    await m.answer(f"🛠 <b>Строка БД</b>\n\n{text}", parse_mode=ParseMode.HTML)


@router.message(Command("admin_give_item"))
async def admin_give_item(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer("Использование: /admin_give_item Железный меч"); return
    await g.db.add_item(m.from_user.id, parts[1].strip())
    await m.answer(f"🛠 Выдано: {parts[1].strip()}")


@router.message(Command("admin_mats"))
async def admin_mats(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    for mat in ("iron", "leather", "dust", "crystal"):
        await g.db.add_material(m.from_user.id, mat, 10)
    await m.answer("🛠 +10 всех материалов.")


@router.message(Command("admin_resetquests"))
async def admin_resetquests(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    async with g.db.pool.acquire() as conn:
        await conn.execute("DELETE FROM daily_quests WHERE user_id=$1", m.from_user.id)
    await m.answer("🛠 Квесты сброшены.")


@router.message(Command("admin_resettutorial"))
async def admin_resettutorial(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    async with g.db.pool.acquire() as conn:
        await conn.execute("DELETE FROM tutorial_progress WHERE user_id=$1", m.from_user.id)
    await m.answer("🛠 Туториал сброшен.")


@router.message(Command("admin_teleport"))
async def admin_teleport(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        codes = ", ".join(W.LOCATIONS.keys())
        await m.answer(f"Коды: {codes}"); return
    code = parts[1].strip().lower()
    if code not in W.LOCATIONS:
        await m.answer("Неизвестный код."); return
    loc = W.get_location(code)
    await g.db.set_location_code(m.from_user.id, code)
    await g.db.add_location(m.from_user.id, loc["name"])
    await m.answer(f"🛠 Перемещён в: {loc['name']}")


@router.message(Command("admin_event"))
async def admin_event(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    parts = m.text.split()
    if len(parts) < 2:
        codes = ", ".join(W.LOCATIONS.keys())
        await m.answer(f"Использование: /admin_event <code>\nКоды: {codes}")
        return
    loc_code = parts[1].strip().lower()
    if loc_code not in W.LOCATIONS:
        await m.answer("Неизвестная локация."); return
    tpl = random.choice(W.EVENT_TEMPLATES)
    await g.db.create_world_event(
        loc_code, tpl["code"], tpl["name"], tpl["desc"],
        tpl["duration_min"], tpl["xp_mult"], tpl["gold_mult"],
        tpl["spawn_mult"], tpl.get("enemy_dmg_mult", 1.0)
    )
    loc_name = W.get_location(loc_code)["name"]
    await m.answer(f"🛠 Событие {tpl['name']} в {loc_name}.")


@router.message(Command("admin_spawn_event"))
async def admin_spawn_event(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    loc_code = random.choice(list(W.LOCATIONS.keys()))
    tpl = random.choice(W.EVENT_TEMPLATES)
    await g.db.create_world_event(
        loc_code, tpl["code"], tpl["name"], tpl["desc"],
        tpl["duration_min"], tpl["xp_mult"], tpl["gold_mult"],
        tpl["spawn_mult"], tpl.get("enemy_dmg_mult", 1.0)
    )
    loc_name = W.get_location(loc_code)["name"]
    await m.answer(f"🛠 Событие {tpl['name']} в {loc_name}.")
    
    
@router.message(Command("admin_premium"))
async def admin_premium(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    u = await g.db.get_user(m.from_user.id)
    new_val = 0 if u.get("is_premium") else 1
    await g.db.set_premium(m.from_user.id, new_val)
    await m.answer(f"🛠 Премиум: {'ВКЛ' if new_val else 'ВЫКЛ'}")



# ================= ПРЕМИУМ-РАСЫ И КЛАССЫ =================
@router.message(Command("admin_unlock_races"))
async def admin_unlock_races(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_RACES
    for code in EXCLUSIVE_RACES:
        await g.db.unlock_premium_race(m.from_user.id, code)
    names = ", ".join(r["name"] for r in EXCLUSIVE_RACES.values())
    await m.answer(
        f"🛠 Открыты все премиум-расы: <b>{names}</b>\n\n"
        f"Проверь /newchar → выбор расы.",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_unlock_classes"))
async def admin_unlock_classes(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_CLASSES
    for code in EXCLUSIVE_CLASSES:
        await g.db.unlock_premium_class(m.from_user.id, code)
    names = ", ".join(c["name"] for c in EXCLUSIVE_CLASSES.values())
    await m.answer(
        f"🛠 Открыты все премиум-классы: <b>{names}</b>\n\n"
        f"Проверь /newchar → выбор класса.",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_unlock_items"))
async def admin_unlock_items(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_ITEMS
    for code in EXCLUSIVE_ITEMS:
        await g.db.add_item(m.from_user.id, code)
    names = ", ".join(EXCLUSIVE_ITEMS.keys())
    await m.answer(
        f"🛠 Выданы все премиум-предметы:\n<code>{names}</code>\n\n"
        f"Проверь /inventory.",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_unlock_all"))
async def admin_unlock_all(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return

    from core.premium import EXCLUSIVE_RACES, EXCLUSIVE_CLASSES, EXCLUSIVE_ITEMS, EXCLUSIVE_PETS

    # Расы
    for code in EXCLUSIVE_RACES:
        await g.db.unlock_premium_race(m.from_user.id, code)

    # Классы
    for code in EXCLUSIVE_CLASSES:
        await g.db.unlock_premium_class(m.from_user.id, code)

    # Предметы
    for code in EXCLUSIVE_ITEMS:
        await g.db.add_item(m.from_user.id, code)

    # Питомцы
    for code, pet in EXCLUSIVE_PETS.items():
        try:
            await g.db.add_pet(m.from_user.id, code, pet.get("name", code))
        except Exception:
            pass

    # Премиум навсегда
    await g.db.set_premium(m.from_user.id, 1)

    await m.answer(
        "🛠 <b>ВСЁ ОТКРЫТО!</b>\n\n"
        f"🎭 Расы: {len(EXCLUSIVE_RACES)}\n"
        f"🛡 Классы: {len(EXCLUSIVE_CLASSES)}\n"
        f"⚔️ Предметы: {len(EXCLUSIVE_ITEMS)}\n"
        f"🐉 Питомцы: {len(EXCLUSIVE_PETS)}\n\n"
        "Проверь:\n"
        "• /newchar → расы и классы\n"
        "• /inventory → предметы\n"
        "• /pet → питомцы",
        parse_mode=ParseMode.HTML)
