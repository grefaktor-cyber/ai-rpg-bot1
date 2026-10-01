"""PvP: дуэли с очередью 4 действия."""
import json
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core import globals as g
from core.formulas import (
    effective_stats, faction_mult, calc_max_hp, hp_bar,
    calc_damage, calc_p_def, calc_m_def, apply_defense, get_dmg_type,
    racial_crit_bonus, get_crit_bonus, racial_heal_mult,
)
from core.keyboards import main_kb, combat_kb, combat_pending_text
from core.skills import get_skill, skill_multiplier
from core.game_data import POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE


router = Router()

MAX_ACTIONS = 4


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

    from core.keyboards import duel_offer_kb
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
    a = await g.db.get_user(a["user_id"])
    b = await g.db.get_user(b["user_id"])
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
    await c.answer()


# ================= СОСТОЯНИЕ =================
async def send_pvp_state(uid, user, combat, edit_message=None):
    if not combat:
        return
    user = await g.db.get_user(uid)
    combat = await g.db.get_combat(uid)
    if not combat:
        return

    enemy_bar = hp_bar(combat["enemy_hp"], combat["enemy_max_hp"])
    player_bar = hp_bar(user["hp"], user["max_hp"])
    turn_text = "🎯 <b>Твой ход!</b>" if combat["my_turn"] else "⏳ Ждём хода противника..."

    header = f"⚔️ <b>ДУЭЛЬ · РАУНД {combat['round_num']}</b>"
    mp = user.get("mp", 0)
    max_mp = user.get("max_mp", 0)
    mp_line = f" · 💧 MP: {mp}/{max_mp}" if max_mp else ""

    enemy_block = (f"🛡 <b>{combat['enemy_name']}</b> (Ур. {combat['enemy_level']})\n"
                   f"{enemy_bar} {combat['enemy_hp']}/{combat['enemy_max_hp']}")
    player_block = (f"❤️ <b>{user['char_name']}</b> (Ур. {user['level']})\n"
                    f"{player_bar} {user['hp']}/{user['max_hp']}{mp_line}\n"
                    f"💰 Ставка: {combat['stake']}")

    text = f"{header}\n\n{enemy_block}\n\n{player_block}\n\n{turn_text}"

    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if combat["my_turn"]:
        text += f"\n\n{combat_pending_text(pending, MAX_ACTIONS)}"

    try:
        active = json.loads(user.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    kb = combat_kb(active, mp, pending, prefix="pvp",
                   max_actions=MAX_ACTIONS, is_pvp=True)

    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            return
        except Exception:
            pass
    try:
        await g.bot.send_message(uid, text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================= ДЕЙСТВИЯ ИГРОКА =================
async def _get_pvp_combat(uid):
    combat = await g.db.get_combat(uid)
    if not combat or not combat.get("is_pvp"):
        return None
    return combat


async def _queue_pvp_action(uid, action_code):
    combat = await _get_pvp_combat(uid)
    if not combat:
        return False, "no_combat"
    if not combat["my_turn"]:
        return False, "not_my_turn"
    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if len(pending) >= MAX_ACTIONS:
        return False, "full"
    pending.append(action_code)
    await g.db.set_pending_actions(uid, json.dumps(pending))
    return True, "ok"


async def _undo_pvp_action(uid):
    combat = await _get_pvp_combat(uid)
    if not combat or not combat["my_turn"]:
        return False
    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if pending:
        pending.pop()
        await g.db.set_pending_actions(uid, json.dumps(pending))
        return True
    return False


@router.callback_query(F.data == "pvp_add_attack")
async def pvp_add_attack(c: CallbackQuery):
    ok, reason = await _queue_pvp_action(c.from_user.id, "attack")
    if not ok:
        msg = {"not_my_turn": "Не твой ход", "full": "Очередь полна"}.get(reason, "Ошибка")
        await c.answer(msg, show_alert=True); return
    await c.answer("⚔️ +Атака")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id))


@router.callback_query(F.data == "pvp_add_defend")
async def pvp_add_defend(c: CallbackQuery):
    ok, reason = await _queue_pvp_action(c.from_user.id, "defend")
    if not ok:
        msg = {"not_my_turn": "Не твой ход", "full": "Очередь полна"}.get(reason, "Ошибка")
        await c.answer(msg, show_alert=True); return
    await c.answer("🛡 +Защита")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id))


@router.callback_query(F.data.startswith("pvp_add_skill_"))
async def pvp_add_skill(c: CallbackQuery):
    skill_code = c.data.replace("pvp_add_skill_", "")
    s = get_skill(skill_code)
    if not s:
        await c.answer("Не найден"); return
    user = await g.db.get_user(c.from_user.id)
    if user["mp"] < s["mp_cost"]:
        await c.answer(f"❌ Нужно {s['mp_cost']} MP", show_alert=True); return
    ok, reason = await _queue_pvp_action(c.from_user.id, f"skill_{skill_code}")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer(f"✨ +{s['name']}")
await send_pvp_state(c.from_user.id, user,
                     await g.db.get_combat(c.from_user.id),
                     edit_message=c.message)


@router.callback_query(F.data == "pvp_add_potion_hp")
async def pvp_add_potion_hp(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    if user["hp"] >= user["max_hp"]:
        await c.answer("❤️ HP полное", show_alert=True); return
    ok, reason = await _queue_pvp_action(c.from_user.id, "potion_hp")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer("💚 +Зелье HP")
await send_pvp_state(c.from_user.id, user,
                     await g.db.get_combat(c.from_user.id),
                     edit_message=c.message)


@router.callback_query(F.data == "pvp_add_potion_mp")
async def pvp_add_potion_mp(c: CallbackQuery):
    user = await g.db.get_user(c.from_user.id)
    if user["mp"] >= user["max_mp"]:
        await c.answer("💧 MP полное", show_alert=True); return
    ok, reason = await _queue_pvp_action(c.from_user.id, "potion_mp")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer("🔮 +Зелье MP")
await send_pvp_state(c.from_user.id, user,
                     await g.db.get_combat(c.from_user.id),
                     edit_message=c.message)


@router.callback_query(F.data == "pvp_undo")
async def pvp_undo(c: CallbackQuery):
    ok = await _undo_pvp_action(c.from_user.id)
    if not ok:
        await c.answer("Очередь пуста или не твой ход"); return
    await c.answer("↩️")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id))


# ================= ВЫПОЛНЕНИЕ ХОДА =================
@router.callback_query(F.data == "pvp_execute")
async def pvp_execute(c: CallbackQuery):
    uid = c.from_user.id
    combat = await _get_pvp_combat(uid)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    if not combat["my_turn"]:
        await c.answer("Не твой ход", show_alert=True); return

    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if not pending:
        await c.answer("Очередь пуста", show_alert=True); return

    user = await g.db.get_user(uid)
    opp_id = combat["opponent_id"]
    opp = await g.db.get_user(opp_id)

    log = []
    enemy_skip = False

    # Применяем каждое действие
    for action in pending:
        # Проверка: противник ещё жив?
        opp = await g.db.get_user(opp_id)
        if opp["hp"] <= 0:
            break

        if action == "attack":
            eff = effective_stats(user)
            t_pdef = calc_p_def(opp)
            t_mdef = calc_m_def(opp)
            dmg_type = get_dmg_type(user)
            base = calc_damage(user)
            if dmg_type == "magic":
                dmg = apply_defense(base, t_mdef)
            else:
                dmg = apply_defense(base, t_pdef)
            dmg = int(dmg * faction_mult(user, "dmg_mult"))

            crit_chance = eff["dex"] + racial_crit_bonus(user) + get_crit_bonus(user)
            if user.get("pet_type") == "owl":
                crit_chance += 15
            is_crit = random.randint(1, 100) <= crit_chance
            if is_crit:
                dmg = int(dmg * 2)

            new_hp = max(0, opp["hp"] - dmg)
            await g.db.update_hp(opp_id, new_hp)
            # Обновить enemy_hp в combat opponent
            async with g.db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
                    new_hp, uid
                )
            log.append(f"⚔️ {dmg} урона" + (" 💥 КРИТ!" if is_crit else ""))

        elif action == "defend":
            heal = int(user["max_hp"] * 0.05)
            new_hp = min(user["max_hp"], user["hp"] + heal)
            await g.db.update_hp(uid, new_hp)
            user["hp"] = new_hp
            log.append(f"🛡 Защита: +{heal} HP")

        elif action.startswith("skill_"):
            skill_code = action.replace("skill_", "")
            s = get_skill(skill_code)
            if not s:
                continue
            mp_cost = s["mp_cost"]
            if user["mp"] < mp_cost:
                log.append(f"❌ Не хватило MP для «{s['name']}»")
                continue
            await g.db.spend_mp(uid, mp_cost)
            user["mp"] -= mp_cost
            mult = skill_multiplier(user, skill_code)
            effect = s["effect"]

            if effect == "damage":
                t_pdef = calc_p_def(opp)
                t_mdef = calc_m_def(opp)
                dmg_type = get_dmg_type(user)
                base = calc_damage(user)
                if dmg_type == "magic":
                    dmg = apply_defense(base, t_mdef)
                else:
                    dmg = apply_defense(base, t_pdef)
                dmg = int(dmg * mult * faction_mult(user, "dmg_mult"))
                new_hp = max(0, opp["hp"] - dmg)
                await g.db.update_hp(opp_id, new_hp)
                async with g.db.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
                        new_hp, uid
                    )
                log.append(f"✨ {s['name']}: {dmg} урона")

            elif effect == "heal":
                heal = int(user["max_hp"] * mult * racial_heal_mult(user))
                new_hp = min(user["max_hp"], user["hp"] + heal)
                await g.db.update_hp(uid, new_hp)
                user["hp"] = new_hp
                log.append(f"✨ {s['name']}: +{heal} HP")

            elif effect == "buff_atk":
                # В PvP не работает долгосрочно, но дадим бонус к след. атаке
                log.append(f"✨ {s['name']}: бафф атаки")

            elif effect == "debuff":
                # Снимаем урон у противника на его след. ход — упрощённо
                log.append(f"✨ {s['name']}: дебафф")

            elif effect == "stun":
                enemy_skip = True
                log.append(f"✨ {s['name']}: враг оглушён!")

            elif effect == "buff_def":
                log.append(f"✨ {s['name']}: защита")

        elif action == "potion_hp":
            if user["hp"] >= user["max_hp"]:
                log.append("💚 HP полное, зелье не использовано")
                continue
            if user["gold"] < POTION_PRICE:
                log.append(f"❌ Нет {POTION_PRICE}💰 на зелье")
                continue
            await g.db.spend_gold(uid, POTION_PRICE)
            new_hp = min(user["max_hp"], user["hp"] + POTION_HEAL)
            await g.db.update_hp(uid, new_hp)
            user["hp"] = new_hp
            log.append(f"💚 Зелье HP: +{POTION_HEAL}")

        elif action == "potion_mp":
            if user["mp"] >= user["max_mp"]:
                log.append("🔮 MP полное, зелье не использовано")
                continue
            if user["gold"] < MP_POTION_PRICE:
                log.append(f"❌ Нет {MP_POTION_PRICE}💰 на зелье")
                continue
            await g.db.spend_gold(uid, MP_POTION_PRICE)
            new_mp = min(user["max_mp"], user["mp"] + MP_POTION_RESTORE)
            await g.db.update_mp(uid, new_mp)
            user["mp"] = new_mp
            log.append(f"🔮 Зелье MP: +{MP_POTION_RESTORE}")

    # Очистка очереди
    await g.db.clear_pending_actions(uid)

    # Проверить победу
    opp = await g.db.get_user(opp_id)
    summary = "<b>🗡 Твои действия:</b>\n" + "\n".join(log)

    if opp["hp"] <= 0:
        await c.answer("⚡ Выполнено!")
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await pvp_end(winner_id=uid, loser_id=opp_id, stake=combat["stake"])
        return

    # Уведомление оппоненту + переключение хода
    try:
        await g.bot.send_message(opp_id,
            f"⚔️ <b>Ход противника</b> ({user['char_name']})\n\n{summary}",
            parse_mode=ParseMode.HTML)
    except Exception:
        pass

    if enemy_skip:
        # Ход остаётся у игрока
        await g.db.set_pending_actions(uid, "[]")
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        user = await g.db.get_user(uid)
        await send_pvp_state(uid, user, await g.db.get_combat(uid))
        await c.answer("⚡ Враг оглушён! Ход остаётся у тебя")
        return

    await g.db.pvp_switch_turn(uid)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    user = await g.db.get_user(uid)
    opp = await g.db.get_user(opp_id)
    await send_pvp_state(uid, user, await g.db.get_combat(uid),
                         edit_message=c.message)
    await send_pvp_state(opp_id, opp, await g.db.get_combat(opp_id))
    await c.answer("⚡ Ход передан")


# ================= СДАТЬСЯ =================
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
