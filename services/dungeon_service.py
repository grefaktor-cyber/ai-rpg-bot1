"""Логика подземелий: спавн врагов, регенерация, завершение."""
import json
import logging

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import DUNGEONS
from core.formulas import calc_enemy_hp, regen_between_rooms
from services.combat_service import send_combat_state

log = logging.getLogger(__name__)


async def spawn_dungeon_enemy(chat_id, uid, dungeon_id, room):
    d = DUNGEONS[dungeon_id]
    enemy_name = d["enemies"][min(room - 1, len(d["enemies"]) - 1)]
    is_boss = 1 if room == d["rooms"] else 0
    base_level = d["level_req"] + room - 1
    enemy_level = base_level + (2 if is_boss else 0)

    u = await g.db.get_user(uid)
    # Новые формулы HP
    enemy_hp = calc_enemy_hp(enemy_level, u["level"], is_boss=bool(is_boss))

    # Регенерация перед боем (кроме первой комнаты)
    if room > 1:
        new_hp, new_mp = regen_between_rooms(u, hp_pct=0.20, mp_pct=0.30)
        await g.db.update_hp(uid, new_hp)
        await g.db.update_mp(uid, new_mp)
        u = await g.db.get_user(uid)

    log.info(f"[DUNGEON] spawn uid={uid} room={room} enemy={enemy_name} "
             f"lvl={enemy_level} hp={enemy_hp} boss={is_boss}")

    await g.db.start_combat(uid, enemy_name, enemy_level, enemy_hp,
                            boss=is_boss, dungeon=1)
    # ⚠️ Явный сброс очереди — на случай если start_combat не сбросил
    try:
        await g.db.clear_pending_actions(uid)
    except Exception as e:
        log.warning(f"[DUNGEON] clear_pending_actions failed: {e}")

    u = await g.db.get_user(uid)
    combat = await g.db.get_combat(uid)
    label = "🐉 БОСС" if is_boss else f"Комната {room}/{d['rooms']}"
    regen_note = ""
    if room > 1:
        regen_note = "\n💚 <i>+20% HP · +30% MP между комнатами</i>"
    await send_combat_state(chat_id, u, combat,
                            f"🏰 <b>{label}</b>{regen_note}")


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
