"""Логика боя 4.0: очередь 4 действия, спойл, range, расовые бонусы, итоги."""
import json
import random

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import (
    DUNGEONS, DROP_TABLE, MATERIAL_NAMES,
    POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE,
    PETS, RANGE_CLASSES, get_racial_combat_bonus,
)
from core.materials import RARE_MATERIALS, SPOIL_CLASSES
from core.books import SKILL_BOOKS
from core.crafting import RECIPES
from core.formulas import (
    calc_max_hp, calc_max_mp, danger_emoji, effective_stats,
    faction_mult, hp_bar, calc_damage, get_dmg_type,
    enemy_p_def, enemy_m_def, apply_defense,
    racial_crit_bonus, racial_magic_mult, racial_heal_mult,
    racial_gold_mult, racial_low_hp_mult,
    calc_xp_reward, calc_enemy_base_dmg,
    get_enemy_dmg_type, get_player_def_for_enemy, apply_player_defense,
    get_boss_phase, get_block_chance, get_crit_bonus, get_gold_mult,
)
from core.keyboards import combat_kb, combat_pending_text, dungeon_continue_kb
from core.skills import get_skill, skill_multiplier
from services.notifications import (
    notify_item, notify_achievement, notify_boss, notify_quest,
    notify_drop, notify_book, notify_recipe, notify_level,
)
import world as W

MAX_ACTIONS = 4

DEFEND_MULT_BY_COUNT = {
    0: 1.00, 1: 0.70, 2: 0.50, 3: 0.35, 4: 0.20,
}


def _is_range_round_1(user, combat):
    """Range-класс бьёт дальше в 1-м раунде."""
    return (combat.get("round_num", 1) == 1
            and user.get("class") in RANGE_CLASSES)


def _rage_mult(user):
    """Множитель ярости: чем ниже HP, тем выше урон.
    Демон: rage_max = 1.60 → при 0% HP урон ×1.6."""
    rage_max = get_racial_combat_bonus(user, "rage_max", 0.0)
    if rage_max <= 1.0:
        return 1.0
    hp_pct = user["hp"] / max(1, user["max_hp"])
    return 1.0 + (1.0 - hp_pct) * (rage_max - 1.0)


def _get_enemy_actions(combat):
    is_boss = bool(combat.get("is_boss"))
    is_dungeon = bool(combat.get("is_dungeon"))
    if is_boss:
        n = random.choice([2, 3, 3])
        return n, {2: 0.65, 3: 0.5}[n]
    if is_dungeon:
        return 2, 0.65
    n = random.choice([1, 1, 2])
    return n, {1: 1.0, 2: 0.65}[n]


def calc_final_damage_safe(user, t_pdef, t_mdef):
    base = calc_damage(user)
    dmg_type = get_dmg_type(user)
    if dmg_type == "magic":
        return apply_defense(base, t_mdef), dmg_type
    return apply_defense(base, t_pdef), dmg_type


# ================= СОСТОЯНИЕ =================
async def send_combat_state(chat_id, user, combat, round_text="", event=None,
                            edit_message=None):
    user = await g.db.get_user(user["user_id"])
    combat = await g.db.get_combat(user["user_id"])
    if not combat:
        return

    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    emoji = danger_emoji(user["level"], combat["enemy_level"], combat["is_boss"])
    boss_label = " 🐉 БОСС" if combat["is_boss"] else ""

    enemy_dmg_type = get_enemy_dmg_type(combat["enemy_name"])
    type_label = " 🔮" if enemy_dmg_type == "magic" else " ⚔️"
    phase = get_boss_phase(combat)
    phase_label = f" [{phase['name']}]" if phase else ""

    header = f"⚔️ <b>РАУНД {combat['round_num']}</b>"
    if event:
        header += f" · {event['event_name']}"

    enemy_block = (f"{emoji} <b>{combat['enemy_name']}</b>"
                   f"{type_label} (Ур. {combat['enemy_level']}){boss_label}{phase_label}\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")

    pet_line = ""
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"], {})
        pet_line = f"\n🐾 {user.get('pet_name', pet.get('name', 'Питомец'))}"

    mp = user.get("mp", 0)
    max_mp = user.get("max_mp", 0)
    mp_line = f" · 💧 MP: {mp}/{max_mp}" if max_mp else ""

    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']}){pet_line}\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}{mp_line}")

    text = f"{header}\n\n{enemy_block}\n\n{player_block}"
    if round_text:
        text += f"\n\n{round_text}"

    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    text += f"\n\n{combat_pending_text(pending)}"

    try:
        active = json.loads(user.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    can_spoil = user.get("class") in SPOIL_CLASSES
    spoil_used = bool(combat.get("spoil_used"))

    kb = combat_kb(active, mp, pending, can_spoil=can_spoil,
                   spoil_used=spoil_used)

    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=kb,
                                          parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass

    hints = []
    hp_pct = user["hp"] / max(1, user["max_hp"])
    if hp_pct < 0.30 and user["hp"] > 0:
        if user["gold"] >= POTION_PRICE:
            hints.append("💡 HP низкое — добавь 💚 <b>Зелье HP</b> в очередь")
        else:
            hints.append("⚠️ HP низкое, но золота на зелье нет — беги или защищайся")
    if combat["round_num"] >= 5 and not pending:
        hints.append("💡 Собери очередь из 3-4 действий для сильного хода")

    if hints:
        text += "\n\n" + "\n".join(hints)

    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)


async def start_combat_from_ai(chat_id, user, enemy):
    await g.db.start_combat(user["user_id"], enemy["name"], enemy["level"],
                            enemy["hp"], 1 if enemy["is_boss"] else 0)
    await g.db.set_pending_actions(user["user_id"], "[]")
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
    if ptype == "edragon":
        return 25 * plvl, "🐲 Древний дракон атакует"
    return 0, ""


# ================= ОЧЕРЕДЬ =================
async def queue_action(uid, action_code):
    combat = await g.db.get_combat(uid)
    if not combat:
        return False, "no_combat"
    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if len(pending) >= MAX_ACTIONS:
        return False, "full"
    pending.append(action_code)
    await g.db.set_pending_actions(uid, json.dumps(pending))
    return True, "ok"


async def undo_action(uid):
    combat = await g.db.get_combat(uid)
    if not combat:
        return False
    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if pending:
        pending.pop()
        await g.db.set_pending_actions(uid, json.dumps(pending))
        return True
    return False


# ================= ДЕЙСТВИЕ ИГРОКА =================
async def _exec_player_action(user, combat, action, log):
    new_enemy_hp = combat["enemy_hp"]
    enemy_skip = False

    # --- Расчёт расовых бонусов ---
    race_dmg_mult = get_racial_combat_bonus(user, "dmg_mult", 1.0)
    race_magic_mult = get_racial_combat_bonus(user, "magic_mult", 1.0)
    race_crit_bonus = get_racial_combat_bonus(user, "crit_bonus", 0)
    race_lifesteal = get_racial_combat_bonus(user, "lifesteal", 0.0)
    rage_mult = _rage_mult(user)
    range_bonus = 1.30 if _is_range_round_1(user, combat) else 1.0

    if action == "attack":
        eff = effective_stats(user)
        next_mult = combat.get("next_atk_mult", 1.0) or 1.0
        t_pdef = enemy_p_def(combat["enemy_level"])
        t_mdef = enemy_m_def(combat["enemy_level"])
        dmg_after_def, dmg_type = calc_final_damage_safe(user, t_pdef, t_mdef)
        if dmg_type == "magic":
            dmg_after_def = int(dmg_after_def * racial_magic_mult(user) * race_magic_mult)
        else:
            dmg_after_def = int(dmg_after_def * race_dmg_mult)
        dmg_after_def = int(dmg_after_def * racial_low_hp_mult(user))
        dmg_after_def = int(dmg_after_def * rage_mult)
        crit_chance = eff["dex"] + racial_crit_bonus(user) + get_crit_bonus(user) + race_crit_bonus
        if user.get("pet_type") == "owl":
            crit_chance += 15
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit:
            dmg_after_def = int(dmg_after_def * 2)
        dmg = int(dmg_after_def * faction_mult(user, "dmg_mult") * next_mult * range_bonus)
        if next_mult != 1.0:
            await g.db.set_next_atk_mult(user["user_id"], 1.0)
        pet_dmg, pet_text = pet_attack_damage(user, combat["round_num"])
        total_dmg = dmg + pet_dmg
        new_enemy_hp = combat["enemy_hp"] - total_dmg
        await g.db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
        line = f"⚔️ {dmg} урона" + (" 💥 КРИТ!" if is_crit else "")
        if range_bonus > 1.0:
            line += " 🎯 <i>(преимущество дальнего боя)</i>"
        if rage_mult > 1.05:
            line += f" 😈 <i>(ярость ×{rage_mult:.2f})</i>"
        if pet_dmg > 0:
            line += f"\n  {pet_text} — {pet_dmg}!"
        log.append(line)
        # Вампиризм расы
        if race_lifesteal > 0 and total_dmg > 0:
            heal = int(total_dmg * race_lifesteal)
            new_hp = min(user["max_hp"], user["hp"] + heal)
            await g.db.update_hp(user["user_id"], new_hp)
            user["hp"] = new_hp
            log.append(f"😈 Вампиризм: +{heal} HP")

    elif action == "defend":
        log.append("🛡 Защита")

    elif action == "spoil":
        await g.db.set_combat_spoil_used(user["user_id"])
        log.append("🌿 Спойл: моб помечен — при убийстве есть шанс на редкий материал")

    elif action.startswith("skill_"):
        skill_code = action.replace("skill_", "")
        s = get_skill(skill_code)
        if not s:
            log.append("⚠️ Скил не найден")
            return new_enemy_hp, enemy_skip
        mp_cost = s["mp_cost"]
        if user["mp"] < mp_cost:
            log.append(f"❌ «{s['name']}» — не хватило MP ({user['mp']}/{mp_cost})")
            return new_enemy_hp, enemy_skip
        await g.db.spend_mp(user["user_id"], mp_cost)
        user["mp"] -= mp_cost
        mult = skill_multiplier(user, skill_code)
        effect = s["effect"]
        if effect == "damage":
            t_pdef = enemy_p_def(combat["enemy_level"])
            t_mdef = enemy_m_def(combat["enemy_level"])
            dmg_type = get_dmg_type(user)
            # pierce — игнорирует защиту
            if s.get("pierce"):
                base_dmg = calc_damage(user)
            else:
                base_dmg, _ = calc_final_damage_safe(user, t_pdef, t_mdef)
            if dmg_type == "magic":
                base_dmg = int(base_dmg * racial_magic_mult(user) * race_magic_mult)
            else:
                base_dmg = int(base_dmg * race_dmg_mult)
            base_dmg = int(base_dmg * racial_low_hp_mult(user) * rage_mult)
            dmg = int(base_dmg * mult * faction_mult(user, "dmg_mult") * range_bonus)
            # double — двойной удар
            if s.get("double"):
                dmg *= 2
            # execute — добивание при HP врага < 20%
            if s.get("execute") and new_enemy_hp < combat["enemy_max_hp"] * 0.20:
                dmg = int(dmg * s["execute"])
                log.append(f"✨ {s['name']}: <b>ДОБИВАНИЕ!</b> ×{s['execute']}")
            if s.get("pierce"):
                log.append(f"✨ {s['name']} (игнор брони): {dmg} урона")
            else:
                log.append(f"✨ {s['name']}: {dmg} урона")
            new_enemy_hp = combat["enemy_hp"] - dmg
            await g.db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
            # lifesteal
            if s.get("lifesteal") and dmg > 0:
                heal = int(dmg * s["lifesteal"])
                new_hp = min(user["max_hp"], user["hp"] + heal)
                await g.db.update_hp(user["user_id"], new_hp)
                user["hp"] = new_hp
                log.append(f"💗 Вампиризм скилла: +{heal} HP")
        elif effect == "heal":
            heal = int(user["max_hp"] * mult * racial_heal_mult(user))
            new_hp = min(user["max_hp"], user["hp"] + heal)
            await g.db.update_hp(user["user_id"], new_hp)
            user["hp"] = new_hp
            log.append(f"✨ {s['name']}: +{heal} HP")
        elif effect == "buff_atk":
            await g.db.set_next_atk_mult(user["user_id"], mult)
            log.append(f"✨ {s['name']}: +{int((mult-1)*100)}% атака")
        elif effect == "buff_def":
            log.append(f"✨ {s['name']}: защита активна")
        elif effect == "debuff":
            log.append(f"✨ {s['name']}: враг ослаблен")
        elif effect == "stun":
            enemy_skip = True
            log.append(f"✨ {s['name']}: враг оглушён!")

    elif action == "potion_hp":
        if user["hp"] >= user["max_hp"]:
            log.append("💚 HP полное — зелье не использовано")
            return new_enemy_hp, enemy_skip
        if user["gold"] < POTION_PRICE:
            log.append(f"❌ Нет {POTION_PRICE}💰 на зелье HP")
            return new_enemy_hp, enemy_skip
        await g.db.spend_gold(user["user_id"], POTION_PRICE)
        before = user["hp"]
        new_hp = min(user["max_hp"], user["hp"] + POTION_HEAL)
        await g.db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        log.append(f"💚 Зелье HP: {before} → {new_hp} (+{new_hp - before})")

    elif action == "potion_mp":
        if user["mp"] >= user["max_mp"]:
            log.append("🔮 MP полное — зелье не использовано")
            return new_enemy_hp, enemy_skip
        if user["gold"] < MP_POTION_PRICE:
            log.append(f"❌ Нет {MP_POTION_PRICE}💰 на зелье MP")
            return new_enemy_hp, enemy_skip
        await g.db.spend_gold(user["user_id"], MP_POTION_PRICE)
        before = user["mp"]
        new_mp = min(user["max_mp"], user["mp"] + MP_POTION_RESTORE)
        await g.db.update_mp(user["user_id"], new_mp)
        user["mp"] = new_mp
        log.append(f"🔮 Зелье MP: {before} → {new_mp} (+{new_mp - before})")

    return new_enemy_hp, enemy_skip


async def _exec_enemy_turn(chat_id, user, combat, log, def_mult=1.0):
    # Уклонение (плут)
    dodge = get_racial_combat_bonus(user, "dodge", 0)
    if dodge > 0 and random.randint(1, 100) <= dodge:
        log.append(f"💨 <b>Уклонение!</b> Ты избежал атаки врага")
        return False

    n_actions, dmg_mult = _get_enemy_actions(combat)
    enemy_dmg_type = get_enemy_dmg_type(combat["enemy_name"])
    player_def = get_player_def_for_enemy(user, enemy_dmg_type)
    phase = get_boss_phase(combat)
    phase_mult = phase["dmg_mult"] if phase else 1.0
    total_raw = 0
    for _ in range(n_actions):
        raw = calc_enemy_base_dmg(combat["enemy_level"], user["level"],
                                   is_boss=bool(combat["is_boss"]))
        total_raw += int(raw * dmg_mult * phase_mult)
    total_dmg = apply_player_defense(total_raw, player_def)
    total_dmg = int(total_dmg * def_mult)

    block_chance = get_block_chance(user)
    if block_chance > 0 and random.randint(1, 100) <= block_chance:
        log.append(f"🛡 <b>Блок!</b> Все {n_actions} атак отражены")
        return False
    new_hp = max(0, user["hp"] - total_dmg)
    await g.db.update_hp(user["user_id"], new_hp)
    user["hp"] = new_hp
    if total_dmg > 0:
        await g.db.incr_combat_dmg_taken(user["user_id"], total_dmg)
    if n_actions == 1:
        log.append(f"💔 Враг: {total_dmg} урона")
    else:
        log.append(f"💔 Враг ×{n_actions} — итого {total_dmg}")
    if phase:
        log.append(f"{phase['name']}: {phase['desc']}")
    if user["hp"] <= 0:
        await handle_death(chat_id, user, combat)
        return True
    return False


# ================= РАУНД =================
async def execute_queued_round(chat_id, user, combat, edit_message=None):
    event = await g.db.get_active_event(user.get("location_code", "village"))
    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []

    if not pending:
        await send_combat_state(chat_id, user, combat,
            "⚠️ Добавь хотя бы одно действие.", event,
            edit_message=edit_message)
        return False

    defends_count = sum(1 for a in pending if a == "defend")
    def_mult = DEFEND_MULT_BY_COUNT.get(defends_count, 1.0)

    player_log = []
    new_enemy_hp = combat["enemy_hp"]
    enemy_skip = False

    for action in pending:
        if new_enemy_hp <= 0:
            break
        cur_combat = dict(combat)
        cur_combat["enemy_hp"] = new_enemy_hp
        prev_hp = new_enemy_hp
        new_hp_enemy, en_skip = await _exec_player_action(
            user, cur_combat, action, player_log
        )
        new_enemy_hp = new_hp_enemy
        dmg_dealt = prev_hp - new_enemy_hp
        if dmg_dealt > 0:
            await g.db.incr_combat_dmg_dealt(user["user_id"], dmg_dealt)
        if en_skip:
            enemy_skip = True
        user = await g.db.get_user(user["user_id"])

    await g.db.clear_pending_actions(user["user_id"])

    if new_enemy_hp <= 0:
        await handle_victory(chat_id, user, combat, "\n".join(player_log))
        return False

    if defends_count > 0:
        pct = int((1 - def_mult) * 100)
        player_log.append(f"🛡 Защита ×{defends_count}: урон врага −{pct}%")

    enemy_log = []
    if not enemy_skip:
        dead = await _exec_enemy_turn(chat_id, user, combat, enemy_log, def_mult)
        if dead:
            return False
    else:
        enemy_log.append("💫 Враг пропускает ход")

    if user.get("max_mp", 0) > 0:
        regen = max(1, int(user["max_mp"] * 0.05))
        new_mp = min(user["max_mp"], user["mp"] + regen)
        if new_mp > user["mp"]:
            await g.db.update_mp(user["user_id"], new_mp)
            user["mp"] = new_mp

    summary = ""
    if player_log:
        summary += "<b>🗡 Твой ход:</b>\n" + "\n".join(f"  {ln}" for ln in player_log)
    if enemy_log:
        if summary:
            summary += "\n\n"
        summary += "<b>💀 Ответ врага:</b>\n" + "\n".join(f"  {ln}" for ln in enemy_log)

    await g.db.incr_combat_round(user["user_id"])
    user = await g.db.get_user(user["user_id"])
    await send_combat_state(chat_id, user,
                            await g.db.get_combat(user["user_id"]),
                            summary, event, edit_message=edit_message)
    return True


# ================= ДРОП С БОССОВ =================
async def _roll_boss_drop(uid, boss_name, boss_level, is_world_boss=False):
    drops = []
    for code, b in SKILL_BOOKS.items():
        if boss_name not in b.get("drop_boss", []):
            continue
        chance = b["chance"]
        if is_world_boss:
            chance *= 2
        if random.random() <= chance:
            await g.db.add_item(uid, b["name"])
            drops.append(("📖 Книга", b["name"]))

    if boss_level < 15:
        pool = [r for r, d in RECIPES.items() if d.get("grade") == "D"]
        chance = 0.05
    elif boss_level < 30:
        pool = [r for r, d in RECIPES.items() if d.get("grade") == "C"]
        chance = 0.05
    else:
        pool = [r for r, d in RECIPES.items() if d.get("grade") == "B"]
        chance = 0.03
    if is_world_boss:
        chance *= 2
    if pool and random.random() <= chance:
        recipe = random.choice(pool)
        recipe_item = f"📜 Рецепт: {recipe}"
        await g.db.add_item(uid, recipe_item)
        await g.db.learn_recipe(uid, recipe)
        drops.append(("📜 Рецепт", recipe))

    for mat_code, mat_data in RARE_MATERIALS.items():
        if boss_name in mat_data.get("mobs", []):
            if random.random() <= mat_data.get("chance", 0.10):
                await g.db.add_rare_material(uid, mat_code, 1)
                drops.append(("💠 Материал", mat_data["name"]))
    return drops


# ================= ПОБЕДА =================
async def handle_victory(chat_id, user, combat, prefix_text):
    from services.dungeon_service import dungeon_finish
    await g.db.end_combat(user["user_id"])
    marker = f"\n[БОЙ ОКОНЧЕН: {combat['enemy_name']} побеждён]\n"
    story_now = user.get("story") or ""
    await g.db.update_story(user["user_id"], (story_now + marker)[-4000:])

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

    base_exp = combat["enemy_level"] * 15
    if combat["is_boss"]:
        base_exp *= 3
    exp = calc_xp_reward(combat["enemy_level"], user["level"], base_exp)

    gold = combat["enemy_level"] * 10
    is_dungeon = combat.get("is_dungeon", 0)
    if combat["is_boss"]:
        gold *= 3
    gold = int(gold * faction_mult(user, "gold_mult") * racial_gold_mult(user)
               * get_gold_mult(user))

    event = await g.db.get_active_event(user.get("location_code", "village"))
    xp_mult = event.get("xp_mult", 1.0) if event else 1.0
    gold_mult_ev = event.get("gold_mult", 1.0) if event else 1.0
    exp = int(exp * xp_mult)
    gold = int(gold * gold_mult_ev)

    if user.get("pet_type"):
        await g.db.add_pet_xp(user["user_id"], combat["enemy_level"] * 5)

    spoil_reward = None
    if combat.get("spoil_used") and user.get("class") in SPOIL_CLASSES:
        for mat_code, mat_data in RARE_MATERIALS.items():
            if enemy_name in mat_data.get("mobs", []):
                if random.random() <= mat_data.get("chance", 0.15):
                    await g.db.add_rare_material(user["user_id"], mat_code, 1)
                    spoil_reward = mat_data["name"]
                    break

    boss_drops = []
    if combat["is_boss"]:
        boss_drops = await _roll_boss_drop(
            user["user_id"], enemy_name, combat["enemy_level"]
        )

    # ==================== ПОДЗЕМЕЛЬЕ ====================
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
        await g.db.add_season_xp(user["user_id"], combat["enemy_level"] * 2)

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
    # ==================== КОНЕЦ ПОДЗЕМЕЛЬЯ ====================

    await g.db.add_gold(user["user_id"], gold)
    level, xp, leveled_up = await g.db.add_xp(user["user_id"], exp)

    season_exp = combat["enemy_level"] * 2
    if combat["is_boss"]:
        season_exp *= 5
    await g.db.add_season_xp(user["user_id"], season_exp)

    diff = combat["enemy_level"] - user["level"]
    xp_note = ""
    if diff >= 3:
        xp_note = " 🔥"
    elif diff <= -5:
        xp_note = " 💤"

    rounds = combat.get("round_num", 1)
    dmg_dealt = combat.get("total_dmg_dealt", 0)
    dmg_taken = combat.get("total_dmg_taken", 0)
    boss_label = " 🐉" if combat["is_boss"] else ""

    text = (
        f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>ИТОГИ БОЯ</b>\n"
        f"⚔️ Противник: <b>{combat['enemy_name']}</b> "
        f"(ур. {combat['enemy_level']}){boss_label}\n"
        f"🎯 Раундов: <b>{rounds}</b>\n"
        f"💥 Нанесено: <b>{dmg_dealt}</b>\n"
        f"💔 Получено: <b>{dmg_taken}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"+{exp} XP{xp_note} · +{gold}💰"
    )

    if event:
        text += f"\n<i>{event['event_name']} усиливает награду</i>"

    if spoil_reward:
        text += f"\n\n🌿 <b>Спойл:</b> +{spoil_reward}"
        await notify_drop(chat_id, spoil_reward, source="🌿 Спойл")

    if combat["is_boss"]:
        await g.db.incr_bosses(user["user_id"])
        await g.db.add_world_event(user["user_id"], user["username"],
                                   f"победил босса «{combat['enemy_name']}»")
        await g.db.add_journal_entry(user["user_id"],
                                      f"Победил босса «{combat['enemy_name']}»", "boss")
        await g.db.update_hp(user["user_id"], user["max_hp"])
        text += f"\n\n🐉 <b>БОСС ПОВЕРЖЕН!</b> HP восстановлено."
        await notify_boss(chat_id, combat["enemy_name"])

        if await g.db.add_achievement(user["user_id"], "first_boss"):
            text += "\n🏆 Достижение: ⚔️ Убийца боссов"
            await notify_achievement(chat_id, "⚔️ Убийца боссов")

        for cat, name in boss_drops:
            text += f"\n{cat}: <b>{name}</b>"
            if "Книга" in cat:
                await notify_book(chat_id, name)
            elif "Рецепт" in cat:
                await notify_recipe(chat_id, name)
            elif "Материал" in cat:
                await notify_drop(chat_id, name, source="Спойл с босса")

    if random.randint(1, 100) <= 30:
        item = random.choice(DROP_TABLE)
        await g.db.add_item(user["user_id"], item)
        text += f"\n\n🎒 <b>Добыча:</b> {item}"
        await notify_item(chat_id, item)

    if user.get("pet_type") == "owl" and random.randint(1, 100) <= 20:
        mat = random.choice(["iron", "leather", "dust", "crystal"])
        await g.db.add_material(user["user_id"], mat, 1)
        text += f"\n🔨 Сова нашла: {MATERIAL_NAMES[mat]}"

    if leveled_up:
        u = await g.db.get_user(user["user_id"])
        nm = calc_max_hp(u)
        nmp = calc_max_mp(u)
        await g.db.update_hp_max(user["user_id"], nm, nm)
        await g.db.update_mp(user["user_id"], nmp)
        async with g.db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET skill_points = skill_points + 1 WHERE user_id=$1",
                user["user_id"]
            )
        text += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm} · MP: {nmp} · +1 очко умений"
        await notify_level(chat_id, level, nm, nmp)
        if level in (5, 10, 15, 20, 30):
            await g.db.add_journal_entry(user["user_id"],
                                          f"Достиг {level} уровня", "level")
        if level in (5, 10, 15, 20):
            await g.db.add_world_event(user["user_id"], user["username"],
                                       f"достиг {level} уровня!")

    if await g.db.add_achievement(user["user_id"], "first_blood"):
        text += "\n🏆 Достижение: 🩸 Первая кровь"
        await notify_achievement(chat_id, "🩸 Первая кровь")

    u = await g.db.get_user(user["user_id"])
    if u["bosses_defeated"] >= 5:
        if await g.db.add_achievement(user["user_id"], "boss_5"):
            text += "\n🏆 Достижение: 🐉 Легенда"
            await notify_achievement(chat_id, "🐉 Легенда — 5 боссов")

    await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)


# ================= СМЕРТЬ =================
async def handle_death(chat_id, user, combat):
    if (user.get("pet_type") == "ephoenix"
            and not combat.get("phoenix_used")):
        await g.db.set_combat_phoenix_used(user["user_id"])
        new_hp = max(1, user["max_hp"] // 2)
        await g.db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        await send_combat_state(
            chat_id, user,
            await g.db.get_combat(user["user_id"]),
            "🦅 <b>ФЕНИКС ВЕЧНОСТИ ВОЗРОДИЛ ТЕБЯ!</b>\nHP: 50%."
        )
        return

    was_dungeon = combat.get("is_dungeon", 0)
    await g.db.end_combat(user["user_id"])
    marker = f"\n[БОЙ ОКОНЧЕН: игрок пал в бою с {combat['enemy_name']}]\n"
    story_now = user.get("story") or ""
    await g.db.update_story(user["user_id"], (story_now + marker)[-4000:])

    if was_dungeon:
        await g.db.exit_dungeon(user["user_id"])
    lost = int(user["gold"] * 0.30)
    await g.db.set_gold(user["user_id"], user["gold"] - lost)
    u = await g.db.get_user(user["user_id"])
    nm = calc_max_hp(u)
    await g.db.update_hp_max(user["user_id"], nm, nm)
    await g.db.incr_deaths(user["user_id"])
    await g.db.add_achievement(user["user_id"], "survivor")
    await g.db.add_world_event(user["user_id"], user["username"],
                               f"пал в бою с «{combat['enemy_name']}»")
    await g.db.add_journal_entry(user["user_id"],
                                  f"Пал в бою с «{combat['enemy_name']}»", "death")

    rounds = combat.get("round_num", 1)
    dmg_dealt = combat.get("total_dmg_dealt", 0)
    dmg_taken = combat.get("total_dmg_taken", 0)

    text = (f"💀 <b>ТЫ ПАЛ В БОЮ</b>\n\n"
            f"<b>{combat['enemy_name']}</b> оказался сильнее.\n\n"
            f"Ты очнулся в Начальной деревне.\n"
            f"Жрецы забрали <b>{lost}💰</b> (30%).")
    if was_dungeon:
        text += "\n\n⚠️ <b>Вся добыча из подземелья потеряна!</b>"
    text += (f"\n\n━━━━━━━━━━━━━━━━━━━\n"
             f"📊 <b>ИТОГИ БОЯ</b>\n"
             f"🎯 Раундов: {rounds}\n"
             f"💥 Нанесено: {dmg_dealt}\n"
             f"💔 Получено: {dmg_taken}\n"
             f"━━━━━━━━━━━━━━━━━━━\n\n"
             f"❤️ HP: {nm}/{nm}\n💰 Золото: {u['gold'] - lost}\n\n"
             f"<i>Уровень и опыт сохранены.</i>")
    await g.db.set_location_code(user["user_id"], "village")
    await g.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
