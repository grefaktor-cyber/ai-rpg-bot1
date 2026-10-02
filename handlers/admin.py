"""Админ-команды."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.formulas import calc_max_hp, calc_max_mp
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


# ================= УРОВЕНЬ + ОЧКИ УМЕНИЙ =================
@router.message(Command("admin_levelup"))
async def admin_levelup(m: Message):
    """+1 уровень и +1 очко умений."""
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    uid = m.from_user.id
    u = await g.db.get_user(uid)
    new_level = u["level"] + 1

    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET level=$1, xp=0, skill_points=skill_points+1 "
            "WHERE user_id=$2",
            new_level, uid
        )

    u2 = await g.db.get_user(uid)
    nm = calc_max_hp(u2)
    nmp = calc_max_mp(u2)
    await g.db.update_hp_max(uid, nm, nm)
    await g.db.update_mp(uid, nmp)

    await m.answer(
        f"🛠 <b>Уровень {new_level}</b>\n"
        f"HP: {nm}/{nm} · MP: {nmp}/{nmp}\n"
        f"🎯 Очки умений: <b>{u2['skill_points']}</b>",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_setlevel"))
async def admin_setlevel(m: Message):
    """Установить конкретный уровень и выдать столько же очков умений."""
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("Использование: <code>/admin_setlevel 20</code>",
                       parse_mode=ParseMode.HTML)
        return
    try:
        lvl = int(parts[1])
    except ValueError:
        await m.answer("Число нужно."); return
    if lvl < 1 or lvl > 100:
        await m.answer("От 1 до 100."); return

    uid = m.from_user.id
    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET level=$1, xp=0, skill_points=$1 "
            "WHERE user_id=$2",
            lvl, uid
        )

    u = await g.db.get_user(uid)
    nm = calc_max_hp(u)
    nmp = calc_max_mp(u)
    await g.db.update_hp_max(uid, nm, nm)
    await g.db.update_mp(uid, nmp)

    await m.answer(
        f"🛠 <b>Уровень установлен: {lvl}</b>\n"
        f"HP: {nm}/{nm} · MP: {nmp}/{nmp}\n"
        f"🎯 Очки умений: <b>{u['skill_points']}</b>",
        parse_mode=ParseMode.HTML)


# ================= ОСТАЛЬНЫЕ =================
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
    items = list(u.items())
    text = "\n".join(f"<code>{k}</code> = {v}" for k, v in items)
    if len(text) > 3800:
        text = text[:3800] + "\n<i>...обрезано</i>"
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
@router.message(Command("admin_check_races"))
async def admin_check_races(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    uid = m.from_user.id
    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, char_name, is_premium, "
            "unlocked_premium_races, unlocked_premium_classes "
            "FROM users WHERE user_id=$1", uid
        )
    if not row:
        await m.answer("❌ Нет строки в БД. Напиши /start сначала.")
        return
    await m.answer(
        f"🛠 <b>Проверка БД</b>\n\n"
        f"user_id: <code>{row['user_id']}</code>\n"
        f"char_name: <code>{row['char_name']}</code>\n"
        f"is_premium: <code>{row['is_premium']}</code>\n"
        f"premium_races: <code>{row['unlocked_premium_races']}</code>\n"
        f"premium_classes: <code>{row['unlocked_premium_classes']}</code>",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_set_races"))
async def admin_set_races(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_RACES, EXCLUSIVE_CLASSES
    import json

    races = list(EXCLUSIVE_RACES.keys())
    classes = list(EXCLUSIVE_CLASSES.keys())

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id=$1", m.from_user.id
        )
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, last_reset, last_energy_regen) "
                "VALUES ($1, $2, NOW())",
                m.from_user.id, str(__import__('datetime').date.today())
            )
        await conn.execute(
            "UPDATE users SET "
            "unlocked_premium_races=$1, "
            "unlocked_premium_classes=$2, "
            "is_premium=1 "
            "WHERE user_id=$3",
            json.dumps(races), json.dumps(classes), m.from_user.id
        )

    await m.answer(
        f"🛠 <b>ФОРС-ЗАПИСЬ</b>\n\n"
        f"🎭 Расы: <code>{races}</code>\n"
        f"🛡 Классы: <code>{classes}</code>\n\n"
        f"Проверь: /admin_check_races\n"
        f"Потом: /newchar",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_unlock_races"))
async def admin_unlock_races(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_RACES
    ok_count = 0
    for code in EXCLUSIVE_RACES:
        res = await g.db.unlock_premium_race(m.from_user.id, code)
        if res:
            ok_count += 1
    names = ", ".join(r["name"] for r in EXCLUSIVE_RACES.values())
    await m.answer(
        f"🛠 Открыты премиум-расы ({ok_count}/{len(EXCLUSIVE_RACES)}): "
        f"<b>{names}</b>\n\n"
        f"Проверь /newchar → выбор расы.\n"
        f"<i>Если не появились — /admin_check_races</i>",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_unlock_classes"))
async def admin_unlock_classes(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    from core.premium import EXCLUSIVE_CLASSES
    ok_count = 0
    for code in EXCLUSIVE_CLASSES:
        res = await g.db.unlock_premium_class(m.from_user.id, code)
        if res:
            ok_count += 1
    names = ", ".join(c["name"] for c in EXCLUSIVE_CLASSES.values())
    await m.answer(
        f"🛠 Открыты премиум-классы ({ok_count}/{len(EXCLUSIVE_CLASSES)}): "
        f"<b>{names}</b>\n\n"
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

    uid = m.from_user.id

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id=$1", uid
        )
        if not row:
            await m.answer("❌ Сначала /start — создай игрока.")
            return

    races_ok = 0
    for code in EXCLUSIVE_RACES:
        if await g.db.unlock_premium_race(uid, code):
            races_ok += 1

    classes_ok = 0
    for code in EXCLUSIVE_CLASSES:
        if await g.db.unlock_premium_class(uid, code):
            classes_ok += 1

    for code in EXCLUSIVE_ITEMS:
        await g.db.add_item(uid, code)

    for code, pet in EXCLUSIVE_PETS.items():
        try:
            await g.db.add_pet(uid, code, pet.get("name", code))
        except Exception:
            pass

    await g.db.set_premium(uid, 1)

    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT unlocked_premium_races, unlocked_premium_classes "
            "FROM users WHERE user_id=$1", uid
        )

    races_db = row["unlocked_premium_races"] if row else "?"
    classes_db = row["unlocked_premium_classes"] if row else "?"

    await m.answer(
        f"🛠 <b>ВСЁ ОТКРЫТО!</b>\n\n"
        f"🎭 Расы: {races_ok}/{len(EXCLUSIVE_RACES)}\n"
        f"🛡 Классы: {classes_ok}/{len(EXCLUSIVE_CLASSES)}\n"
        f"⚔️ Предметы: {len(EXCLUSIVE_ITEMS)}\n"
        f"🐉 Питомцы: {len(EXCLUSIVE_PETS)}\n\n"
        f"<b>В БД сейчас:</b>\n"
        f"races: <code>{races_db}</code>\n"
        f"classes: <code>{classes_db}</code>\n\n"
        f"Проверь /newchar",
        parse_mode=ParseMode.HTML)


# ================= СПАВН БОССА (ТЕСТ) =================
@router.message(Command("admin_spawn_boss"))
async def admin_spawn_boss(m: Message):
    """Форс-спавн обычного босса.

    /admin_spawn_boss                    — случайный
    /admin_spawn_boss ancient_dragon     — конкретный
    /admin_spawn_boss ancient_dragon cave — + локация
    """
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return

    parts = m.text.split()
    boss_code = parts[1] if len(parts) > 1 else None
    location_code = parts[2] if len(parts) > 2 else None

    try:
        from services.world_boss_service import force_spawn_boss
    except ImportError:
        await m.answer("⚠️ В services/world_boss_service.py нет force_spawn_boss.")
        return

    result = await force_spawn_boss(boss_code, location_code, notify=False)

    if "error" in result:
        err_text = f"❌ {result['error']}\n\n"
        if "available" in result:
            err_text += "<b>Доступные коды:</b>\n"
            for code in result["available"]:
                err_text += f"• <code>{code}</code>\n"
        await m.answer(err_text, parse_mode=ParseMode.HTML)
        return

    await m.answer(
        f"🛠 <b>Босс заспавнен!</b>\n\n"
        f"🐉 <b>{result['boss_name']}</b> (ур. {result['boss_level']})\n"
        f"❤️ HP: <b>{result['hp']}</b>\n"
        f"⚔️ Урон: ~{result['attack_dmg']} ({result['dmg_type']})\n"
        f"📍 Локация: <b>{result['location_name']}</b>\n"
        f"   код: <code>{result['location_code']}</code>\n\n"
        f"<b>Что дальше:</b>\n"
        f"1. <code>/admin_teleport {result['location_code']}</code>\n"
        f"2. В боте напиши <code>/boss</code>\n"
        f"3. Жми «⚔️ Атаковать»",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_spawn_raid"))
async def admin_spawn_raid(m: Message):
    """Форс-спавн РЕЙД-босса (требует 2+ игрока).

    /admin_spawn_raid                      — случайный рейд-босс
    /admin_spawn_raid abyss_lord           — конкретный
    /admin_spawn_raid abyss_lord abyss     — + локация
    """
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return

    parts = m.text.split()
    boss_code = parts[1] if len(parts) > 1 else None
    location_code = parts[2] if len(parts) > 2 else None

    try:
        from services.world_boss_service import (
            force_spawn_boss, RAID_BOSSES,
        )
    except ImportError:
        await m.answer("⚠️ В services/world_boss_service.py нет RAID_BOSSES.")
        return

    if boss_code is None:
        import random as _r
        boss_code = _r.choice(list(RAID_BOSSES.keys()))

    if boss_code not in RAID_BOSSES:
        avail = ", ".join(f"<code>{c}</code>" for c in RAID_BOSSES)
        await m.answer(
            f"❌ Рейд-босс «{boss_code}» не найден.\n\n"
            f"<b>Доступные:</b> {avail}",
            parse_mode=ParseMode.HTML)
        return

    result = await force_spawn_boss(boss_code, location_code, notify=True)

    if "error" in result:
        err_text = f"❌ {result['error']}\n\n"
        if "available" in result:
            err_text += "<b>Доступные коды:</b>\n"
            for code in result["available"]:
                err_text += f"• <code>{code}</code>\n"
        await m.answer(err_text, parse_mode=ParseMode.HTML)
        return

    await m.answer(
        f"🛠 <b>⚔️ РЕЙД-БОСС заспавнен!</b>\n\n"
        f"👹 <b>{result['boss_name']}</b> (ур. {result['boss_level']})\n"
        f"❤️ HP: <b>{result['hp']}</b>\n"
        f"⚔️ Урон: ~{result['attack_dmg']} ({result['dmg_type']})\n"
        f"👥 Требуется: <b>{result['min_players']}+ игрока</b>\n"
        f"📍 Локация: <b>{result['location_name']}</b>\n"
        f"   код: <code>{result['location_code']}</code>\n\n"
        f"<i>Все игроки получили уведомление.</i>\n\n"
        f"<b>Что дальше:</b>\n"
        f"1. <code>/admin_teleport {result['location_code']}</code>\n"
        f"2. Позови друга с собой\n"
        f"3. В боте напиши <code>/boss</code>\n"
        f"4. Жми «⚔️ Атаковать»",
        parse_mode=ParseMode.HTML)
