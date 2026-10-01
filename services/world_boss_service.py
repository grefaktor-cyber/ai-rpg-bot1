"""Логика мировых боссов: спавн, атака, награды."""
import random
from datetime import datetime

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import DROP_TABLE
from core.world_bosses import (
    WORLD_BOSSES, GOLD_PER_1K_DAMAGE, XP_PER_1K_DAMAGE,
    TOP1_BONUS_ITEM_CHANCE, KILLER_BONUS_MULT,
)
from core.formulas import effective_stats, calc_damage, get_dmg_type
import world as W


async def try_spawn_boss():
    """Попробовать создать нового босса (вызывается из cron)."""
    active = await g.db.get_all_active_world_bosses()
    if active:
        return None

    boss_code = random.choice(list(WORLD_BOSSES.keys()))
    boss_data = WORLD_BOSSES[boss_code]
    loc_code = random.choice(boss_data["locations"])

    # Масштабируем HP от среднего уровня активных игроков
    # Берём базовый HP
    hp = boss_data["hp"]

    boss_id = await g.db.spawn_world_boss(boss_code, loc_code, hp)

    # Broadcast всем игрокам
    loc_name = W.get_location(loc_code).get("name", "?")
    players = await g.db.get_players_at_location(loc_code, 0)
    try:
        # Оповещаем всех игроков через get_all_users (если нет, шлём только в чат)
        from db import DATABASE_URL  # noqa
    except Exception:
        pass

    return {"boss_id": boss_id, "boss_code": boss_code,
            "location_code": loc_code, "location_name": loc_name,
            "boss_name": boss_data["name"]}


async def attack_boss(uid, damage):
    """Игрок атакует босса. Возвращает (ok, info)."""
    u = await g.db.get_user(uid)
    if not u["char_name"]:
        return False, {"error": "no_char"}

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        return False, {"error": "no_boss"}

    await g.db.add_boss_damage(boss["id"], uid, u["char_name"], damage)
    updated = await g.db.get_active_world_boss(loc_code)

    if updated["current_hp"] <= 0:
        # Босс убит — обрабатываем награды
        await _handle_boss_kill(updated, uid)
        return True, {"killed": True, "boss": updated}

    return True, {"killed": False, "boss": updated}


async def _handle_boss_kill(boss, killer_id):
    """Босс убит — выдаём награды всем участникам."""
    await g.db.kill_world_boss(boss["id"], killer_id)
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=50)
    if not damage_list:
        return

    boss_code = boss.get("boss_code", "")
    boss_data = WORLD_BOSSES.get(boss_code, {})
    boss_name = boss_data.get("name", "Босс")
    loc_name = W.get_location(boss["location_code"]).get("name", "?")
    total_dmg = boss.get("total_damage", 1) or 1

    # Награды
    for entry in damage_list:
        uid = entry["user_id"]
        damage = entry["damage"]
        # Золото и XP пропорционально урону
        gold = int((damage / 1000) * GOLD_PER_1K_DAMAGE)
        xp = int((damage / 1000) * XP_PER_1K_DAMAGE)
        gold = max(gold, 50)
        xp = max(xp, 100)

        # Убийца — бонус
        is_killer = (uid == killer_id)
        if is_killer:
            gold = int(gold * KILLER_BONUS_MULT)

        # Топ-1 — шанс на предмет
        is_top1 = (entry == damage_list[0])
        bonus_item = None
        if is_top1 and random.random() < TOP1_BONUS_ITEM_CHANCE:
            bonus_item = random.choice(DROP_TABLE)
            await g.db.add_item(uid, bonus_item)

        await g.db.add_gold(uid, gold)
        await g.db.add_xp(uid, xp)
        await g.db.add_journal_entry(
            uid,
            f"Победил мирового босса «{boss_name}» (урон: {damage})",
            "boss"
        )

        # Уведомление
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
