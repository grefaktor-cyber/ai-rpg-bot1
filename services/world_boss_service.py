"""Логика мировых боссов: спавн, атака с ответным уроном, награды."""
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
)
import world as W


# Кулдаун игроков в памяти: uid -> timestamp
_BOSS_COOLDOWN = {}


def check_cooldown(uid):
    """Возвращает (ok, seconds_left)."""
    now = time.time()
    last = _BOSS_COOLDOWN.get(uid, 0)
    elapsed = now - last
    if elapsed < ATTACK_COOLDOWN_SEC:
        return False, int(ATTACK_COOLDOWN_SEC - elapsed) + 1
    _BOSS_COOLDOWN[uid] = now
    return True, 0


def _now_msk():
    """Текущее время по МСК (UTC+3)."""
    return datetime.now(timezone.utc) + timedelta(hours=3)


def should_spawn_now():
    """Проверить: сейчас время спавна?"""
    now_msk = _now_msk()
    return now_msk.hour in SPAWN_HOURS_MSK


async def try_spawn_boss():
    """Создать босса если сейчас время спавна и нет активных."""
    if not should_spawn_now():
        return None

    active = await g.db.get_all_active_world_bosses()
    if active:
        return None  # уже есть живой

    # Проверить: не спавнили ли уже в этом слоте
    last = await g.db.get_last_boss_spawn_time()
    if last:
        delta = datetime.now(timezone.utc) - last
        if delta.total_seconds() < 60 * 60 * 5:  # меньше 5 часов
            return None

    boss_code = random.choice(list(WORLD_BOSSES.keys()))
    boss_data = WORLD_BOSSES[boss_code]
    loc_code = random.choice(boss_data["locations"])

    boss_id = await g.db.spawn_world_boss(
        boss_code, loc_code, boss_data["hp"]
    )
    loc_name = W.get_location(loc_code).get("name", "?")

    # Broadcast всем
    async with g.db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM users WHERE char_name!=''"
        )
    for r in rows:
        try:
            await g.bot.send_message(
                r["user_id"],
                f"🐉 <b>МИРОВОЙ БОСС!</b>\n\n"
                f"<b>{boss_data['name']}</b> появился в «{loc_name}»!\n"
                f"HP: <b>{boss_data['hp']}</b>\n"
                f"Урон в ответ: ~{boss_data['attack_dmg']}\n\n"
                f"⚠️ <i>{boss_data['desc']}</i>\n\n"
                f"<i>Босс живёт 2 часа. Иди в локацию и напиши /boss.</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    return {"boss_id": boss_id, "boss_code": boss_code,
            "location_code": loc_code, "location_name": loc_name,
            "boss_name": boss_data["name"]}


async def attack_boss(uid, base_damage=None):
    """Атаковать босса. Возвращает (ok, info)."""
    u = await g.db.get_user(uid)
    if not u["char_name"]:
        return False, {"error": "no_char"}

    # Кулдаун
    ok_cd, sec_left = check_cooldown(uid)
    if not ok_cd:
        return False, {"error": "cooldown", "seconds": sec_left}

    # Проверка HP
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
    if base_damage is None:
        eff = effective_stats(u)
        base_damage = calc_damage(u)
        crit_chance = eff["dex"] + racial_crit_bonus(u) + get_crit_bonus(u)
        if u.get("pet_type") == "owl":
            crit_chance += 15
        is_crit = random.randint(1, 100) <= crit_chance
        if is_crit:
            base_damage = int(base_damage * 2)
    else:
        is_crit = False

    # Ответный урон босса
    boss_atk = boss_data.get("attack_dmg", 100)
    boss_atk = int(boss_atk * random.uniform(0.9, 1.1))
    new_hp = max(0, u["hp"] - boss_atk)
    await g.db.update_hp(uid, new_hp)
    u["hp"] = new_hp

    # Наносим урон боссу
    await g.db.add_boss_damage(boss["id"], uid, u["char_name"], base_damage)
    updated = await g.db.get_active_world_boss(loc_code)

    # Игрок умер от босса
    player_died = (new_hp <= 0)
    if player_died:
        lost = int(u["gold"] * DEATH_GOLD_LOSS_PCT)
        await g.db.spend_gold(uid, lost)
        nm = calc_max_hp(u)
        await g.db.update_hp_max(uid, nm, nm)
        await g.db.set_location_code(uid, "village")
        await g.db.incr_deaths(uid)
        await g.db.add_journal_entry(
            uid,
            f"Пал от мирового босса «{boss_data.get('name', '?')}»",
            "death"
        )

    # Босс убит?
    killed = updated and updated["current_hp"] <= 0
    if killed:
        await _handle_boss_kill(updated, uid)

    return True, {
        "killed": killed,
        "boss": updated,
        "my_damage": base_damage,
        "is_crit": is_crit,
        "boss_atk": boss_atk,
        "my_hp": new_hp,
        "player_died": player_died,
        "lost_gold": int(u["gold"] * DEATH_GOLD_LOSS_PCT) if player_died else 0,
    }


async def _handle_boss_kill(boss, killer_id):
    """Босс убит — выдаём награды."""
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
