"""Логика боя 2.0: P.Def/M.Def игрока, умный XP, фазы боссов."""
import json
import random

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import (
    DUNGEONS, DROP_TABLE, MATERIAL_NAMES,
    POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE,
)
from core.formulas import (
    calc_max_hp, calc_max_mp, danger_emoji, effective_stats,
    faction_mult, hp_bar, calc_damage, get_dmg_type,
    enemy_p_def, enemy_m_def, apply_defense,
    racial_crit_bonus, racial_magic_mult, racial_heal_mult,
    racial_gold_mult, racial_low_hp_mult,
    calc_xp_reward, calc_enemy_base_dmg,
    get_enemy_dmg_type, get_player_def_for_enemy, apply_player_defense,
    get_boss_phase,
    get_block_chance, get_crit_bonus, get_gold_mult,
)
from core.keyboards import combat_kb, dungeon_continue_kb
from core.game_data import PETS
from core.skills import get_skill, skill_multiplier
import world as W


# ================= ВСПОМОГАТЕЛЬНАЯ =================
def calc_final_damage_safe(user, t_pdef, t_mdef):
    """Урон игрока по врагу с учётом защиты врага."""
    base = calc_damage(user)
    dmg_type = get_dmg_type(user)
    if dmg_type == "magic":
        final = apply_defense(base, t_mdef)
    else:
        final = apply_defense(base, t_pdef)
    return final, dmg_type


# ================= СОСТОЯНИЕ БОЯ =================
async def send_combat_state(chat_id, user, combat, round_text="", event=None):
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
    if phase:
        header += f" · {phase['name']}"

    enemy_block = (f"{emoji} <b>{combat['enemy_name']}</b>"
                   f"{type_label} (Ур. {combat['enemy_level']}){boss_label}{phase_label}\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")

    pet_line = ""
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"], {})
        pet_line = f"\n🐾 {user.get('pet_name', pet.get('name', 'Питомец'))} (ур. {user.get('pet_level', 1)})"

    mp = user.get("mp", 0)
    max_mp = user.get("max_mp", 0)
    mp_line = f"\n💧 MP: {mp}/{max_mp}" if max_mp else ""

    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']}){pet_line}\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}{mp_line}\n"
                    f"💰 {user['gold']}")

    text = f"{header}\n\n{enemy_block}\n\n{player_block}"
    if round_text:
        text += f"\n\n{round_text}"

    try:
        active = json.loads(user.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    await g.bot.send_message(chat_id, text,
                             reply_markup=combat_kb(active, mp),
                             parse_mode=ParseMode.HTML)


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


# ================= РАУНД =================
async def process_combat_round(chat_id, user, combat, action_type, extra_text=""):
    event = await g.db.get_active_event(user.get("location_code", "village"))
    base_enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0

    new_enemy_hp = combat["enemy_hp"]
    enemy_skip = False
    def_reduce = 1.0
    enemy_debuff = 1.0

    # ---------- ДЕЙСТВИЕ ИГРОКА ----------
    if action_type == "attack":
        eff = effective_stats(user)
        next_mult = combat.get("next_atk_mult", 1.0) or 1.0
        t_pdef = enemy_p_def(combat["enemy_level"])
        t_mdef = enemy_m_def(combat["enemy_level"])
        dmg_after_def, dmg_type = calc_final_damage_safe(user, t_pdef, t_mdef)

        if dmg_type == "magic":
            dmg_after_def = int(dmg_after_def * racial_magic_mult(user))
        dmg_after_def = int(dmg_after_def * racial_low_hp_mult(user))

        crit_chance = (eff["dex"]
                       + racial_crit_bonus(user)
                       + get_crit_bonus(user))
        if user.get("pet_type") == "owl":
            crit_chance += 15
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit:
            dmg_after_def = int(dmg_after_def * 2)

        dmg = int(dmg_after_def * faction_mult(user, "dmg_mult") * next_mult)
        if next_mult != 1.0:
            await g.db.set_next_atk_mult(user["user_id"], 1.0)

        pet_dmg, pet_text = pet_attack_damage(user, combat["round_num"])
        total_dmg = dmg + pet_dmg
        new_enemy_hp = combat["enemy_hp"] - total_dmg
        await g.db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)

        parts = []
        if is_crit:
            parts.append(f"💥 <b>КРИТ!</b> {dmg}")
        else:
            parts.append(f"⚔️ {dmg} урона")
        if next_mult != 1.0:
            parts[0] += f" (бафф ×{next_mult:.2f})"
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
        def_reduce = 0.5
        extra_text = f"🛡 Защита: +{heal} HP, −50% получаемого урона"

    elif action_type == "skill":
        skill_code = extra_text.strip()
        s = get_skill(skill_code)
        if not s:
            extra_text = "⚠️ Скил не найден."
        else:
            mp_cost = s["mp_cost"]
            if user["mp"] < mp_cost:
                await send_combat_state(chat_id, user, combat,
                    f"❌ Не хватает MP ({user['mp']}/{mp_cost})", event)
                return True

            await g.db.spend_mp(user["user_id"], mp_cost)
            user["mp"] -= mp_cost

            mult = skill_multiplier(user, skill_code)
            effect = s["effect"]

            if effect == "damage":
                t_pdef = enemy_p_def(combat["enemy_level"])
                t_mdef = enemy_m_def(combat["enemy_level"])
                base_dmg, dmg_type = calc_final_damage_safe(user, t_pdef, t_mdef)
                if dmg_type == "magic":
                    base_dmg = int(base_dmg * racial_magic_mult(user))
                base_dmg = int(base_dmg * racial_low_hp_mult(user))
                dmg = int(base_dmg * mult * faction_mult(user, "dmg_mult"))
                new_enemy_hp = combat["enemy_hp"] - dmg
                await g.db.update_combat_enemy_hp(user["user_id"], new_enemy_hp)
                extra_text = f"✨ <b>{s['name']}</b> — {dmg} урона (−{mp_cost} MP)"

            elif effect == "heal":
                heal = int(user["max_hp"] * mult * racial_heal_mult(user))
                new_hp = min(user["max_hp"], user["hp"] + heal)
                await g.db.update_hp(user["user_id"], new_hp)
                user["hp"] = new_hp
                extra_text = f"✨ <b>{s['name']}</b> — +{heal} HP (−{mp_cost} MP)"

            elif effect == "buff_atk":
                await g.db.set_next_atk_mult(user["user_id"], mult)
                extra_text = (f"✨ <b>{s['name']}</b> — "
                              f"+{int((mult-1)*100)}% к следующей атаке (−{mp_cost} MP)")

            elif effect == "buff_def":
                def_reduce = mult
                extra_text = (f"✨ <b>{s['name']}</b> — "
                              f"−{int((1-mult)*100)}% урона (−{mp_cost} MP)")

            elif effect == "debuff":
                enemy_debuff = mult
                extra_text = (f"✨ <b>{s['name']}</b> — "
                              f"атака врага −{int((1-mult)*100)}% (−{mp_cost} MP)")

            elif effect == "stun":
                enemy_skip = True
                extra_text = f"✨ <b>{s['name']}</b> — враг оглушён! (−{mp_cost} MP)"

    # ---------- ПОБЕДА? ----------
    if new_enemy_hp <= 0:
        await handle_victory(chat_id, user, combat, extra_text)
        return False

    # ---------- ХОД ВРАГА ----------
    if not enemy_skip:
        if user.get("pet_type") == "phoenix":
            plvl = user.get("pet_level", 1)
            heal = int(user["max_hp"] * 0.05) + plvl
            new_hp = min(user["max_hp"], user["hp"] + heal)
            if new_hp > user["hp"]:
                await g.db.update_hp(user["user_id"], new_hp)
                user["hp"] = new_hp
                extra_text += f"\n🔥 Феникс лечит +{heal} HP"

        phase = get_boss_phase(combat)
        attacks = phase["attacks"] if phase else 1
        phase_mult = phase["dmg_mult"] if phase else 1.0

        total_enemy_dmg = 0

        for _ in range(attacks):
            raw_dmg = calc_enemy_base_dmg(combat["enemy_level"], user["level"],
                                          is_boss=bool(combat["is_boss"]))
            enemy_dmg_type = get_enemy_dmg_type(combat["enemy_name"])
            player_def = get_player_def_for_enemy(user, enemy_dmg_type)
            mitigated = apply_player_defense(raw_dmg, player_def)
            final = int(mitigated * base_enemy_dmg_mult * def_reduce
                        * enemy_debuff * phase_mult)
            final = max(1, final)
            total_enemy_dmg += final

        # Проверка блока (Эгида Богов)
        block_chance = get_block_chance(user)
        is_blocked = False
        if block_chance > 0 and random.randint(1, 100) <= block_chance:
            is_blocked = True

        if is_blocked:
            extra_text += (f"\n🛡 <b>Блок!</b> "
                           f"{combat['enemy_name']} атака отражена "
                           f"(шанс {block_chance}%)")
        else:
            new_hp = max(0, user["hp"] - total_enemy_dmg)
            await g.db.update_hp(user["user_id"], new_hp)
            user["hp"] = new_hp

            if attacks > 1:
                extra_text += (f"\n💔 {combat['enemy_name']} атакует ×2 — "
                               f"итого {total_enemy_dmg}")
            else:
                extra_text += f"\n💔 {combat['enemy_name']} наносит {total_enemy_dmg}"

        if phase:
            extra_text += f"\n{phase['name']}: {phase['desc']}"

    else:
        extra_text += f"\n💫 {combat['enemy_name']} пропускает ход"

    if user.get("max_mp", 0) > 0:
        regen = max(1, int(user["max_mp"] * 0.05))
        new_mp = min(user["max_mp"], user["mp"] + regen)
        if new_mp > user["mp"]:
            await g.db.update_mp(user["user_id"], new_mp)
            user["mp"] = new_mp

    if user["hp"] <= 0:
        await handle_death(chat_id, user, combat)
        return False

    await g.db.incr_combat_round(user["user_id"])
    await send_combat_state(chat_id, user,
                            await g.db.get_combat(user["user_id"]), extra_text, event)
    return True


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

    # ---- XP ----
    base_exp = combat["enemy_level"] * 15
    if combat["is_boss"]:
        base_exp *= 3
    exp = calc_xp_reward(combat["enemy_level"], user["level"], base_exp)

    # ---- Золото ----
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

    diff = combat["enemy_level"] - user["level"]
    if diff >= 3:
        xp_note = " 🔥 отличный опыт!"
    elif diff <= -5:
        xp_note = " 💤 слабый враг"
    else:
        xp_note = ""

    text = (f"🎉 <b>ПОБЕДА!</b>\n\n{prefix_text}\n\n"
            f"<b>{combat['enemy_name']}</b> повержен!\n"
            f"+{exp} XP{xp_note} · +{gold}💰")

    if event:
        text += f"\n<i>{event['event_name']} усиливает награду</i>"

    if combat["is_boss"]:
        await g.db.incr_bosses(user["user_id"])
        await g.db.add_world_event(user["user_id"], user["username"],
                                   f"победил босса «{combat['enemy_name']}»")
        await g.db.add_journal_entry(
            user["user_id"],
            f"Победил босса «{combat['enemy_name']}»",
            "boss"
        )
        loc_code = user.get("location_code", "village")
        await g.db.add_location_event(
            loc_code,
            f"победил босса «{combat['enemy_name']}»",
            "boss",
            user["username"]
        )
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
        nmp = calc_max_mp(u)
        await g.db.update_hp_max(user["user_id"], nm, nm)
        await g.db.update_mp(user["user_id"], nmp)
        async with g.db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET skill_points = skill_points + 1 WHERE user_id=$1",
                user["user_id"]
            )
        text += f"\n\n⭐ <b>Уровень {level}!</b> HP: {nm} · MP: {nmp} · +1 очко умений"

        if level in (5, 10, 15, 20, 30):
            await g.db.add_journal_entry(
                user["user_id"],
                f"Достиг {level} уровня",
                "level"
            )

        if level in (5, 10, 15, 20):
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
    if (user.get("pet_type") == "ephoenix"
            and not combat.get("phoenix_used")):
        await g.db.set_combat_phoenix_used(user["user_id"])
        new_hp = max(1, user["max_hp"] // 2)
        await g.db.update_hp(user["user_id"], new_hp)
        user["hp"] = new_hp
        await send_combat_state(
            chat_id, user,
            await g.db.get_combat(user["user_id"]),
            "🦅 <b>ФЕНИКС ВЕЧНОСТИ ВОЗРОДИЛ ТЕБЯ!</b>\n"
            "HP восстановлено на 50%. Второй раз не сработает."
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
    await g.db.add_journal_entry(
        user["user_id"],
        f"Пал в бою с «{combat['enemy_name']}»",
        "death"
    )
    loc_code = user.get("location_code", "village")
    await g.db.add_location_event(
        loc_code,
        f"пал в бою с «{combat['enemy_name']}»",
        "death",
        user["username"]
    )
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
