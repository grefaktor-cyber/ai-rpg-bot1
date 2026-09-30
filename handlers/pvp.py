"""PvP: дуэли, бой, ставки."""
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import globals as g
from core.formulas import effective_stats, faction_mult, calc_max_hp, hp_bar
from core.keyboards import main_kb, pvp_kb, duel_offer_kb


router = Router()


class DuelStates(StatesGroup):
    waiting_counter_stake = State()


# ================= ВЫЗОВ =================
@router.message(Command("duel"))
async def duel_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты уже в бою!"); return
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("/duel Имя — ставка 10%\n/duel Имя 100 — своя"); return
    target = await g.db.get_user_by_char_name(parts[1])
    if not target:
        await m.answer(f"❌ «{parts[1]}» не найден."); return
    if target["user_id"] == u["user_id"]:
        await m.answer("❌ Нельзя себя."); return
    if target.get("location_code") != u.get("location_code"):
        await m.answer(f"❌ {target['char_name']} в другой локации."); return
    if await g.db.get_combat(target["user_id"]):
        await m.answer(f"❌ {target['char_name']} уже в бою."); return
    if len(parts) >= 3:
        try:
            stake = int(parts[2])
        except ValueError:
            await m.answer("Ставка числом."); return
        if stake < 10:
            await m.answer("Минимум 10💰"); return
    else:
        stake = max(10, int(u["gold"] * 0.10))
    if u["gold"] < stake:
        await m.answer(f"❌ У тебя нет {stake}💰"); return
    if target["gold"] < stake:
        await m.answer(f"❌ У {target['char_name']} нет {stake}💰"); return
    oid = await g.db.create_duel_offer(u["user_id"], u["char_name"],
                                       target["user_id"], target["char_name"], stake)
    try:
        await g.bot.send_message(target["user_id"],
            f"⚔️ <b>Тебя вызывает {u['char_name']}!</b>\n\nСтавка: <b>{stake}💰</b>",
            reply_markup=duel_offer_kb(oid, is_caller=False), parse_mode=ParseMode.HTML)
    except Exception:
        await m.answer("❌ Не удалось отправить вызов."); return
    await m.answer(f"⚔️ Вызов отправлен <b>{target['char_name']}</b>!",
                   reply_markup=duel_offer_kb(oid, is_caller=True),
                   parse_mode=ParseMode.HTML)


# ================= ПРИНЯТИЕ / ОТКАЗ / ОТМЕНА =================
@router.callback_query(F.data.startswith("duel_accept_"))
async def duel_accept(c: CallbackQuery):
    oid = int(c.data.replace("duel_accept_", ""))
    offer = await g.db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Уже неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой вызов"); return
    a = await g.db.get_user(offer["challenger_id"])
    b = await g.db.get_user(offer["opponent_id"])
    stake = offer["stake"]
    if a["gold"] < stake or b["gold"] < stake:
        await c.answer("Не хватает золота", show_alert=True)
        await g.db.set_duel_status(oid, "cancelled"); return
    await g.db.set_duel_status(oid, "accepted")
    for p in (a, b):
        nm = calc_max_hp(p)
        await g.db.update_hp_max(p["user_id"], nm, nm)
        p["hp"] = nm; p["max_hp"] = nm
    await g.db.start_pvp_combat(a, b, stake)
    try:
        await c.message.edit_text("✅ Дуэль началась!")
    except Exception:
        pass
    await send_pvp_state(a["user_id"], a, await g.db.get_combat(a["user_id"]))
    await send_pvp_state(b["user_id"], b, await g.db.get_combat(b["user_id"]))
    await c.answer("Начали!")


@router.callback_query(F.data.startswith("duel_decline_"))
async def duel_decline(c: CallbackQuery):
    oid = int(c.data.replace("duel_decline_", ""))
    offer = await g.db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Уже неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой"); return
    await g.db.set_duel_status(oid, "declined")
    await g.db.add_reputation(c.from_user.id, -1)
    try:
        await c.message.edit_text("🏳️ Отказ. Репутация: −1")
    except Exception:
        pass
    try:
        await g.bot.send_message(offer["challenger_id"],
                                 f"🏳️ {offer['opponent_name']} отказался.")
    except Exception:
        pass
    if await g.db.add_achievement(c.from_user.id, "coward"):
        await c.message.answer("🏆 Достижение: 🏳️ Трус")
    await c.answer()


@router.callback_query(F.data.startswith("duel_cancel_"))
async def duel_cancel(c: CallbackQuery):
    oid = int(c.data.replace("duel_cancel_", ""))
    offer = await g.db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Неактивно"); return
    if c.from_user.id != offer["challenger_id"]:
        await c.answer("Не твой"); return
    await g.db.set_duel_status(oid, "cancelled")
    try:
        await c.message.edit_text("❌ Отменено.")
    except Exception:
        pass
    try:
        await g.bot.send_message(offer["opponent_id"], "❌ Вызов отменён.")
    except Exception:
        pass
    await c.answer()


# ================= СВОЯ СТАВКА (FSM) =================
@router.callback_query(F.data.startswith("duel_counter_"))
async def duel_counter(c: CallbackQuery, state: FSMContext):
    oid = int(c.data.replace("duel_counter_", ""))
    offer = await g.db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await c.answer("Неактивно"); return
    if c.from_user.id != offer["opponent_id"]:
        await c.answer("Не твой"); return
    await state.set_state(DuelStates.waiting_counter_stake)
    await state.update_data(duel_oid=oid)
    await c.answer()
    await c.message.answer("💰 Введи свою ставку числом.")


@router.message(DuelStates.waiting_counter_stake)
async def counter_stake_handler(m: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("duel_oid")
    try:
        new_stake = int(m.text.strip())
    except ValueError:
        await m.answer("Число нужно."); return
    if new_stake < 10:
        await m.answer("Минимум 10💰"); return
    offer = await g.db.get_duel_offer(oid)
    if not offer or offer["status"] != "pending":
        await m.answer("Неактивно.")
        await state.clear()
        return
    ch = await g.db.get_user(offer["challenger_id"])
    me = await g.db.get_user(offer["opponent_id"])
    if ch["gold"] < new_stake or me["gold"] < new_stake:
        await m.answer("У кого-то не хватает золота"); return
    await g.db.set_duel_status(oid, "cancelled")
    new_oid = await g.db.create_duel_offer(offer["opponent_id"], offer["opponent_name"],
                                           offer["challenger_id"], offer["challenger_name"],
                                           new_stake)
    await state.clear()
    await m.answer(f"💰 Встречная ставка: {new_stake}💰")
    try:
        await g.bot.send_message(offer["challenger_id"],
            f"💰 <b>{offer['opponent_name']}</b> предлагает {new_stake}💰",
            reply_markup=duel_offer_kb(new_oid, is_caller=False), parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= СОСТОЯНИЕ =================
async def send_pvp_state(uid, user, combat):
    if not combat:
        return
    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    header = f"⚔️ <b>ДУЭЛЬ · РАУНД {combat['round_num']}</b>"
    turn_text = "🎯 <b>Твой ход!</b>" if combat["my_turn"] else "⏳ Ждём хода противника..."
    enemy_block = (f"🛡 <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']})\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']})\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}\n"
                    f"💰 Ставка: {combat['stake']}")
    text = f"{header}\n\n{enemy_block}\n\n{player_block}\n\n{turn_text}"
    try:
        await g.bot.send_message(uid, text, reply_markup=pvp_kb(combat["my_turn"]),
                                 parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= БОЙ =================
@router.callback_query(F.data == "pvp_attack")
async def pvp_attack_cb(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or not combat.get("is_pvp"):
        await c.answer("Неактивно"); return
    if not combat["my_turn"]:
        await c.answer("Не твой ход!", show_alert=True); return
    from core.formulas import (
        calc_damage, calc_p_def, calc_m_def, apply_defense, get_dmg_type,
    )
    eff = effective_stats(user)
    # Защита противника — реальные P.Def/M.Def
    opponent = await g.db.get_user(combat["opponent_id"])
    t_pdef = calc_p_def(opponent)
    t_mdef = calc_m_def(opponent)
    dmg_type = get_dmg_type(user)
    base = calc_damage(user)
    if dmg_type == "magic":
        dmg = apply_defense(base, t_mdef)
    else:
        dmg = apply_defense(base, t_pdef)
    dmg = int(dmg * faction_mult(user, "dmg_mult"))
    is_crit = random.randint(1, 100) <= eff["dex"]
    if is_crit:
        dmg = int(dmg * 2)
    res = await g.db.pvp_damage(c.from_user.id, dmg)
    if not res:
        await c.answer("Ошибка"); return
    opp_hp, opp_id = res
    await c.answer(f"Нанесено {dmg}{' КРИТ' if is_crit else ''}")
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if opp_hp <= 0:
        await pvp_end(winner_id=c.from_user.id, loser_id=opp_id, stake=combat["stake"])
        return
    await g.db.pvp_switch_turn(c.from_user.id)
    try:
        opp_user = await g.db.get_user(opp_id)
        opp_combat = await g.db.get_combat(opp_id)
        await g.bot.send_message(opp_id,
            f"💔 <b>{user['char_name']}</b> бьёт на {dmg}!" + (" 💥 КРИТ" if is_crit else ""),
            parse_mode=ParseMode.HTML)
        await send_pvp_state(opp_id, opp_user, opp_combat)
    except Exception:
        pass
    new_combat = await g.db.get_combat(c.from_user.id)
    await send_pvp_state(c.from_user.id, await g.db.get_user(c.from_user.id), new_combat)


@router.callback_query(F.data == "pvp_surrender")
async def pvp_surrender_cb(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    combat = await g.db.get_combat(c.from_user.id)
    if not combat or not combat.get("is_pvp"):
        await c.answer("Неактивно"); return
    opp_id = combat["opponent_id"]
    stake = combat["stake"]
    await g.db.end_combat(c.from_user.id)
    await g.db.end_combat(opp_id)
    await g.db.spend_gold(c.from_user.id, min(stake, user["gold"]))
    await g.db.add_gold(opp_id, stake)
    await g.db.add_reputation(c.from_user.id, -1)
    await g.db.incr_pvp_losses(c.from_user.id)
    await g.db.incr_pvp_wins(opp_id)
    await g.db.add_reputation(opp_id, 1)
    ou = await g.db.get_user(opp_id)
    nm = calc_max_hp(ou)
    await g.db.update_hp_max(opp_id, nm, nm)
    try:
        await c.message.edit_text(f"🏳️ Сдался. {stake}💰 ушло {combat['enemy_name']}.")
    except Exception:
        pass
    try:
        await g.bot.send_message(opp_id,
            f"🏆 Победа! {user['char_name']} сдался. +{stake}💰",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer()


async def pvp_end(winner_id, loser_id, stake):
    await g.db.end_combat(winner_id)
    await g.db.end_combat(loser_id)
    w = await g.db.get_user(winner_id)
    l = await g.db.get_user(loser_id)
    real = min(stake, l["gold"])
    await g.db.spend_gold(loser_id, real)
    await g.db.add_gold(winner_id, real)
    await g.db.incr_pvp_wins(winner_id)
    await g.db.incr_pvp_losses(loser_id)
    await g.db.add_reputation(winner_id, 1)
    await g.db.add_reputation(loser_id, -1)
    for p in (w, l):
        nm = calc_max_hp(p)
        await g.db.update_hp_max(p["user_id"], nm, nm)
    await g.db.add_world_event(winner_id, w["username"],
                               f"победил {l['char_name']} в дуэли ({real}💰)")
    await g.db.add_achievement(winner_id, "duelist")
    wu = await g.db.get_user(winner_id)
    if wu["pvp_wins"] >= 5:
        if await g.db.add_achievement(winner_id, "arena_king"):
            try:
                await g.bot.send_message(winner_id, "🏆 ⚜️ Гроза арены",
                                         parse_mode=ParseMode.HTML)
            except Exception:
                pass
    await g.db.progress_quest(winner_id, "win_duels", 1)
    try:
        await g.bot.send_message(winner_id,
            f"🏆 <b>ПОБЕДА!</b> над {l['char_name']}\n+{real}💰 · Репутация +1",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        await g.bot.send_message(loser_id,
            f"💀 <b>Поражение</b> от {w['char_name']}\n−{real}💰 · Репутация −1",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        pass
