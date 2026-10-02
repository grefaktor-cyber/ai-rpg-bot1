"""Логика мировых боссов + рейд-боссы (2+ игрока) + очередь действий."""
import json
import random
import time
from datetime import datetime, timezone, timedelta

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import (
    DROP_TABLE,
    POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE,
)
from core.world_bosses import (
    WORLD_BOSSES, SPAWN_HOURS_MSK, GOLD_PER_1K_DAMAGE, XP_PER_1K_DAMAGE,
    TOP1_BONUS_ITEM_CHANCE, KILLER_BONUS_MULT,
    ATTACK_COOLDOWN_SEC, MIN_HP_PCT, DEATH_GOLD_LOSS_PCT,
)
from core.formulas import (
    calc_max_hp, effective_stats, calc_damage,
    racial_crit_bonus, get_crit_bonus,
    calc_boss_damage_to_player,
    enemy_p_def, enemy_m_def, apply_defense, get_dmg_type,
    faction_mult, racial_heal_mult, racial_magic_mult, racial_low_hp_mult,
)
from core.skills import get_skill, skill_multiplier
import world as W


# ================= РЕЙД-БОССЫ (СБАЛАНСИРОВАНО) =================
RAID_BOSSES = {
    "abyss_lord": {
        "name": "👹 Повелитель Бездны",
        "level": 45,
        "hp": 40000,
        "attack_dmg": 240,
        "dmg_type": "magic",
        "locations": ["cave", "mountains", "ruins"],
        "desc": ("Требует МИНИМУМ 2 игрока. "
                 "Каждые 5 атак восстанавливает 500 HP."),
        "raid": True,
        "min_players": 2,
        "heal_amount": 500,
        "heal_every_n": 5,
    },
    "world_devourer": {
        "name": "🐲 Пожиратель Миров",
        "level": 50,
        "hp": 70000,
        "attack_dmg": 300,
        "dmg_type": "phys",
        "locations": ["mountains", "ruins", "swamp"],
        "desc": ("Требует МИНИМУМ 3 игрока. "
                 "Каждые 5 атак восстанавливает 700 HP."),
        "raid": True,
        "min_players": 3,
        "heal_amount": 700,
        "heal_every_n": 5,
    },
}

WORLD_BOSSES.update(RAID_BOSSES)


# ================= МНОЖИТЕЛИ ЗАЩИТЫ =================
DEFEND_MULT_BY_COUNT = {
    0: 1.00,
    1: 0.70,
    2: 0.50,
    3: 0.35,
    4: 0.20,
}


_BOSS_COOLDOWN = {}


def check_cooldown(uid):
    now = time.time()
    last = _BOSS_COOLDOWN.get(uid, 0)
    elapsed = now - last
    if elapsed < ATTACK_COOLDOWN_SEC:
        return False, int(ATTACK_COOLDOWN_SEC - elapsed) + 1
    _BOSS_COOLDOWN[uid] = now
    return True, 0


def _now_msk():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def _parse_dt(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def should_spawn_now():
    now_msk = _now_msk()
    return now_msk.hour in SPAWN_HOURS_MSK


def is_raid_boss(boss_code):
    return boss_code in RAID_BOSSES


async def _count_players_in_location(loc_code, exclude_uid=0):
    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM users "
            "WHERE location_code=$1 AND char_name!='' AND user_id!=$2",
            loc_code, exclude_uid
        )
    return (row["cnt"] if row else 0) + 1


# ================= СПАВН =================
async def try_spawn_boss():
    if not should_spawn_now():
        return None
    active = await g.db.get_all_active_world_bosses()
    if active:
        return None
    last = await g.db.get_last_boss_spawn_time()
    if last:
        last_aware = _parse_dt(last)
        delta = datetime.now(timezone.utc) - last_aware
        if delta.total_seconds() < 60 * 60 * 5:
            return None

    normal_codes = [c for c in WORLD_BOSSES if c not in RAID_BOSSES]
    if not normal_codes:
        return None
    boss_code = random.choice(normal_codes)
    boss_data = WORLD_BOSSES[boss_code]
    loc_code = random.choice(boss_data["locations"])

    boss_id = await g.db.spawn_world_boss(boss_code, loc_code, boss_data["hp"])
    loc_name = W.get_location(loc_code).get("name", "?")

    async with g.db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE char_name!=''")
    for r in rows:
        try:
            await g.bot.send_message(
                r["user_id"],
                f"🐉 <b>МИРОВОЙ БОСС!</b>\n\n"
                f"<b>{boss_data['name']}</b> в «{loc_name}»!\n"
                f"HP: <b>{boss_data['hp']}</b>\n"
                f"⚔️ Урон: ~{boss_data['attack_dmg']} ({boss_data['dmg_type']})\n\n"
                f"⚠️ <i>{boss_data['desc']}</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
    return {"boss_id": boss_id, "boss_code": boss_code,
            "location_code": loc_code, "location_name": loc_name,
            "boss_name": boss_data["name"]}


async def force_spawn_boss(boss_code=None, location_code=None, notify=False):
    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM world_bosses WHERE killed=1 OR expires_at < NOW()"
        )

    if boss_code is None:
        boss_code = random.choice(list(WORLD_BOSSES.keys()))
    boss_data = WORLD_BOSSES.get(boss_code)
    if not boss_data:
        return {"error": f"boss '{boss_code}' не найден",
                "available": list(WORLD_BOSSES.keys())}

    if location_code is None:
        location_code = random.choice(boss_data["locations"])
    if location_code not in W.LOCATIONS:
        return {"error": f"локация '{location_code}' не найдена",
                "available": list(W.LOCATIONS.keys())}

    boss_id = await g.db.spawn_world_boss(boss_code, location_code, boss_data["hp"])
    loc_name = W.get_location(location_code).get("name", "?")
    is_raid = is_raid_boss(boss_code)

    if notify:
        async with g.db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM users WHERE char_name!=''")
        raid_tag = "⚔️ <b>РЕЙД-БОСС!</b>\n" if is_raid else ""
        min_p = boss_data.get("min_players", 1)
        raid_hint = (f"\n⚠️ <b>Требуется {min_p}+ игрока в локации!</b>\n"
                     if is_raid else "")
        for r in rows:
            try:
                await g.bot.send_message(
                    r["user_id"],
                    f"{raid_tag}🐉 <b>МИРОВОЙ БОСС!</b>\n\n"
                    f"<b>{boss_data['name']}</b> в «{loc_name}»!\n"
                    f"HP: <b>{boss_data['hp']}</b>\n"
                    f"⚔️ Урон: ~{boss_data['attack_dmg']} ({boss_data['dmg_type']})\n"
                    f"{raid_hint}\n"
                    f"⚠️ <i>{boss_data['desc']}</i>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

    return {
        "boss_id": boss_id, "boss_code": boss_code,
        "boss_name": boss_data["name"], "boss_level": boss_data["level"],
        "location_code": location_code, "location_name": loc_name,
        "hp": boss_data["hp"], "attack_dmg": boss_data["attack_dmg"],
        "dmg_type": boss_data["dmg_type"],
        "is_raid": is_raid, "min_players": boss_data.get("min_players", 1),
    }


# ================= АТАКА (старая, оставлена для совместимости) =================
async def attack_boss(uid):
    u = await g.db.get_user(uid)
    if not u["char_name"]:
        return False, {"error": "no_char"}

    ok_cd, sec_left = check_cooldown(uid)
    if not ok_cd:
        return False, {"error": "cooldown", "seconds": sec_left}

    hp_pct = u["hp"] / max(1, u["max_hp"])
    if hp_pct < MIN_HP_PCT:
        return False, {"error": "low_hp",
                       "hp": u["hp"], "max_hp": u["max_hp"],
                       "pct": int(MIN_HP_PCT * 100)}

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return False, {"error": "no_boss"}

    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    is_raid = is_raid_boss(boss["boss_code"])

    if is_raid:
        min_players = boss_data.get("min_players", 2)
        count = await _count_players_in_location(loc_code, exclude_uid=0)
        if count < min_players:
            return False, {
                "error": "not_enough_players",
                "min_players": min_players,
                "current": count,
            }

    eff = effective_stats(u)
    my_dmg = calc_damage(u)
    crit_chance = eff["dex"] + racial_crit_bonus(u) + get_crit_bonus(u)
    if u.get("pet_type") == "owl":
        crit_chance += 15
    is_crit = random.randint(1, 100) <= crit_chance
    if is_crit:
        my_dmg = int(my_dmg * 2)

    boss_atk = calc_boss_damage_to_player(u, boss_data, phase_mult=1.0)

    new_hp = max(0, u["hp"] - boss_atk)
    await g.db.update_hp(uid, new_hp)
    u["hp"] = new_hp

    await g.db.add_boss_damage(boss["id"], uid, u["char_name"], my_dmg)
    updated = await g.db.get_active_world_boss(loc_code)

    heal_amount = 0
    if is_raid and updated and updated["current_hp"] > 0:
        n = boss_data.get("heal_every_n", 5)
        attacks = await g.db.get_boss_attacks_count(boss["id"])
        if attacks > 0 and attacks % n == 0:
            heal_amount = boss_data.get("heal_amount", 0)
            if heal_amount > 0:
                await g.db.heal_world_boss(boss["id"], heal_amount)
                updated = await g.db.get_active_world_boss(loc_code)

    player_died = (new_hp <= 0)
    lost_gold = 0
    if player_died:
        lost_gold = int(u["gold"] * DEATH_GOLD_LOSS_PCT)
        await g.db.spend_gold(uid, lost_gold)
        nm = calc_max_hp(u)
        await g.db.update_hp_max(uid, nm, nm)
        await g.db.set_location_code(uid, "village")
        await g.db.incr_deaths(uid)
        await g.db.add_journal_entry(
            uid,
            f"Пал от мирового босса «{boss_data.get('name', '?')}»",
            "death"
        )

    killed = updated and updated["current_hp"] <= 0
    if killed:
        await _handle_boss_kill(updated, uid)

    return True, {
        "killed": killed,
        "boss": updated,
        "my_damage": my_dmg,
        "is_crit": is_crit,
        "boss_atk": boss_atk,
        "boss_dmg_type": boss_data.get("dmg_type", "phys"),
        "my_hp": new_hp,
        "player_died": player_died,
        "lost_gold": lost_gold,
        "is_raid": is_raid,
        "boss_heal": heal_amount,
    }


# ================= ОЧЕРЕДЬ ДЕЙСТВИЙ (НОВОЕ) =================
async def execute_boss_actions(uid, actions):
    """Прогоняет очередь действий игрока против мирового босса.

    actions: список строк — "attack", "defend", "potion_hp", "potion_mp",
             "skill_<code>"

    Возвращает (ok, info), где info — словарь с логом и результатом.
    """
    u = await g.db.get_user(uid)
    if not u["char_name"]:
        return False, {"error": "no_char"}

    if not actions:
        return False, {"error": "empty"}

    ok_cd, sec_left = check_cooldown(uid)
    if not ok_cd:
        return False, {"error": "cooldown", "seconds": sec_left}

    hp_pct = u["hp"] / max(1, u["max_hp"])
    if hp_pct < MIN_HP_PCT:
        return False, {"error": "low_hp",
                       "hp": u["hp"], "max_hp": u["max_hp"],
                       "pct": int(MIN_HP_PCT * 100)}

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return False, {"error": "no_boss"}

    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    is_raid = is_raid_boss(boss["boss_code"])

    # Рейд: проверка min_players
    if is_raid:
        min_players = boss_data.get("min_players", 2)
        count = await _count_players_in_location(loc_code, exclude_uid=0)
        if count < min_players:
            return False, {"error": "not_enough_players",
                           "min_players": min_players, "current": count}

    # === ПОДСЧЁТ ЗАЩИТЫ ===
    defends_count = sum(1 for a in actions if a == "defend")
    def_mult = DEFEND_MULT_BY_COUNT.get(defends_count, 1.0)

    log = []
    total_my_dmg = 0
    is_any_crit = False
    mp = u.get("mp", 0)
    max_mp = u.get("max_mp", 0)
    gold = u["gold"]
    hp = u["hp"]
    max_hp = u["max_hp"]

    # === ПРОХОД ПО ДЕЙСТВИЯМ ===
    for action in actions:
        if action == "attack":
            eff = effective_stats(u)
            base = calc_damage(u)
            t_pdef = enemy_p_def(boss_data.get("level", 40))
            t_mdef = enemy_m_def(boss_data.get("level", 40))
            dmg_type = get_dmg_type(u)
            dmg = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
            if dmg_type == "magic":
                dmg = int(dmg * racial_magic_mult(u))
            dmg = int(dmg * racial_low_hp_mult(u) * faction_mult(u, "dmg_mult"))
            crit_chance = eff["dex"] + racial_crit_bonus(u) + get_crit_bonus(u)
            if u.get("pet_type") == "owl":
                crit_chance += 15
            if random.randint(1, 100) <= crit_chance:
                dmg = int(dmg * 2)
                is_any_crit = True
                log.append(f"⚔️ Атака: {dmg} 💥 КРИТ!")
            else:
                log.append(f"⚔️ Атака: {dmg}")
            total_my_dmg += dmg

        elif action == "defend":
            log.append("🛡 Защита")

        elif action == "potion_hp":
            if hp >= max_hp:
                log.append("💚 HP полное, зелье не использовано")
            elif gold < POTION_PRICE:
                log.append(f"❌ Нет {POTION_PRICE}💰 на зелье HP")
            else:
                gold -= POTION_PRICE
                hp = min(max_hp, hp + POTION_HEAL)
                log.append(f"💚 Зелье HP: +{POTION_HEAL}")

        elif action == "potion_mp":
            if mp >= max_mp:
                log.append("🔮 MP полное, зелье не использовано")
            elif gold < MP_POTION_PRICE:
                log.append(f"❌ Нет {MP_POTION_PRICE}💰 на зелье MP")
            else:
                gold -= MP_POTION_PRICE
                mp = min(max_mp, mp + MP_POTION_RESTORE)
                log.append(f"🔮 Зелье MP: +{MP_POTION_RESTORE}")

        elif action.startswith("skill_"):
            code = action.replace("skill_", "")
            s = get_skill(code)
            if not s:
                log.append("⚠️ Скилл не найден")
                continue
            if mp < s["mp_cost"]:
                log.append(f"❌ Не хватило MP для «{s['name']}»")
                continue
            mp -= s["mp_cost"]
            mult = skill_multiplier(u, code)
            effect = s["effect"]
            if effect == "damage":
                base = calc_damage(u)
                t_pdef = enemy_p_def(boss_data.get("level", 40))
                t_mdef = enemy_m_def(boss_data.get("level", 40))
                dmg_type = get_dmg_type(u)
                dmg = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
                if dmg_type == "magic":
                    dmg = int(dmg * racial_magic_mult(u))
                dmg = int(dmg * mult * racial_low_hp_mult(u) * faction_mult(u, "dmg_mult"))
                total_my_dmg += dmg
                log.append(f"✨ {s['name']}: {dmg} урона")
            elif effect == "heal":
                heal = int(max_hp * mult * racial_heal_mult(u))
                hp = min(max_hp, hp + heal)
                log.append(f"✨ {s['name']}: +{heal} HP")
            elif effect == "buff_atk":
                log.append(f"✨ {s['name']}: бафф атаки")
            elif effect == "buff_def":
                log.append(f"✨ {s['name']}: защита активна")
            elif effect == "debuff":
                log.append(f"✨ {s['name']}: враг ослаблен")
            elif effect == "stun":
                log.append(f"✨ {s['name']}: враг оглушён")

    # === ОТВЕТ БОССА ===
    boss_atk_raw = calc_boss_damage_to_player(u, boss_data, phase_mult=1.0)
    boss_atk = int(boss_atk_raw * def_mult)
    if defends_count > 0:
        pct = int((1 - def_mult) * 100)
        log.append(f"🛡 Защита ×{defends_count}: урон босса −{pct}%")

    new_hp = max(0, hp - boss_atk)
    log.append(f"💔 Босс ответил: -{boss_atk}")

    # === ПРИМЕНЯЕМ К БД ===
    await g.db.update_hp(uid, new_hp)
    await g.db.update_mp(uid, mp)
    if gold != u["gold"]:
        await g.db.set_gold(uid, gold)

    # === УРОН БОССУ ===
    if total_my_dmg > 0:
        await g.db.add_boss_damage(boss["id"], uid, u["char_name"], total_my_dmg)
    updated = await g.db.get_active_world_boss(loc_code)

    # === РЕГЕНЕРАЦИЯ РЕЙД-БОССА (раз в N атак) ===
    heal_amount = 0
    if is_raid and updated and updated["current_hp"] > 0:
        n = boss_data.get("heal_every_n", 5)
        attacks = await g.db.get_boss_attacks_count(boss["id"])
        if attacks > 0 and attacks % n == 0:
            heal_amount = boss_data.get("heal_amount", 0)
            if heal_amount > 0:
                await g.db.heal_world_boss(boss["id"], heal_amount)
                updated = await g.db.get_active_world_boss(loc_code)

    # === СМЕРТЬ ИГРОКА ===
    player_died = (new_hp <= 0)
    lost_gold = 0
    if player_died:
        lost_gold = int(gold * DEATH_GOLD_LOSS_PCT)
        await g.db.spend_gold(uid, lost_gold)
        nm = calc_max_hp(u)
        await g.db.update_hp_max(uid, nm, nm)
        await g.db.set_location_code(uid, "village")
        await g.db.incr_deaths(uid)
        await g.db.add_journal_entry(
            uid,
            f"Пал от мирового босса «{boss_data.get('name', '?')}»",
            "death"
        )

    # === УБИЙСТВО БОССА ===
    killed = updated and updated["current_hp"] <= 0
    if killed:
        await _handle_boss_kill(updated, uid)

    return True, {
        "killed": killed,
        "boss": updated,
        "my_damage": total_my_dmg,
        "is_crit": is_any_crit,
        "boss_atk": boss_atk,
        "boss_dmg_type": boss_data.get("dmg_type", "phys"),
        "my_hp": new_hp,
        "player_died": player_died,
        "lost_gold": lost_gold,
        "is_raid": is_raid,
        "boss_heal": heal_amount,
        "log": log,
        "defends_count": defends_count,
        "def_mult": def_mult,
    }


# ================= НАГРАДЫ ЗА УБИЙСТВО =================
async def _handle_boss_kill(boss, killer_id):
    await g.db.kill_world_boss(boss["id"], killer_id)
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=50)
    if not damage_list:
        return

    boss_code = boss.get("boss_code", "")
    boss_data = WORLD_BOSSES.get(boss_code, {})
    boss_name = boss_data.get("name", "Босс")
    loc_name = W.get_location(boss["location_code"]).get("name", "?")
    is_raid = is_raid_boss(boss_code)

    for entry in damage_list:
        uid = entry["user_id"]
        damage = entry["damage"]
        gold = max(50, int((damage / 1000) * GOLD_PER_1K_DAMAGE))
        xp = max(100, int((damage / 1000) * XP_PER_1K_DAMAGE))

        if is_raid:
            gold = int(gold * 2)
            xp = int(xp * 2)

        is_killer = (uid == killer_id)
        if is_killer:
            gold = int(gold * KILLER_BONUS_MULT)

        is_top1 = (entry == damage_list[0])
        bonus_item = None
        if is_top1 and random.random() < TOP1_BONUS_ITEM_CHANCE:
            bonus_item = random.choice(DROP_TABLE)
            await g.db.add_item(uid, bonus_item)

        if is_raid and len(damage_list) >= 3:
            if entry in damage_list[:3] and random.random() < 0.5:
                bonus_raid_item = random.choice(DROP_TABLE)
                await g.db.add_item(uid, bonus_raid_item)
                if not bonus_item:
                    bonus_item = bonus_raid_item

        await g.db.add_gold(uid, gold)
        await g.db.add_xp(uid, xp)
        await g.db.add_journal_entry(
            uid,
            f"Победил мирового босса «{boss_name}»",
            "boss"
        )

        text = (f"🏆 <b>Мировой босс побеждён!</b>\n\n"
                f"<b>{boss_name}</b> в «{loc_name}»\n"
                f"Твой урон: <b>{damage}</b>\n"
                f"+{gold}💰 · +{xp} XP")
        if is_raid:
            text += "\n⚔️ <b>Рейд-босс! ×2 награды</b>"
        if is_killer:
            text += "\n🎯 <b>Последний удар — твой!</b> (+50% золота)"
        if is_top1:
            text += "\n🥇 <b>Топ-1 по урону!</b>"
        if bonus_item:
            text += f"\n🎁 Бонус: {bonus_item}"

        try:
            await g.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
