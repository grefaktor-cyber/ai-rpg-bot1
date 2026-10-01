"""Хендлеры боя: очередь + спойл + подземелья."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import DUNGEONS
from core.keyboards import dungeons_kb
from core.skills import get_skill
from core.materials import SPOIL_CLASSES
from services.combat_service import (
    execute_queued_round, queue_action, undo_action,
    send_combat_state, handle_death,
)
from services.dungeon_service import spawn_dungeon_enemy, dungeon_finish

router = Router()


async def _get_active_combat(uid):
    combat = await g.db.get_combat(uid)
    if not combat or combat.get("is_pvp"):
        return None
    return combat


# ================= ДОБАВЛЕНИЕ =================
@router.callback_query(F.data == "combat_add_attack")
async def add_attack(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, "attack")
    if not ok:
        await c.answer("Очередь полна (4 действия)", show_alert=True); return
    await c.answer("⚔️ +Атака")
    user = await g.db.get_user(c.from_user.id)
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_add_defend")
async def add_defend(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, "defend")
    if not ok:
        await c.answer("Очередь полна", show_alert=True); return
    await c.answer("🛡 +Защита")
    user = await g.db.get_user(c.from_user.id)
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data.startswith("combat_add_skill_"))
async def add_skill(c: CallbackQuery):
    skill_code = c.data.replace("combat_add_skill_", "")
    s = get_skill(skill_code)
    if not s:
        await c.answer("Скил не найден"); return
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    user = await g.db.get_user(c.from_user.id)
    if user["mp"] < s["mp_cost"]:
        await c.answer(f"❌ Нужно {s['mp_cost']} MP", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, f"skill_{skill_code}")
    if not ok:
        await c.answer("Очередь полна", show_alert=True); return
    await c.answer(f"✨ +{s['name']}")
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_add_potion_hp")
async def add_potion_hp(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    user = await g.db.get_user(c.from_user.id)
    if user["hp"] >= user["max_hp"]:
        await c.answer("❤️ HP полное", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, "potion_hp")
    if not ok:
        await c.answer("Очередь полна", show_alert=True); return
    await c.answer("💚 +Зелье HP")
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_add_potion_mp")
async def add_potion_mp(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    user = await g.db.get_user(c.from_user.id)
    if user["mp"] >= user["max_mp"]:
        await c.answer("💧 MP полное", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, "potion_mp")
    if not ok:
        await c.answer("Очередь полна", show_alert=True); return
    await c.answer("🔮 +Зелье MP")
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_add_spoil")
async def add_spoil(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    if user.get("class") not in SPOIL_CLASSES:
        await c.answer("Твой класс не умеет спойлить", show_alert=True); return
    if combat.get("spoil_used"):
        await c.answer("Спойл уже использован в этом бою", show_alert=True); return
    ok, reason = await queue_action(c.from_user.id, "spoil")
    if not ok:
        await c.answer("Очередь полна", show_alert=True); return
    await c.answer("🌿 +Спойл")
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_spoil_noop")
async def spoil_noop(c: CallbackQuery):
    await c.answer("Спойл уже использован в этом бою", show_alert=True)


@router.callback_query(F.data == "combat_undo")
async def undo(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    ok = await undo_action(c.from_user.id)
    if not ok:
        await c.answer("Очередь пуста"); return
    await c.answer("↩️ Убрано")
    user = await g.db.get_user(c.from_user.id)
    await send_combat_state(c.message.chat.id, user,
                            await g.db.get_combat(c.from_user.id),
                            edit_message=c.message)


@router.callback_query(F.data == "combat_execute")
async def execute(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    user = await g.db.get_user(c.from_user.id)
    await c.answer("⚡ Выполняю...")
    await execute_queued_round(c.message.chat.id, user, combat,
                                edit_message=c.message)


# ================= ПОБЕГ =================
@router.callback_query(F.data == "combat_flee")
async def flee(c: CallbackQuery):
    combat = await _get_active_combat(c.from_user.id)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    if combat["is_boss"]:
        await c.answer("🐉 От босса не убежать!", show_alert=True); return
    if combat.get("is_dungeon"):
        await c.answer("🏰 Из подземелья не сбежать!", show_alert=True); return
    if random.randint(1, 100) <= 50:
        await g.db.end_combat(c.from_user.id)
        await c.answer("🏃 Побег!")
        try:
            await c.message.edit_text("🏃 Ты сбежал.", reply_markup=None)
        except Exception:
            await c.message.answer("🏃 Ты сбежал.")
    else:
        await c.answer("❌ Не удалось!")
        user = await g.db.get_user(c.from_user.id)
        event = await g.db.get_active_event(user.get("location_code", "village"))
        enemy_dmg_mult = event.get("enemy_dmg_mult", 1.0) if event else 1.0
        enemy_dmg = int((combat["enemy_level"] * 5 + random.randint(0, 5)) // 2 * enemy_dmg_mult)
        new_hp = max(0, user["hp"] - enemy_dmg)
        await g.db.update_hp(c.from_user.id, new_hp)
        user["hp"] = new_hp
        if user["hp"] <= 0:
            await handle_death(c.message.chat.id, user, combat); return
        await g.db.incr_combat_round(c.from_user.id)
        await send_combat_state(c.message.chat.id, user,
                                await g.db.get_combat(c.from_user.id),
                                f"❌ Побег не удался! -{enemy_dmg}.", event,
                                edit_message=c.message)


# ================= ПОДЗЕМЕЛЬЯ =================
@router.message(Command("dungeon"))
@router.message(F.text == "🏰 Подземелья")
async def dungeon_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты в бою!"); return
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
        await c.answer("Нет"); return
    d = DUNGEONS[code]
    u = await g.db.get_user(c.from_user.id)
    if u["level"] < d["level_req"]:
        await c.answer(f"Нужен {d['level_req']} уровень", show_alert=True); return
    if not await g.db.spend_gold(c.from_user.id, d["entry"]):
        await c.answer(f"Нужно {d['entry']}💰", show_alert=True); return
    await g.db.start_dungeon(c.from_user.id, code)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer("Вход!")
    await c.message.answer(f"🏰 Входишь в <b>{d['name']}</b>...",
                            parse_mode=ParseMode.HTML)
    await spawn_dungeon_enemy(c.message.chat.id, c.from_user.id, code, 1)


@router.message(Command("dungeon_continue"))
async def dungeon_continue_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u.get("dungeon_id"):
        await m.answer("Ты не в подземелье."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return
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
        await m.answer("Ты не в подземелье."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return
    await dungeon_finish(m.chat.id, m.from_user.id, "Ты покидаешь подземелье с добычей.")


@router.callback_query(F.data == "dungeon_next")
async def dungeon_next_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    if not u.get("dungeon_id"):
        await c.answer("Не в подземелье"); return
    if await g.db.get_combat(c.from_user.id):
        await c.answer("Бой!"); return
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
