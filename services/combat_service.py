"""Логика боя: раунды, победа, смерть, состояние."""
import json
import random

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import (
    DUNGEONS, DROP_TABLE, MATERIAL_NAMES,
)
from core.formulas import (
    calc_max_hp, danger_emoji, effective_stats, faction_mult, hp_bar,
)
from core.keyboards import combat_kb, dungeon_continue_kb
from core.game_data import PETS
import world as W


# ================= СОСТОЯНИЕ БОЯ =================
async def send_combat_state(chat_id, user, combat, round_text="", event=None):
    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    emoji = danger_emoji(user["level"], combat["enemy_level"], combat["is_boss"])
    boss_label = " 🐉 БОСС" if combat["is_boss"] else ""
    header = f"⚔️ <b>РАУНД {combat['round_num']}</b>"
    if event:
        header += f" · {event['event_name']}"
    enemy_block = (f"{emoji} <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']}){boss_label}\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    pet_line = ""
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"], {})
        pet_line = f"\n🐾 {user.get('pet_name', pet.get('name', 'Питомец'))} (ур. {user.get('pet_level', 1)})"
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']}){pet_line}\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}\n"
                    f"💰 {user['gold']}")
    text = f"{header}\n\n{enemy_block}\n\n{player_block}"
    if round_text:
        text += f"\n\n{round_text}"
    await g.bot.send_message(chat_id, text, reply_markup=combat_kb(),
                             parse_mode=ParseMode.HTML)


async def start_combat_from_ai(chat_id, user, enemy):
    """Начать бой из сценария ИИ."""
    await g.db.start_combat(user["user_id"], enemy["name"], enemy["level"],
                            enemy["hp"], 1 if enemy["is_boss"] else 0)
    combat = await g.db.get_combat(user["user_id"])
    intro = "🐉 <b>БОСС!</b>" if enemy["is_boss"] else "Бой начался!"
    event = await g.db.get_active_event(user.get("location_code", "village"))
    await send_combat_state(chat_id, user, combat, intro, event)


def pet_attack_damage(user, round_num):
    """Урон питомца в раунде."""
    if not user.get("pet_type"):
        return 0, ""
    ptype = user["pet_type"]
    plvl = user.get("pet_level", 1)
    if ptype == "wolf":
        return 5 + plvl * 2, "🐺 Волк кусает"
    if ptype == "dragon":
        if round_num % 2 == 0:
            return 10 + plvl * 3, "🐉 Дракон дышит огнём"
        return 0, ""
    return 0, ""


# ================= РАУНД БОЯ =================
async def process_combat_round(chat_id, user, combat, action_type, extra_text=""):
    event = await g.db.get_active_event(user.get("location_code", "village"))
    enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
    new_enemy_hp = combat["enemy_hp"]

    if action_type == "attack":
        eff = effective_stats(user)
        dmg = int((eff["str"] * 2 + eff["dex"] + random.randint(0, 5)) * faction_mult(user, "dmg_mult"))
        crit_chance = eff["dex"]
        if user.get("pet_type") == "owl":
            crit_chance += 15
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit:
            dmg = int(dmg * 2)
        pet_dmg, pet_text = pet_attack_damage(user, combat["round_num"])
        total_dmg = dmg + pet_dmg
        new_enemy_hp = combat["enemy_hp"] - total_dmg
        await g.db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
        parts = []
        if is_crit:
            parts.append(f"💥 <b>КРИТ!</b> {dmg}")
        else:
            parts.append(f"⚔️ {dmg} урона.")
        if pet_dmg > 0:
            parts.append(f"{pet_text} — {pet_dmg}!")
        extra_text = "\n".join(parts)
        await g.db.set_combat_defending(user["user_id"], 0)

    elif action_type == "defend":
        await g.db.set_combat_defending(user["user_id"], 1)
        heal = int(user["max_hp"] * 0.05)
        new_hp = min(user["max_hp"], user["hp"] + heal)
        await g.db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text = f"🛡 +{heal} HP."
        enemy_dmg = max(1, int((combat["enemy_level"] * 5 + random.randint(0, 5)) * 0.5 * enemy_dmg_mult))
        new_hp = max(0, user["hp"] - enemy_dmg)
        await g.db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        extra_text += f"\n💔 {combat['enemy_name']} бьёт на {enemy_dmg}."
        if user["hp"] <= 0:
            await handle_death(chat_id, user, combat)
            return False
        await g.db.incr_combat_round(user["user_id"])
        await send_combat_state(chat_id, user,
                                await g.db.get_combat(user["user_id"]), extra_text, event)
        return True

    if new_enemy_hp <= 0:
        await handle_victory(chat_id, user, combat, extra_text)
        return False

    if user.get("pet_type") == "phoenix":
        plvl = user.get("pet_level", 1)
        heal = int(user["max_hp"] * 0.05) + plvl
        new_hp = min(user["max_hp"], user["hp"] + heal)
        if new_hp > user["hp"]:
            await g.db.update_hp(user["user_id"], new_hp)
            user["hp"] = new_hp
            extra_text += f"\n🔥 Феникс лечит +{heal} HP."

    enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) * enemy_dmg_mult)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await g.db.update_hp(user["user_id"], new_hp)
    user["hp"] = new_hp
    extra_text += f"\n💔 {combat['enemy_name']} наносит {enemy_dmg}."

    if user["hp"] <= 0:
        await handle_death(chat_id, user, combat)
        return False

    await g.db.incr_combat_round(user["user_id"])
    await send_combat_state(chat_id, user,
                            await g.db.get_combat(user["user_id"]), extra_text, event)
    return True


# ================= ПОБЕДА =================
async def handle_victory(chat_id, user, combat, prefix_text):
    # Lazy import — избегаем циклической зависимости с dungeon_service
    from services.dungeon_service import dungeon_finish

    await g.db.end_combat(user["user_id"])

    enemy_name = combat["enemy_name"]
    all_q = await g.db.get_user_quests(user["user_id"])
    for qrow in all_q:
        if qrow["completed"]:
            continue
        q = W.get_quest(qrow["quest_code"])
        if not q:
            continue
        if q["target"].lower() in enemy_name.lower():
            await g.db.incr_npc_quest(user["user_id"], qrow["quest_code"], 1)

    q = await g.db.progress_quest(user["user_id"], "kill_enemies", 1)
    if q and q.get("completed"):
        try:
            await g.bot.send_message(
                user["user_id"],
                f"✅ <b>Квест выполнен:</b> Убить врагов\n+{q['gold']}💰 · +{q['xp']} XP",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass

    exp = combat["enemy_level"] * 15
    gold = combat["enemy_level"] * 10
    is_dungeon = combat.get("is_dungeon", 0)
    if combat["is_boss"]:
        exp *= 3
        gold *= 3
    gold = int(gold * faction_mult(user, "gold_mult"))

    event = await g.db.get_active_event(user.get("location_code", "village"))
    xp_mult = event.get("xp_mult", 1.0) if event else 1.0
    gold_mult_ev = event.get("gold_mult", 1.0) if event else 1.0
    exp = int(exp * xp_mult)
    gold = int(gold * gold_mult_ev)

    if user.get("pet_type"):
        await g.db.add_pet_xp(user["user_id"], combat["enemy_level"] * 5)

    if is_dungeon:
        d = DUNGEONS.get(user.get("dungeon_id", ""), {})
        mult = d.get("reward_mult", 1.0)
        gold = int(gold * mult)
        try:
            items = json.loads(user.get("dungeon_loot_items") or "[]")
        except Exception:
            items = []
        if random.randint(1, 100) <= 40:
            items.append(random.choice(DROP_TABLE))
        await g.db.advance_dungeon(user["user_id"], gold, json.dumps(items))
        text = (f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
                f"<b>{combat['enemy_name']}</b> повержен!\n"
                f"💰 Добыча: +{gold}")
        u = await g.db.get_user(user["user_id"])
        d = DUNGEONS.get(u.get("dungeon_id", ""))
        if combat["is_boss"]:
            text += f"\n\n🐉 <b>БОСС ПОВЕРЖЕН!</b>"
        text += f"\n\n<b>Комната {u['dungeon_room']}/{d.get('rooms', '?')}</b>"
        if u["dungeon_room"] >= d.get("rooms", 1):
            await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            await dungeon_finish(chat_id, user["user_id"], "Подземелье пройдено!")
            return
        await g.bot.send_message(chat_id, text, reply_markup=dungeon_continue_kb(),
                                 parse_mode=ParseMode.HTML)
        if combat["is_boss"]:
            await g.db.incr_bosses(user["user_id"])
        return

    await g.db.add_gold(user["user_id"], gold)
    level, xp, leveled_up = await g.db.add_xp(user["user_id"], exp)
    text = (f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
            f"<b>{combat['enemy_name']}</b> повержен!\n"
            f"+{exp} XP · +{gold}💰")

    if event:
        text += f"\n<i>{event['event_name']} усиливает награду</i>"

    if combat["is_boss"]:
        await g.db.incr_bosses(user["user_id"])
        await g.db.add_world_event(user["user_id"], user["username"],
                                   f"победил босса «{combat['enemy_name']}»")
        await g.db.update_hp(user["user_id"], user["max_hp"])
        text += f"\n\n🐉 <b>БОСС ПОВЕРЖЕН!</b> HP восстановлено."
        if await g.db.add_achievement(user["user_id"], "first_boss"):
            text += "\n🏆 Достижение: ⚔️ Убийца боссов"

    if random.randint(1, 100) <= 30:
        item = random.choice(DROP_TABLE)
        await g.db.add_item(user["user_id"], item)
        text += f"\n\n🎒 <b>Добыча:</b> {item}"

    if user.get("pet_type") == "owl" and random.randint(1, 100) <= 20:
        mat = random.choice(["iron", "leather", "dust", "crystal"])
        await g.db.add_material(user["user_id"], mat, 1)
        text += f"\n🔨 Сова нашла: {MATERIAL_NAMES[mat]}"

    if leveled_up:
        u = await g.db.get_user(user["user_id"])
        nm = calc_max_hp(u)
        await g.db.update_hp_max(user["user_id"], nm, nm)
        text += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm}."
        if level in (5, 10):
            await g.db.add_world_event(user["user_id"], user["username"],
                                       f"достиг {level} уровня!")

    if await g.db.add_achievement(user["user_id"], "first_blood"):
        text += "\n🏆 Достижение: 🩸 Первая кровь"
    u = await g.db.get_user(user["user_id"])
    if u["bosses_defeated"] >= 5:
        if await g.db.add_achievement(user["user_id"], "boss_5"):
            text += "\n🏆 Достижение: 🐉 Легенда"

    await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)


# ================= СМЕРТЬ =================
async def handle_death(chat_id, user, combat):
    was_dungeon = combat.get("is_dungeon", 0)
    await g.db.end_combat(user["user_id"])
    if was_dungeon:
        await g.db.exit_dungeon(user["user_id"])
    lost = int(user["gold"] * 0.30)
    await g.db.set_gold(user["user_id"], user["gold"] - lost)
    u = await g.db.get_user(user["user_id"])
    nm = calc_max_hp(u)
    await g.db.update_hp_max(user["user_id"], nm, nm)
    await g.db.update_story(user["user_id"], "")
    await g.db.incr_deaths(user["user_id"])
    await g.db.add_achievement(user["user_id"], "survivor")
    await g.db.add_world_event(user["user_id"], user["username"],
                               f"пал в бою с «{combat['enemy_name']}»")
    text = (f"💀 <b>ТЫ ПАЛ В БОЮ</b>\n\n"
            f"<b>{combat['enemy_name']}</b> оказался сильнее.\n\n"
            f"Ты очнулся в Начальной деревне.\n"
            f"Жрецы забрали <b>{lost}💰</b> (30%).")
    if was_dungeon:
        text += "\n\n⚠️ <b>Вся добыча из подземелья потеряна!</b>"
    text += (f"\n\n❤️ HP: {nm}/{nm}\n💰 Золото: {u['gold'] - lost}\n\n"
             f"<i>Уровень и опыт сохранены.</i>")
    await g.db.set_location_code(user["user_id"], "village")
    await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
