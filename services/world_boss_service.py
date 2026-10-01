"""Логика мировых боссов: спавн, атака с P.Def/M.Def, награды."""
import random
import time
from datetime import datetime, timezone, timedelta

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import DROP_TABLE
from core.world_bosses import (
    WORLD_BOSSES, SPAWN_HOURS_MSK, GOLD_PER_1K_DAMAGE, XP_PER_1K_DAMAGE,
    TOP1_BONUS_ITEM_CHANCE, KILLER_BONUS_MULT,
    ATTACK_COOLDOWN_SEC, MIN_HP_PCT, DEATH_GOLD_LOSS_PCT,
)
from core.formulas import (
    calc_max_hp, effective_stats, calc_damage,
    racial_crit_bonus, get_crit_bonus,
    calc_boss_damage_to_player,
)
import world as W


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


def should_spawn_now():
    now_msk = _now_msk()
    return now_msk.hour in SPAWN_HOURS_MSK


async def try_spawn_boss():
    if not should_spawn_now():
        return None

    active = await g.db.get_all_active_world_bosses()
    if active:
        return None

    last = await g.db.get_last_boss_spawn_time()
    if last:
        delta = datetime.now(timezone.utc) - last
        if delta.total_seconds() < 60 * 60 * 5:
            return None

    boss_code = random.choice(list(WORLD_BOSSES.keys()))
    boss_data = WORLD_BOSSES[boss_code]
    loc_code = random.choice(boss_data["locations"])

    boss_id = await g.db.spawn_world_boss(
        boss_code, loc_code, boss_data["hp"]
    )
    loc_name = W.get_location(loc_code).get("name", "?")

    async with g.db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM users WHERE char_name!=''"
        )
    for r in rows:
        try:
            await g.bot.send_message(
                r["user_id"],
                f"🐉 <b>МИРОВОЙ БОСС!</b>\n\n"
                f"<b>{boss_data['name']}</b> в «{loc_name}»!\n"
                f"HP: <b>{boss_data['hp']}</b>\n"
                f"⚔️ Урон: ~{boss_data['attack_dmg']} ({boss_data['dmg_type']})\n\n"
                f"⚠️ <i>{boss_data['desc']}</i>\n\n"
                f"<i>Живёт 2 часа. /boss в локации.</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    return {"boss_id": boss_id, "boss_code": boss_code,
            "location_code": loc_code, "location_name": loc_name,
            "boss_name": boss_data["name"]}


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

    # Урон игрока
    eff = effective_stats(u)
    my_dmg = calc_damage(u)
    crit_chance = eff["dex"] + racial_crit_bonus(u) + get_crit_bonus(u)
    if u.get("pet_type") == "owl":
        crit_chance += 15
    is_crit = random.randint(1, 100) <= crit_chance
    if is_crit:
        my_dmg = int(my_dmg * 2)

    # Ответный урон босса с учётом P.Def/M.Def игрока
    boss_atk = calc_boss_damage_to_player(u, boss_data, phase_mult=1.0)

    new_hp = max(0, u["hp"] - boss_atk)
    await g.db.update_hp(uid, new_hp)
    u["hp"] = new_hp

    await g.db.add_boss_damage(boss["id"], uid, u["char_name"], my_dmg)
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
    }


async def _handle_boss_kill(boss, killer_id):
    await g.db.kill_world_boss(boss["id"], killer_id)
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=50)
    if not damage_list:
        return

    boss_code = boss.get("boss_code", "")
    boss_data = WORLD_BOSSES.get(boss_code, {})
    boss_name = boss_data.get("name", "Босс")
    loc_name = W.get_location(boss["location_code"]).get("name", "?")

    for entry in damage_list:
        uid = entry["user_id"]
        damage = entry["damage"]
        gold = max(50, int((damage / 1000) * GOLD_PER_1K_DAMAGE))
        xp = max(100, int((damage / 1000) * XP_PER_1K_DAMAGE))

        is_killer = (uid == killer_id)
        if is_killer:
            gold = int(gold * KILLER_BONUS_MULT)

        is_top1 = (entry == damage_list[0])
        bonus_item = None
        if is_top1 and random.random() < TOP1_BONUS_ITEM_CHANCE:
            bonus_item = random.choice(DROP_TABLE)
            await g.db.add_item(uid, bonus_item)

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
        if is_killer:
            text += "\n⚔️ <b>Последний удар — твой!</b> (+50% золота)"
        if is_top1:
            text += "\n🥇 <b>Топ-1 по урону!</b>"
        if bonus_item:
            text += f"\n🎁 Бонус: {bonus_item}"

        try:
            await g.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
