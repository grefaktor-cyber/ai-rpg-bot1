"""Создание героя + основной обработчик (свободный текст → GigaChat)."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import (
    RACES, CLASSES, FACTIONS, ACHIEVEMENTS, MATERIAL_NAMES, classes_for_race,
)
from core.formulas import (
    calc_stats, effective_stats, calc_max_hp, calc_max_mp, faction_mult,
)
from core.keyboards import (
    main_kb, race_selection_kb, faction_selection_kb, pvp_kb, combat_kb,
)
from core.texts import EXCLUDE_FROM_AI
from config import ADMIN_IDS, AI_MARKER
from handlers.onboarding import run_tutorial
from services.combat_service import start_combat_from_ai
import world as W
import ai

router = Router()


async def _show_race(m):
    await g.bot.send_message(m.chat.id, "🧝 <b>Выбери расу:</b>",
                             reply_markup=race_selection_kb(RACES),
                             parse_mode=ParseMode.HTML)


async def _show_class(m, race_code):
    classes = classes_for_race(race_code)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = [[InlineKeyboardButton(
        text=f"{cl['name']} — {cl['desc']}",
        callback_data=f"class_{code}"
    )] for code, cl in classes.items()]
    await g.bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                             parse_mode=ParseMode.HTML)


async def _show_faction(m):
    await g.bot.send_message(m.chat.id, "🏛 <b>Выбери фракцию:</b>",
                             reply_markup=faction_selection_kb(FACTIONS),
                             parse_mode=ParseMode.HTML)


async def check_achievements(uid, user):
    new = []
    if user["action_count"] >= 1:
        if await g.db.add_achievement(uid, "first_step"): new.append("first_step")
    locs = await g.db.get_locations(uid)
    if len(locs) >= 5:
        if await g.db.add_achievement(uid, "explorer_5"): new.append("explorer_5")
    if len(locs) >= 10:
        if await g.db.add_achievement(uid, "explorer_10"): new.append("explorer_10")
    if len(locs) >= len(W.LOCATIONS):
        if await g.db.add_achievement(uid, "explorer_all"): new.append("explorer_all")
    items = await g.db.get_inventory(uid)
    if len(items) >= 5:
        if await g.db.add_achievement(uid, "collector_5"): new.append("collector_5")
    if user["level"] >= 5:
        if await g.db.add_achievement(uid, "level_5"): new.append("level_5")
    if user["level"] >= 10:
        if await g.db.add_achievement(uid, "level_10"): new.append("level_10")
    if user["level"] >= 20:
        if await g.db.add_achievement(uid, "level_20"): new.append("level_20")
    if user["referral_count"] >= 3:
        if await g.db.add_achievement(uid, "referral_3"): new.append("referral_3")
    if user["daily_streak"] >= 7:
        if await g.db.add_achievement(uid, "daily_7"): new.append("daily_7")
    if user["gold"] >= 1000:
        if await g.db.add_achievement(uid, "rich"): new.append("rich")
    return new


@router.message(F.text, ~F.text.in_(EXCLUDE_FROM_AI))
async def handle(m: Message):
    uid = m.from_user.id
    user = await g.db.get_user(uid, m.from_user.username or "")

    if not user["consent_given"]:
        await m.answer("⚠️ Сначала /start"); return
    if not user["race"] or user["race"] not in RACES:
        await _show_race(m); return
    if not user["class"] or user["class"] not in CLASSES:
        await _show_class(m, user["race"]); return
    if not user["faction"]:
        await _show_faction(m); return

    # Создание героя
    if not user["char_name"]:
        name = m.text.strip()[:20]
        if len(name) < 2:
            await m.answer("✏️ Имя 2–20 символов:"); return
        stats = calc_stats(user["race"], user["class"])
        user_tmp = dict(user)
        for k in ["str", "dex", "con", "int", "wit", "men"]:
            user_tmp[f"stat_{k}"] = stats[k]
        user_tmp["level"] = 1
        hp = calc_max_hp(user_tmp)
        mp = calc_max_mp(user_tmp)
        await g.db.set_char(uid, name, stats, hp)
        await g.db.update_stats(uid, stats, hp, mp)
        await m.answer(
            f"🎉 <b>Герой создан!</b>\n\n"
            f"<b>{name}</b>\n"
            f"{RACES[user['race']]['name']} · {CLASSES[user['class']]['name']}\n"
            f"{FACTIONS[user['faction']]['name']}\n\n"
            f"STR {stats['str']} · DEX {stats['dex']} · CON {stats['con']}\n"
            f"INT {stats['int']} · WIT {stats['wit']} · MEN {stats['men']}\n"
            f"❤️ HP: {hp} · 💧 MP: {mp} · 💰 100\n\n"
            f"📍 Начальная деревня.",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        await run_tutorial(uid, m.chat.id)
        return

    # Если в бою — кнопки
    combat = await g.db.get_combat(uid)
    if combat:
        if combat.get("is_pvp"):
            await m.answer("⚔️ Ты в дуэли!", reply_markup=pvp_kb(combat["my_turn"]))
        else:
            await m.answer("⚔️ Ты в бою! Жми кнопки.", reply_markup=combat_kb())
        return

    # Энергия
    is_admin = uid in ADMIN_IDS
    if not is_admin and not user["is_premium"] and user.get("energy", 0) <= 0:
        wait_min = await g.db.get_energy_wait(uid)
        await m.answer(
            f"⏳ <b>Энергия исчерпана</b>\n\n"
            f"⚡ 0/{user.get('energy_max', 20)}\n"
            f"🕐 До +1: ~{wait_min} мин\n\n"
            f"<i>Энергия восстанавливается +1 каждые 30 мин.\n"
            f"Премиум — ×2 регенерация.</i>\n\n"
            f"💎 Премиум · 👥 Друг · 🎁 Награда",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return

    await g.bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]

    user_for_ai = dict(user)
    eff = effective_stats(user)
    for k in ["str", "dex", "con", "int", "wit", "men"]:
        user_for_ai[f"stat_{k}"] = eff[k]
    pet = await g.db.get_pet(uid)
    if pet:
        user_for_ai["pet_name"] = pet["name"]
        user_for_ai["pet_type"] = pet["pet_type"]
        user_for_ai["pet_level"] = pet["level"]

    loc_code = user.get("location_code", "village")
    event = await g.db.get_active_event(loc_code)
    owner = await g.db.get_location_owner(loc_code)

    result = await ai.generate(user["story"], action, user["arc"],
                                user_for_ai, event, owner)
    response = result["text"]

    if not is_admin:
        await g.db.spend_energy(uid, 1)

    if result["enemy"]:
        await g.db.incr_action_count(uid)
        new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
        await g.db.update_story(uid, new_story)
        await m.answer(f"{response}\n\n<i>{AI_MARKER}</i>", parse_mode=ParseMode.HTML)
        await start_combat_from_ai(m.chat.id, user, result["enemy"])
        return

    if result["item"]:
        await g.db.add_item(uid, result["item"])
        response += f"\n\n🎒 <i>+{result['item']}</i>"
    if result["location"]:
        loc_name = result["location"]
        for ncode, ninfo in W.get_neighbors(loc_code):
            if ninfo["name"].lower() == loc_name.lower() or loc_name.lower() in ninfo["name"].lower():
                can, reason = W.can_enter(ncode, user["level"])
                if can:
                    await g.db.set_location_code(uid, ncode)
                    await g.db.add_location(uid, ninfo["name"])
                    await g.db.progress_quest(uid, "visit_locations", 1)
                    response += (f"\n\n📍 <i>Переход: "
                                 f"{W.get_location(loc_code)['name']} → {ninfo['name']}</i>")
                else:
                    response += f"\n\n🚫 <i>{reason}</i>"
                break
        else:
            response += f"\n\n<i>📍 {loc_name}</i>"

    if result.get("material"):
        await g.db.add_material(uid, result["material"], 1)
        response += f"\n\n🔨 <i>+{MATERIAL_NAMES[result['material']]}</i>"
    if result["damage"] > 0:
        nhp = user["hp"] - result["damage"]
        await g.db.update_hp(uid, nhp)
        response += f"\n\n💔 <i>-{result['damage']} HP</i>"
        if nhp <= 0:
            await g.db.update_hp_max(uid, user["max_hp"], user["max_hp"])
            response += "\n\n💀 <i>Ты очнулся в деревне.</i>"
    if result["heal"] > 0:
        nhp = min(user["max_hp"], user["hp"] + result["heal"])
        await g.db.update_hp(uid, nhp)
        response += f"\n\n💚 <i>+{result['heal']} HP</i>"

    gold_gain = int((5 + result["gold"]) * faction_mult(user, "gold_mult"))
    if owner and user.get("guild_id") and owner.get("guild_id") == user["guild_id"]:
        gold_gain = int(gold_gain * W.LOCATION_OWNER_BONUS["gold_mult"])
    if event:
        gold_gain = int(gold_gain * event.get("gold_mult", 1.0))
    await g.db.add_gold(uid, gold_gain)
    if gold_gain > 0:
        await g.db.progress_quest(uid, "earn_gold", gold_gain)

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    await g.db.update_story(uid, new_story)
    await g.db.incr_action_count(uid)

    level, xp, leveled_up = await g.db.add_xp(uid, 10)
    if leveled_up:
        u = await g.db.get_user(uid)
        nm = calc_max_hp(u)
        nmp = calc_max_mp(u)
        await g.db.update_hp_max(uid, nm, nm)
        # Автоматически +1 очко умений за уровень
        async with g.db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET skill_points = skill_points + 1, "
                "mp=$1, max_mp=$1 WHERE user_id=$2", nmp, uid
            )
        response += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm} · MP: {nmp} · +1 очко умений"
        if level in (5, 10):
            await g.db.add_world_event(uid, user["username"],
                                       f"достиг {level} уровня!")

    updated = await g.db.get_user(uid)
        updated = await g.db.get_user(uid)
    # MP-регенерация вне боя (20%)
    if updated.get("max_mp", 0) > 0:
        regen = max(1, int(updated["max_mp"] * 0.20))
        new_mp = min(updated["max_mp"], updated.get("mp", 0) + regen)
        if new_mp > updated.get("mp", 0):
            await g.db.update_mp(uid, new_mp)
            updated["mp"] = new_mp

    new_ach = await check_achievements(uid, updated)
    new_ach = await check_achievements(uid, updated)
    if new_ach:
        ach_lines = "\n".join(f"• {ACHIEVEMENTS[c]}" for c in new_ach)
        response += f"\n\n🏆 <b>Достижение!</b>\n{ach_lines}"

    if is_admin:
        energy_line = "∞ (admin)"
    elif updated.get("is_premium"):
        energy_line = "∞"
    else:
        energy_line = f"{updated.get('energy', 0)}/{updated.get('energy_max', 20)}"
    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · 💰 {updated['gold']} · "
        f"❤️ {updated['hp']}/{updated['max_hp']} · ⚡ {energy_line}</i>",
        parse_mode=ParseMode.HTML)
