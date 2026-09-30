"""Логика подземелий: спавн врагов, завершение."""
import json

from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import DUNGEONS
from services.combat_service import send_combat_state


async def spawn_dungeon_enemy(chat_id, uid, dungeon_id, room):
    """Создать врага в комнате подземелья."""
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


async def dungeon_finish(chat_id, uid, msg):
    """Завершить подземелье, выдать добычу."""
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
