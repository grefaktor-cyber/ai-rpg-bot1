"""Создание героя + основной обработчик (свободный текст → GigaChat)."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS, ACHIEVEMENTS, MATERIAL_NAMES
from core.formulas import (
    calc_stats, effective_stats, calc_max_hp, faction_mult,
)
from core.keyboards import main_kb, race_selection_kb, class_selection_kb, faction_selection_kb, pvp_kb, combat_kb
from core.texts import EXCLUDE_FROM_AI
from config import ADMIN_IDS, FREE_DAILY_LIMIT, AI_MARKER
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
    await g.bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                             reply_markup=class_selection_kb(CLASSES),
                             parse_mode=ParseMode.HTML)


async def _show_faction(m):
    await g.bot.send_message(m.chat.id, "🏛 <b>Выбери фракцию:</b>",
                             reply_markup=faction_selection_kb(FACTIONS),
                             parse_mode=ParseMode.HTML)


# ================= ДОСТИЖЕНИЯ =================
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


# ================= ОСНОВНОЙ ОБРАБОТЧИК =================
@router.message(F.text, ~F.text.in_(EXCLUDE_FROM_AI))
async def handle(m: Message):
    uid = m.from_user.id
    user = await g.db.get_user(uid, m.from_user.username or "")

    if not user["consent_given"]:
        await m.answer("⚠️ Сначала /start"); return
    if not user["race"]:
        await _show_race(m); return
    if not user["class"]:
        await _show_class(m, user["race"]); return
    if not user["faction"]:
        await _show_faction(m); return

    # Создание героя
    if not user["char_name"]:
        name = m.text.strip()[:20]
        if len(name) < 2:
            await m.answer("✏️ Имя 2–20 символов:"); return
        stats = calc_stats(user["race"], user["class"])
        hp_base = stats["con"] * 20 + 15
        user_tmp = {"faction": user["faction"], "level": 1, "stat_con": stats["con"],
                    "stat_str": stats["str"], "stat_dex": stats["dex"],
                    "stat_int": stats["int"], "stat_wit": stats["wit"],
                    "stat_men": stats["men"], "pet_type": None}
        hp = int(hp_base * faction_mult(user_tmp, "hp_mult"))
        await g.db.set_char(uid, name, stats, hp)
        await m.answer(
            f"🎉 <b>Герой создан!</b>\n\n"
            f"<b>{name}</b>\n"
            f"{RACES[user['race']]['name']} · {CLASSES[user['class']]['name']}\n"
            f"{FACTIONS[user['faction']]['name']}\n\n"
            f"STR {stats['str']} · DEX {stats['dex']} · CON {stats['con']}\n"
            f"INT {stats['int']} · WIT {stats['wit']} · MEN {stats['men']}\n"
            f"❤️ HP: {hp} · 💰 100\n\n"
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

    # Лимит
    is_admin = uid in ADMIN_IDS
    if not is_admin and not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит исчерпан ({FREE_DAILY_LIMIT}).\n\n"
            "💎 Премиум · 👥 Друг · 🎁 Награда",
            reply_markup=main_kb())
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

    if result["enemy"]:
        await g.db.increment(uid)
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
    await g.db.increment(uid)
    await g.db.incr_action_count(uid)

    level, xp, leveled_up = await g.db.add_xp(uid, 10)
    if leveled_up:
        u = await g.db.get_user(uid)
        nm = calc_max_hp(u)
        await g.db.update_hp_max(uid, nm, nm)
        response += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm}/{nm}"
        if level in (5, 10):
            await g.db.add_world_event(uid, user["username"],
                                       f"достиг {level} уровня!")

    updated = await g.db.get_user(uid)
    new_ach = await check_achievements(uid, updated)
    if new_ach:
        ach_lines = "\n".join(f"• {ACHIEVEMENTS[c]}" for c in new_ach)
        response += f"\n\n🏆 <b>Достижение!</b>\n{ach_lines}"

    left = ("∞ (admin)" if is_admin
            else "∞" if user["is_premium"]
            else FREE_DAILY_LIMIT - user["requests_today"] - 1)
    need = level * level * 100
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · XP: {xp}/{need} · 💰 {updated['gold']} · "
        f"❤️ {updated['hp']}/{updated['max_hp']} · Осталось: {left}</i>",
        parse_mode=ParseMode.HTML)
