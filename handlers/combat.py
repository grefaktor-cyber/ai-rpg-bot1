"""Хендлеры боя: кнопки, команды подземелий."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import POTION_PRICE, POTION_HEAL
from core.keyboards import dungeons_kb
from services.combat_service import (
    process_combat_round, handle_death, send_combat_state,
)
from services.dungeon_service import spawn_dungeon_enemy, dungeon_finish
from core.game_data import DUNGEONS
from config import ADMIN_IDS

router = Router()


# ================= КНОПКИ БОЯ =================
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
    is_admin = c.from_user.id in ADMIN_IDS
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
    for code, d in DUNGEONS.items():
        can = u["level"] >= d["level_req"] and u["gold"] >= d["entry"]
        mark = "✅" if can else "🔒"
        text += (f"{mark} <b>{d['name']}</b>\n"
                 f"  Ур.{d['level_req']}+ · вход {d['entry']}💰 · комнат {d['rooms']}\n")
    text += "\n<i>Цепочка боёв, в конце босс. Смерть = потеря добычи.</i>"
    await m.answer(text, reply_markup=dungeons_kb(DUNGEONS, u["level"], u["gold"]),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("dungeon_enter_"))
async def dungeon_enter(c: CallbackQuery):
    code = c.data.replace("dungeon_enter_", "")
    if code not in DUNGEONS:
        await c.answer("Нет")
        return
    d = DUNGEONS[code]
    u = await g.db.get_user(c.from_user.id)
    is_admin = c.from_user.id in ADMIN_IDS
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
    await spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, code, 1)


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
    await spawn_dungeon_enemy(m.chat.id, m.from_user.id, u["dungeon_id"], next_room)


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
    await spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, u["dungeon_id"], next_room)


@router.callback_query(F.data == "dungeon_leave")
async def dungeon_leave_cb(c: CallbackQuery):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await dungeon_finish(c.message.chat.id, c.from_user.id, "Ты выходишь с добычей.")
