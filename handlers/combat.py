"""Бои с мобами, боссы, подземелья."""
import json
import random
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
import world as W

router = Router()


# ================= КОНСТАНТЫ =================
POTION_PRICE = 25
POTION_HEAL = 30

SHOP = {
    "Железный меч":       {"type": "weapon", "price": 50,   "bonus": {"str": 2}},
    "Стальной меч":       {"type": "weapon", "price": 250,  "bonus": {"str": 5}},
    "Клинок тьмы":        {"type": "weapon", "price": 1200, "bonus": {"str": 10, "dex": 2}},
    "Посох мага":         {"type": "weapon", "price": 200,  "bonus": {"int": 4}},
    "Лук охотника":       {"type": "weapon", "price": 200,  "bonus": {"dex": 4}},
    "Кожаная броня":      {"type": "armor",  "price": 50,   "bonus": {"con": 2}},
    "Кольчуга":           {"type": "armor",  "price": 300,  "bonus": {"con": 5}},
    "Мантия мага":        {"type": "armor",  "price": 250,  "bonus": {"int": 3, "wit": 2}},
    "Латы рыцаря":        {"type": "armor",  "price": 1200, "bonus": {"con": 10}},
    "Амулет удачи":       {"type": "accessory", "price": 150, "bonus": {"men": 3}},
    "Кольцо силы":        {"type": "accessory", "price": 200, "bonus": {"str": 3}},
    "Перстень мудрости":  {"type": "accessory", "price": 200, "bonus": {"int": 3}},
    "Кольцо ловкости":    {"type": "accessory", "price": 200, "bonus": {"dex": 3}},
    "Амулет мудреца":     {"type": "accessory", "price": 800, "bonus": {"int": 5, "wit": 3}},
}

PETS = {
    "wolf":    {"name": "Волк",      "price": 500,  "bonus": {"str": 2, "dex": 1}},
    "owl":     {"name": "Сова",      "price": 500,  "bonus": {"wit": 2, "int": 1}},
    "dragon":  {"name": "Дракончик", "price": 2000, "bonus": {"str": 3, "con": 1}},
    "phoenix": {"name": "Феникс",    "price": 3000, "bonus": {"men": 3, "con": 2}},
}

FACTIONS = {
    "light": {"hp_mult": 1.10, "shop_mult": 0.90, "gold_mult": 0.90, "dmg_mult": 1.00},
    "dark":  {"hp_mult": 0.80, "shop_mult": 1.00, "gold_mult": 1.20, "dmg_mult": 1.15},
}

DUNGEONS = {
    "goblin_cave": {"name": "Пещера гоблинов",  "level_req": 1,  "entry": 50,
                    "rooms": 3, "reward_mult": 1.0,
                    "enemies": ["Гоблин-разведчик", "Гоблин-воин", "Вождь гоблинов"]},
    "old_ruins":   {"name": "Древние руины",    "level_req": 4,  "entry": 200,
                    "rooms": 4, "reward_mult": 2.0,
                    "enemies": ["Скелет-страж", "Проклятый рыцарь", "Каменный голем", "Древний лич"]},
    "crypt":       {"name": "Проклятый склеп",  "level_req": 9,  "entry": 600,
                    "rooms": 5, "reward_mult": 4.0,
                    "enemies": ["Вампир-новичок", "Призрак", "Некромант", "Тёмный жрец", "Король вампиров"]},
    "abyss":       {"name": "Бездна",           "level_req": 16, "entry": 2000,
                    "rooms": 5, "reward_mult": 8.0,
                    "enemies": ["Демон", "Архидемон", "Пожиратель душ", "Повелитель Бездны", "Древний дракон"]},
}

DROP_TABLE = ["Кожаная броня", "Железный меч", "Амулет удачи", "Кольцо силы",
              "Кольцо ловкости", "Перстень мудрости", "Посох мага", "Лук охотника"]

MATERIAL_NAMES = {"iron": "железо", "leather": "кожа",
                  "dust": "магическая пыль", "crystal": "кристалл"}

ACHIEVEMENTS = {
    "first_boss":  "⚔️ Убийца боссов",
    "boss_5":      "🐉 Легенда — 5 боссов",
    "first_blood": "🩸 Первая кровь",
    "survivor":    "💀 Выживший",
    "dungeon_1":   "🏰 Пещерный ход",
}


# ================= УТИЛИТЫ =================
def parse_item(s):
    if not s:
        return "", 0
    import re as _re
    m = _re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def effective_stats(user):
    base = {
        "str": user.get("stat_str", 5), "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5), "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5), "men": user.get("stat_men", 5),
    }
    for slot in ["equipped_weapon", "equipped_armor", "equipped_accessory"]:
        raw = user.get(slot, "")
        if raw:
            name, lvl = parse_item(raw)
            if name in SHOP:
                for k, v in SHOP[name]["bonus"].items():
                    bonus = int(v * (1 + lvl * 0.10))
                    base[k] = base.get(k, 0) + bonus
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"])
        if pet:
            for k, v in pet["bonus"].items():
                base[k] = base.get(k, 0) + v
    return base


def calc_max_hp(user):
    eff = effective_stats(user)
    hp = eff["con"] * 20 + user["level"] * 15
    f = FACTIONS.get(user.get("faction", ""), None)
    if f:
        hp = int(hp * f["hp_mult"])
    return hp


def hp_bar(current, maximum, length=10):
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def danger_emoji(player_level, enemy_level, is_boss):
    if is_boss:
        return "🐉"
    diff = enemy_level - player_level
    if diff <= -3: return "🟢"
    if diff <= -1: return "🟡"
    if diff <= 1:  return "🟠"
    if diff <= 3:  return "🔴"
    return "💀"


def faction_mult(user, key):
    f = FACTIONS.get(user.get("faction", ""))
    if not f:
        return 1.0
    return f.get(key, 1.0)


# ================= КЛАВИАТУРЫ =================
def combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="combat_attack"),
         InlineKeyboardButton(text="🛡 Защита", callback_data="combat_defend")],
        [InlineKeyboardButton(text=f"💚 Зелье ({POTION_PRICE}💰)", callback_data="combat_potion"),
         InlineKeyboardButton(text="🏃 Бежать", callback_data="combat_flee")],
    ])


def dungeon_continue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="dungeon_next")],
        [InlineKeyboardButton(text="🏃 Выйти с добычей", callback_data="dungeon_leave")],
    ])


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
    await g.bot.send_message(chat_id, text, reply_markup=combat_kb(), parse_mode=ParseMode.HTML)


async def start_combat_from_ai(chat_id, user, enemy):
    await g.db.start_combat(user["user_id"], enemy["name"], enemy["level"],
                            enemy["hp"], 1 if enemy["is_boss"] else 0)
    combat = await g.db.get_combat(user["user_id"])
    intro = "🐉 <b>БОСС!</b>" if enemy["is_boss"] else "Бой начался!"
    event = await g.db.get_active_event(user.get("location_code", "village"))
    await send_combat_state(chat_id, user, combat, intro, event)


def pet_attack_damage(user, round_num):
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
            await g.bot.send_message(user["user_id"],
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


# ================= ХЕНДЛЕРЫ КНОПОК БОЯ =================
@router.callback_query(F.data == "combat_attack")
async def cb_attack(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен.")
        return
    await c.answer("⚔️ Атака!")
    await process_combat_round(c.message.chat.id, user, combat, "attack")


@router.callback_query(F.data == "combat_defend")
async def cb_defend(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен.")
        return
    await c.answer("🛡 Защита")
    await process_combat_round(c.message.chat.id, user, combat, "defend")


@router.callback_query(F.data == "combat_potion")
async def cb_potion(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен.")
        return
    if user["hp"] >= user["max_hp"]:
        await c.answer("❤️ HP полное!", show_alert=True)
        return
    is_admin = c.from_user.id in __import__("config").ADMIN_IDS
    if not is_admin and user["gold"] < POTION_PRICE:
        await c.answer(f"❌ Нужно {POTION_PRICE}💰", show_alert=True)
        return
    if not is_admin:
        await g.db.spend_gold(c.from_user.id, POTION_PRICE)
    new_hp = min(user["max_hp"], user["hp"] + POTION_HEAL)
    await g.db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    await c.answer(f"💚 +{POTION_HEAL} HP")
    event = await g.db.get_active_event(user.get("location_code", "village"))
    enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
    enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) * enemy_dmg_mult)
    if combat["is_boss"]:
        enemy_dmg = int(enemy_dmg * 1.5)
    new_hp = max(0, user["hp"] - enemy_dmg)
    await g.db.update_hp(c.from_user.id, new_hp)
    user["hp"] = new_hp
    if user["hp"] <= 0:
        await handle_death(c.message.chat.id, user, combat)
        return
    await g.db.incr_combat_round(c.from_user.id)
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            f"💚 Зелье +{POTION_HEAL}. 💔 Враг бьёт на {enemy_dmg}.",
                            event)


@router.callback_query(F.data == "combat_flee")
async def cb_flee(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or combat.get("is_pvp"):
        await c.answer("Бой окончен.")
        return
    if combat["is_boss"]:
        await c.answer("🐉 От босса не убежать!", show_alert=True)
        return
    if combat.get("is_dungeon"):
        await c.answer("🏰 Из подземелья не сбежать!", show_alert=True)
        return
    if random.randint(1, 100) <= 50:
        await g.db.end_combat(c.from_user.id)
        await c.answer("🏃 Побег!")
        await c.message.answer("🏃 Ты сбежал.")
    else:
        await c.answer("❌ Не удалось!")
        event = await g.db.get_active_event(user.get("location_code", "village"))
        enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
        enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) // 2 * enemy_dmg_mult)
        new_hp = max(0, user["hp"] - enemy_dmg)
        await g.db.update_hp(c.from_user.id, new_hp)
        user["hp"] = new_hp
        if user["hp"] <= 0:
            await handle_death(c.message.chat.id, user, combat)
            return
        await g.db.incr_combat_round(c.from_user.id)
        await send_combat_state(c.message.chat.id, user,
                                await g.db.get_combat(c.from_user.id),
                                f"❌ Побег не удался! -{enemy_dmg}.", event)


# ================= ПОДЗЕМЕЛЬЯ =================
@router.message(Command("dungeon"))
@router.message(F.text == "🏰 Подземелья")
async def dungeon_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя.")
        return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты в бою!")
        return
    if u.get("dungeon_id"):
        d = DUNGEONS.get(u["dungeon_id"], {})
        await m.answer(
            f"🏰 Ты уже в подземелье: <b>{d.get('name', '?')}</b>\n"
            f"Комната {u['dungeon_room']}/{d.get('rooms', '?')}\n"
            f"💰 Добыча: {u['dungeon_loot_gold']}\n\n"
            f"/dungeon_continue — продолжить\n/dungeon_exit — выйти",
            parse_mode=ParseMode.HTML)
        return
    text = "🏰 <b>Подземелья</b>\n\n"
    buttons = []
    for code, d in DUNGEONS.items():
        can = u["level"] >= d["level_req"] and u["gold"] >= d["entry"]
        mark = "✅" if can else "🔒"
        text += (f"{mark} <b>{d['name']}</b>\n"
                 f"  Ур.{d['level_req']}+ · вход {d['entry']}💰 · комнат {d['rooms']}\n")
        if can:
            buttons.append([InlineKeyboardButton(
                text=f"{d['name']} — {d['entry']}💰",
                callback_data=f"dungeon_enter_{code}")])
    text += "\n<i>Цепочка боёв, в конце босс. Смерть = потеря добычи.</i>"
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("dungeon_enter_"))
async def dungeon_enter(c: CallbackQuery):
    code = c.data.replace("dungeon_enter_", "")
    if code not in DUNGEONS:
        await c.answer("Нет")
        return
    d = DUNGEONS[code]
    u = await g.db.get_user(c.from_user.id)
    is_admin = c.from_user.id in __import__("config").ADMIN_IDS
    if u["level"] < d["level_req"]:
        await c.answer(f"Нужен {d['level_req']} уровень", show_alert=True)
        return
    if not is_admin:
        if not await g.db.spend_gold(c.from_user.id, d["entry"]):
            await c.answer(f"Нужно {d['entry']}💰", show_alert=True)
            return
    await g.db.start_dungeon(c.from_user.id, code)
    await c.answer("Вход!")
    await c.message.answer(f"🏰 Входишь в <b>{d['name']}</b>...", parse_mode=ParseMode.HTML)
    await _spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, code, 1)


async def _spawn_dungeon_enemy(chat_id, uid, dungeon_id, room):
    d = DUNGEONS[dungeon_id]
    enemy_name = d["enemies"][min(room - 1, len(d["enemies"]) - 1)]
    is_boss = 1 if room == d["rooms"] else 0
    base_level = d["level_req"] + room - 1
    enemy_level = base_level + (2 if is_boss else 0)
    enemy_hp = enemy_level * (30 if is_boss else 20)
    await g.db.start_combat(uid, enemy_name, enemy_level, enemy_hp, boss=is_boss, dungeon=1)
    u = await g.db.get_user(uid)
    combat = await g.db.get_combat(uid)
    label = "🐉 БОСС" if is_boss else f"Комната {room}/{d['rooms']}"
    await send_combat_state(chat_id, u, combat, f"🏰 <b>{label}</b>")


@router.message(Command("dungeon_continue"))
async def dungeon_continue_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u.get("dungeon_id"):
        await m.answer("Ты не в подземелье.")
        return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!")
        return
    d = DUNGEONS.get(u["dungeon_id"])
    next_room = u["dungeon_room"] + 1
    if next_room > d["rooms"]:
        await dungeon_finish(m.chat.id, m.from_user.id, "Ты прошёл все комнаты!")
        return
    await g.db.advance_dungeon(m.from_user.id, 0, u["dungeon_loot_items"])
    await _spawn_dungeon_enemy(m.chat.id, m.from_user.id, u["dungeon_id"], next_room)


@router.message(Command("dungeon_exit"))
async def dungeon_exit_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u.get("dungeon_id"):
        await m.answer("Ты не в подземелье.")
        return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!")
        return
    await dungeon_finish(m.chat.id, m.from_user.id, "Ты покидаешь подземелье с добычей.")


@router.callback_query(F.data == "dungeon_next")
async def dungeon_next_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    if not u.get("dungeon_id"):
        await c.answer("Не в подземелье")
        return
    if await g.db.get_combat(c.from_user.id):
        await c.answer("Бой!")
        return
    d = DUNGEONS.get(u["dungeon_id"])
    next_room = u["dungeon_room"] + 1
    if next_room > d["rooms"]:
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await dungeon_finish(c.message.chat.id, c.from_user.id, "Подземелье пройдено!")
        return
    await g.db.advance_dungeon(c.from_user.id, 0, u["dungeon_loot_items"])
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, u["dungeon_id"], next_room)


@router.callback_query(F.data == "dungeon_leave")
async def dungeon_leave_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await dungeon_finish(c.message.chat.id, c.from_user.id, "Ты выходишь с добычей.")


async def dungeon_finish(chat_id, uid, msg):
    u = await g.db.get_user(uid)
    loot_gold = u.get("dungeon_loot_gold", 0)
    try:
        loot_items = json.loads(u.get("dungeon_loot_items") or "[]")
    except Exception:
        loot_items = []
    if loot_gold:
        await g.db.add_gold(uid, loot_gold)
    for it in loot_items:
        await g.db.add_item(uid, it)
    await g.db.exit_dungeon(uid)
    text = f"🏁 <b>{msg}</b>\n\n💰 Золото: +{loot_gold}"
    if loot_items:
        text += f"\n🎒 Предметы: {', '.join(loot_items)}"
    await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
    await g.db.add_achievement(uid, "dungeon_1")
