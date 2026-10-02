"""Логика мировых боссов: спавн, атака с P.Def/M.Def, награды.
Поддерживает рейд-боссов с требованием min_players."""
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


# ================= РЕЙД-БОССЫ (добавляются в WORLD_BOSSES) =================
RAID_BOSSES = {
    "abyss_lord": {
        "name": "👹 Повелитель Бездны",
        "level": 40,
        "hp": 100000,
        "attack_dmg": 350,
        "dmg_type": "magic",
        "locations": ["abyss", "cave", "mountains"],
        "desc": ("Требует МИНИМУМ 2 игрока в локации. "
                 "Восстанавливает 500 HP каждый ход."),
        "raid": True,
        "min_players": 2,
        "heal_per_turn": 500,
    },
    "world_devourer": {
        "name": "🐲 Пожиратель Миров",
        "level": 45,
        "hp": 150000,
        "attack_dmg": 420,
        "dmg_type": "phys",
        "locations": ["abyss", "mountains", "port"],
        "desc": ("Требует МИНИМУМ 3 игрока в локации. "
                 "Восстанавливает 800 HP каждый ход."),
        "raid": True,
        "min_players": 3,
        "heal_per_turn": 800,
    },
}

# Регистрируем в общий словарь
WORLD_BOSSES.update(RAID_BOSSES)


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
    """Приводит naive datetime из БД к aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def should_spawn_now():
    now_msk = _now_msk()
    return now_msk.hour in SPAWN_HOURS_MSK


def is_raid_boss(boss_code):
    """Проверка: рейд-босс ли это."""
    return boss_code in RAID_BOSSES


async def _count_players_in_location(loc_code, exclude_uid=0):
    """Сколько игроков с персонажем в локации."""
    async with g.db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM users "
            "WHERE location_code=$1 AND char_name!='' AND user_id!=$2",
            loc_code, exclude_uid
        )
    return (row["cnt"] if row else 0) + 1  # +1 = сам атакующий


# ================= СПАВН =================
async def try_spawn_boss():
    """Плановая проверка спавна (раз в 5 мин из _cleanup_loop)."""
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

    # Обычные боссы — из WORLD_BOSSES без рейд
    normal_codes = [c for c in WORLD_BOSSES if c not in RAID_BOSSES]
    if not normal_codes:
        return None
    boss_code = random.choice(normal_codes)
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


async def force_spawn_boss(boss_code=None, location_code=None, notify=False):
    """Форс-спавн ЛЮБОГО босса (включая рейд). Игнорирует расписание."""
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

    boss_id = await g.db.spawn_world_boss(
        boss_code, location_code, boss_data["hp"]
    )
    loc_name = W.get_location(location_code).get("name", "?")

    if notify:
        async with g.db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id FROM users WHERE char_name!=''"
            )
        is_raid = is_raid_boss(boss_code)
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
        "boss_id": boss_id,
        "boss_code": boss_code,
        "boss_name": boss_data["name"],
        "boss_level": boss_data["level"],
        "location_code": location_code,
        "location_name": loc_name,
        "hp": boss_data["hp"],
        "attack_dmg": boss_data["attack_dmg"],
        "dmg_type": boss_data["dmg_type"],
        "is_raid": is_raid_boss(boss_code),
        "min_players": boss_data.get("min_players", 1),
    }


# ================= АТАКА =================
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

    # ============ ПРОВЕРКА РЕЙД-БОССА: минимум игроков ============
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

    # ============ РЕГЕНЕРАЦИЯ РЕЙД-БОССА ============
    heal_amount = 0
    if is_raid and updated and updated["current_hp"] > 0:
        heal_amount = boss_data.get("heal_per_turn", 0)
        if heal_amount > 0:
            new_boss_hp = min(
                updated["max_hp"],
                updated["current_hp"] + heal_amount
            )
            async with g.db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE world_bosses SET current_hp=$1 WHERE id=$2",
                    new_boss_hp, updated["id"]
                )
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

        # Рейд-босс даёт больше наград
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

        # Рейд-босс: топ-3 получают доп. предмет
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
