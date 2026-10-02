"""PvP: одновременные раунды с очередью действий + расовые бонусы."""
import json
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from core import globals as g
from core.formulas import (
    effective_stats, faction_mult, calc_max_hp, hp_bar,
    calc_damage, calc_p_def, calc_m_def, apply_defense, get_dmg_type,
    racial_crit_bonus, get_crit_bonus, racial_heal_mult,
    racial_magic_mult, racial_low_hp_mult,
)
from core.keyboards import main_kb, combat_kb, combat_pending_text
from core.skills import get_skill, skill_multiplier
from core.game_data import (
    POTION_PRICE, POTION_HEAL, MP_POTION_PRICE, MP_POTION_RESTORE,
    RANGE_CLASSES, get_racial_combat_bonus,
)


router = Router()

MAX_ACTIONS = 4

DEFEND_MULT_BY_COUNT = {
    0: 1.00,
    1: 0.70,
    2: 0.50,
    3: 0.35,
    4: 0.20,
}


def _is_range_round_1(user, combat):
    """Range-класс бьёт дальше в 1-м раунде."""
    return (combat.get("round_num", 1) == 1
            and user.get("class") in RANGE_CLASSES)


def _rage_mult(user):
    """Множитель ярости (демон): чем ниже HP, тем выше урон."""
    rage_max = get_racial_combat_bonus(user, "rage_max", 0.0)
    if rage_max <= 1.0:
        return 1.0
    hp_pct = user["hp"] / max(1, user["max_hp"])
    return 1.0 + (1.0 - hp_pct) * (rage_max - 1.0)


# ================= ВЫЗОВ =================
@router.message(Command("duel"))
async def duel_cmd(m: Message, state: FSMContext = None):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Ты уже в бою!"); return
    parts = (m.text or "").split()
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

    my_ready = bool(combat.get("my_ready", 0))
    if my_ready:
        turn_text = "⏳ <b>Ждём соперника...</b>"
    else:
        turn_text = "🎯 <b>Выбери действия и жми Готов</b>"

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
    if not my_ready:
        text += f"\n\n{combat_pending_text(pending, MAX_ACTIONS)}"

    try:
        active = json.loads(user.get("active_skills") or "[]")
    except Exception:
        active = []
    active = [x for x in active if x][:3]

    if my_ready:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="pvp_surrender")],
        ])
    else:
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


# ================= ДЕЙСТВИЯ =================
async def _get_pvp_combat(uid):
    combat = await g.db.get_combat(uid)
    if not combat or not combat.get("is_pvp"):
        return None
    return combat


async def _queue_pvp_action(uid, action_code):
    combat = await _get_pvp_combat(uid)
    if not combat:
        return False, "no_combat"
    if combat.get("my_ready"):
        return False, "already_ready"
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
    if not combat or combat.get("my_ready"):
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
        await c.answer("Нельзя добавить" if reason != "full" else "Очередь полна",
                       show_alert=True); return
    await c.answer("⚔️ +Атака")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


@router.callback_query(F.data == "pvp_add_defend")
async def pvp_add_defend(c: CallbackQuery):
    ok, reason = await _queue_pvp_action(c.from_user.id, "defend")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer("🛡 +Защита")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


@router.callback_query(F.data.startswith("pvp_add_skill_"))
async def pvp_add_skill(c: CallbackQuery):
    skill_code = c.data.replace("pvp_add_skill_", "")
    s = get_skill(skill_code)
    if not s:
        await c.answer("Не найден"); return
    ok, reason = await _queue_pvp_action(c.from_user.id, f"skill_{skill_code}")
    if not ok:
        await c.answer("Очередь полна" if reason == "full" else "Нельзя добавить",
                       show_alert=True); return
    await c.answer(f"✨ +{s['name']} ({s['mp_cost']} MP)")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


@router.callback_query(F.data == "pvp_add_potion_hp")
async def pvp_add_potion_hp(c: CallbackQuery):
    ok, reason = await _queue_pvp_action(c.from_user.id, "potion_hp")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer(f"💚 +Зелье HP ({POTION_PRICE}💰)")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


@router.callback_query(F.data == "pvp_add_potion_mp")
async def pvp_add_potion_mp(c: CallbackQuery):
    ok, reason = await _queue_pvp_action(c.from_user.id, "potion_mp")
    if not ok:
        await c.answer("Ошибка", show_alert=True); return
    await c.answer(f"🔮 +Зелье MP ({MP_POTION_PRICE}💰)")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


@router.callback_query(F.data == "pvp_undo")
async def pvp_undo(c: CallbackQuery):
    ok = await _undo_pvp_action(c.from_user.id)
    if not ok:
        await c.answer("Очередь пуста или уже готов"); return
    await c.answer("↩️")
    await send_pvp_state(c.from_user.id,
                          await g.db.get_user(c.from_user.id),
                          await g.db.get_combat(c.from_user.id),
                          edit_message=c.message)


# ================= РАЗРЕШЕНИЕ РАУНДА =================
@router.callback_query(F.data == "pvp_execute")
async def pvp_execute(c: CallbackQuery):
    uid = c.from_user.id
    combat = await _get_pvp_combat(uid)
    if not combat:
        await c.answer("Бой завершён", show_alert=True); return
    if combat.get("my_ready"):
        await c.answer("Ты уже готов", show_alert=True); return

    try:
        pending = json.loads(combat.get("pending_actions") or "[]")
    except Exception:
        pending = []
    if not pending:
        await c.answer("Добавь хотя бы 1 действие", show_alert=True); return

    await g.db.set_my_ready(uid, 1)

    opp_id = combat["opponent_id"]
    opp_combat = await g.db.get_opponent_combat(opp_id)

    if not opp_combat or not opp_combat.get("my_ready"):
        try:
            await c.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(
                    text="⏳ Ждём соперника...", callback_data="pvp_noop")]]))
        except Exception:
            pass
        await c.answer("⏳ Ждём соперника...")
        try:
            await g.bot.send_message(opp_id,
                f"⚔️ <b>Соперник готов!</b>\n\nТвой ход — выбери действия.",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return

    await c.answer("⚡ Разрешаем раунд...")
    await _resolve_pvp_round(uid, opp_id)


async def _resolve_pvp_round(uid_a, uid_b):
    combat_a = await g.db.get_combat(uid_a)
    combat_b = await g.db.get_combat(uid_b)
    if not combat_a or not combat_b:
        return

    user_a = await g.db.get_user(uid_a)
    user_b = await g.db.get_user(uid_b)

    try:
        actions_a = json.loads(combat_a.get("pending_actions") or "[]")
    except Exception:
        actions_a = []
    try:
        actions_b = json.loads(combat_b.get("pending_actions") or "[]")
    except Exception:
        actions_b = []

    log_a = []
    log_b = []

    defends_a = sum(1 for x in actions_a if x == "defend")
    defends_b = sum(1 for x in actions_b if x == "defend")
    def_mult_a = DEFEND_MULT_BY_COUNT.get(defends_a, 1.0)
    def_mult_b = DEFEND_MULT_BY_COUNT.get(defends_b, 1.0)

    # === РАСОВЫЕ БОНУСЫ ===
    a_dmg = get_racial_combat_bonus(user_a, "dmg_mult", 1.0)
    a_magic = get_racial_combat_bonus(user_a, "magic_mult", 1.0)
    a_crit = get_racial_combat_bonus(user_a, "crit_bonus", 0)
    a_lifesteal = get_racial_combat_bonus(user_a, "lifesteal", 0.0)
    a_dodge = get_racial_combat_bonus(user_a, "dodge", 0)
    a_rage = _rage_mult(user_a)
    a_range = 1.30 if _is_range_round_1(user_a, combat_a) else 1.0

    b_dmg = get_racial_combat_bonus(user_b, "dmg_mult", 1.0)
    b_magic = get_racial_combat_bonus(user_b, "magic_mult", 1.0)
    b_crit = get_racial_combat_bonus(user_b, "crit_bonus", 0)
    b_lifesteal = get_racial_combat_bonus(user_b, "lifesteal", 0.0)
    b_dodge = get_racial_combat_bonus(user_b, "dodge", 0)
    b_rage = _rage_mult(user_b)
    b_range = 1.30 if _is_range_round_1(user_b, combat_b) else 1.0

    new_hp_a = user_a["hp"]
    new_hp_b = user_b["hp"]
    new_mp_a = user_a.get("mp", 0)
    new_mp_b = user_b.get("mp", 0)
    gold_a = user_a["gold"]
    gold_b = user_b["gold"]
    max_hp_a = user_a["max_hp"]
    max_hp_b = user_b["max_hp"]
    max_mp_a = user_a.get("max_mp", 0)
    max_mp_b = user_b.get("max_mp", 0)

    dmg_a_to_b = 0
    dmg_b_to_a = 0

    # ============ ОЧЕРЕДЬ A (по порядку) ============
    for action in actions_a:
        if action == "attack":
            eff_a = effective_stats(user_a)
            t_pdef = calc_p_def(user_b)
            t_mdef = calc_m_def(user_b)
            dmg_type = get_dmg_type(user_a)
            base = calc_damage(user_a)
            dmg = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
            if dmg_type == "magic":
                dmg = int(dmg * racial_magic_mult(user_a) * a_magic)
            else:
                dmg = int(dmg * a_dmg)
            dmg = int(dmg * faction_mult(user_a, "dmg_mult"))
            dmg = int(dmg * racial_low_hp_mult(user_a) * a_rage * a_range)
            crit_chance = (eff_a["dex"] + racial_crit_bonus(user_a)
                           + get_crit_bonus(user_a) + a_crit)
            if user_a.get("pet_type") == "owl":
                crit_chance += 15
            is_crit = random.randint(1, 100) <= crit_chance
            if is_crit:
                dmg = int(dmg * 2)
            dmg = int(dmg * def_mult_b)
            dmg_a_to_b += dmg
            line = f"⚔️ Атака: {dmg} урона" + (" 💥 КРИТ!" if is_crit else "")
            if a_range > 1.0:
                line += " 🎯 <i>(дальний бой)</i>"
            if a_rage > 1.05:
                line += f" 😈 <i>(ярость ×{a_rage:.2f})</i>"
            log_a.append(line)
            if a_lifesteal > 0 and dmg > 0:
                heal = int(dmg * a_lifesteal)
                new_hp_a = min(max_hp_a, new_hp_a + heal)
                log_a.append(f"😈 Вампиризм: +{heal} HP")

        elif action == "defend":
            log_a.append("🛡 Защита")

        elif action == "potion_hp":
            if new_hp_a >= max_hp_a:
                log_a.append("💚 HP полное — зелье не использовано")
            elif gold_a < POTION_PRICE:
                log_a.append(f"❌ Нет {POTION_PRICE}💰 на зелье HP")
            else:
                gold_a -= POTION_PRICE
                before = new_hp_a
                new_hp_a = min(max_hp_a, new_hp_a + POTION_HEAL)
                log_a.append(f"💚 Зелье HP: {before} → {new_hp_a} (+{new_hp_a - before})")

        elif action == "potion_mp":
            if new_mp_a >= max_mp_a:
                log_a.append("🔮 MP полное — зелье не использовано")
            elif gold_a < MP_POTION_PRICE:
                log_a.append(f"❌ Нет {MP_POTION_PRICE}💰 на зелье MP")
            else:
                gold_a -= MP_POTION_PRICE
                before = new_mp_a
                new_mp_a = min(max_mp_a, new_mp_a + MP_POTION_RESTORE)
                log_a.append(f"🔮 Зелье MP: {before} → {new_mp_a} (+{new_mp_a - before})")

        elif action.startswith("skill_"):
            code = action.replace("skill_", "")
            s = get_skill(code)
            if not s:
                continue
            if new_mp_a < s["mp_cost"]:
                log_a.append(f"❌ «{s['name']}» — не хватило MP ({new_mp_a}/{s['mp_cost']})")
                continue
            new_mp_a -= s["mp_cost"]
            effect = s["effect"]
            mult = skill_multiplier(user_a, code)
            if effect == "damage":
                t_pdef = calc_p_def(user_b)
                t_mdef = calc_m_def(user_b)
                dmg_type = get_dmg_type(user_a)
                if s.get("pierce"):
                    base = calc_damage(user_a)
                else:
                    base = calc_damage(user_a)
                    base = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
                if dmg_type == "magic":
                    base = int(base * racial_magic_mult(user_a) * a_magic)
                else:
                    base = int(base * a_dmg)
                dmg = int(base * mult * faction_mult(user_a, "dmg_mult")
                          * racial_low_hp_mult(user_a) * a_rage * a_range * def_mult_b)
                if s.get("double"):
                    dmg *= 2
                # execute
                if s.get("execute") and new_hp_b < max_hp_b * 0.20:
                    dmg = int(dmg * s["execute"])
                    log_a.append(f"✨ {s['name']}: <b>ДОБИВАНИЕ ×{s['execute']}</b>")
                dmg_a_to_b += dmg
                if s.get("pierce"):
                    log_a.append(f"✨ {s['name']} (игнор брони): {dmg} урона")
                else:
                    log_a.append(f"✨ {s['name']}: {dmg} урона")
                # lifesteal скилла
                if s.get("lifesteal") and dmg > 0:
                    heal = int(dmg * s["lifesteal"])
                    new_hp_a = min(max_hp_a, new_hp_a + heal)
                    log_a.append(f"💗 Вампиризм скилла: +{heal} HP")
            elif effect == "heal":
                heal = int(max_hp_a * mult * racial_heal_mult(user_a))
                new_hp_a = min(max_hp_a, new_hp_a + heal)
                log_a.append(f"✨ {s['name']}: +{heal} HP")
            elif effect == "buff_atk":
                log_a.append(f"✨ {s['name']}: +атака")
            elif effect == "buff_def":
                log_a.append(f"✨ {s['name']}: +защита")
            elif effect == "debuff":
                log_a.append(f"✨ {s['name']}: дебафф на соперника")
            elif effect == "stun":
                log_a.append(f"✨ {s['name']}: соперник оглушён")

    # ============ ОЧЕРЕДЬ B (по порядку) ============
    for action in actions_b:
        if action == "attack":
            eff_b = effective_stats(user_b)
            t_pdef = calc_p_def(user_a)
            t_mdef = calc_m_def(user_a)
            dmg_type = get_dmg_type(user_b)
            base = calc_damage(user_b)
            dmg = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
            if dmg_type == "magic":
                dmg = int(dmg * racial_magic_mult(user_b) * b_magic)
            else:
                dmg = int(dmg * b_dmg)
            dmg = int(dmg * faction_mult(user_b, "dmg_mult"))
            dmg = int(dmg * racial_low_hp_mult(user_b) * b_rage * b_range)
            crit_chance = (eff_b["dex"] + racial_crit_bonus(user_b)
                           + get_crit_bonus(user_b) + b_crit)
            if user_b.get("pet_type") == "owl":
                crit_chance += 15
            is_crit = random.randint(1, 100) <= crit_chance
            if is_crit:
                dmg = int(dmg * 2)
            dmg = int(dmg * def_mult_a)
            dmg_b_to_a += dmg
            line = f"⚔️ Атака: {dmg} урона" + (" 💥 КРИТ!" if is_crit else "")
            if b_range > 1.0:
                line += " 🎯 <i>(дальний бой)</i>"
            if b_rage > 1.05:
                line += f" 😈 <i>(ярость ×{b_rage:.2f})</i>"
            log_b.append(line)
            if b_lifesteal > 0 and dmg > 0:
                heal = int(dmg * b_lifesteal)
                new_hp_b = min(max_hp_b, new_hp_b + heal)
                log_b.append(f"😈 Вампиризм: +{heal} HP")

        elif action == "defend":
            log_b.append("🛡 Защита")

        elif action == "potion_hp":
            if new_hp_b >= max_hp_b:
                log_b.append("💚 HP полное — зелье не использовано")
            elif gold_b < POTION_PRICE:
                log_b.append(f"❌ Нет {POTION_PRICE}💰 на зелье HP")
            else:
                gold_b -= POTION_PRICE
                before = new_hp_b
                new_hp_b = min(max_hp_b, new_hp_b + POTION_HEAL)
                log_b.append(f"💚 Зелье HP: {before} → {new_hp_b} (+{new_hp_b - before})")

        elif action == "potion_mp":
            if new_mp_b >= max_mp_b:
                log_b.append("🔮 MP полное — зелье не использовано")
            elif gold_b < MP_POTION_PRICE:
                log_b.append(f"❌ Нет {MP_POTION_PRICE}💰 на зелье MP")
            else:
                gold_b -= MP_POTION_PRICE
                before = new_mp_b
                new_mp_b = min(max_mp_b, new_mp_b + MP_POTION_RESTORE)
                log_b.append(f"🔮 Зелье MP: {before} → {new_mp_b} (+{new_mp_b - before})")

        elif action.startswith("skill_"):
            code = action.replace("skill_", "")
            s = get_skill(code)
            if not s:
                continue
            if new_mp_b < s["mp_cost"]:
                log_b.append(f"❌ «{s['name']}» — не хватило MP ({new_mp_b}/{s['mp_cost']})")
                continue
            new_mp_b -= s["mp_cost"]
            effect = s["effect"]
            mult = skill_multiplier(user_b, code)
            if effect == "damage":
                t_pdef = calc_p_def(user_a)
                t_mdef = calc_m_def(user_a)
                dmg_type = get_dmg_type(user_b)
                if s.get("pierce"):
                    base = calc_damage(user_b)
                else:
                    base = calc_damage(user_b)
                    base = apply_defense(base, t_mdef if dmg_type == "magic" else t_pdef)
                if dmg_type == "magic":
                    base = int(base * racial_magic_mult(user_b) * b_magic)
                else:
                    base = int(base * b_dmg)
                dmg = int(base * mult * faction_mult(user_b, "dmg_mult")
                          * racial_low_hp_mult(user_b) * b_rage * b_range * def_mult_a)
                if s.get("double"):
                    dmg *= 2
                if s.get("execute") and new_hp_a < max_hp_a * 0.20:
                    dmg = int(dmg * s["execute"])
                    log_b.append(f"✨ {s['name']}: <b>ДОБИВАНИЕ ×{s['execute']}</b>")
                dmg_b_to_a += dmg
                if s.get("pierce"):
                    log_b.append(f"✨ {s['name']} (игнор брони): {dmg} урона")
                else:
                    log_b.append(f"✨ {s['name']}: {dmg} урона")
                if s.get("lifesteal") and dmg > 0:
                    heal = int(dmg * s["lifesteal"])
                    new_hp_b = min(max_hp_b, new_hp_b + heal)
                    log_b.append(f"💗 Вампиризм скилла: +{heal} HP")
            elif effect == "heal":
                heal = int(max_hp_b * mult * racial_heal_mult(user_b))
                new_hp_b = min(max_hp_b, new_hp_b + heal)
                log_b.append(f"✨ {s['name']}: +{heal} HP")
            elif effect == "buff_atk":
                log_b.append(f"✨ {s['name']}: +атака")
            elif effect == "buff_def":
                log_b.append(f"✨ {s['name']}: +защита")
            elif effect == "debuff":
                log_b.append(f"✨ {s['name']}: дебафф на соперника")
            elif effect == "stun":
                log_b.append(f"✨ {s['name']}: соперник оглушён")

    # ============ УКЛОНЕНИЕ (плут) ============
    # A уклоняется от всего урона B?
    if dmg_b_to_a > 0 and a_dodge > 0 and random.randint(1, 100) <= a_dodge:
        log_a.append(f"💨 <b>Уклонение!</b> Ты уклонился от всех атак ({dmg_b_to_a} урона)")
        log_b.append(f"💨 {user_a['char_name']} уклонился от твоих атак")
        dmg_b_to_a = 0
    # B уклоняется от всего урона A?
    if dmg_a_to_b > 0 and b_dodge > 0 and random.randint(1, 100) <= b_dodge:
        log_b.append(f"💨 <b>Уклонение!</b> Ты уклонился от всех атак ({dmg_a_to_b} урона)")
        log_a.append(f"💨 {user_b['char_name']} уклонился от твоих атак")
        dmg_a_to_b = 0

    # ============ ПРИМЕНЕНИЕ УРОНА ============
    new_hp_b = max(0, new_hp_b - dmg_a_to_b)
    new_hp_a = max(0, new_hp_a - dmg_b_to_a)

    await g.db.update_hp(uid_a, new_hp_a)
    await g.db.update_hp(uid_b, new_hp_b)
    await g.db.update_mp(uid_a, new_mp_a)
    await g.db.update_mp(uid_b, new_mp_b)
    if gold_a != user_a["gold"]:
        await g.db.set_gold(uid_a, gold_a)
    if gold_b != user_b["gold"]:
        await g.db.set_gold(uid_b, gold_b)

    if dmg_a_to_b > 0:
        await g.db.incr_combat_dmg_dealt(uid_a, dmg_a_to_b)
        await g.db.incr_combat_dmg_taken(uid_b, dmg_a_to_b)
    if dmg_b_to_a > 0:
        await g.db.incr_combat_dmg_dealt(uid_b, dmg_b_to_a)
        await g.db.incr_combat_dmg_taken(uid_a, dmg_b_to_a)

    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
            new_hp_b, uid_a
        )
        await conn.execute(
            "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
            new_hp_a, uid_b
        )

    await g.db.clear_pending_actions(uid_a)
    await g.db.clear_pending_actions(uid_b)
    await g.db.set_my_ready(uid_a, 0)
    await g.db.set_my_ready(uid_b, 0)
    await g.db.incr_combat_round(uid_a)
    await g.db.incr_combat_round(uid_b)

    a_dead = new_hp_a <= 0
    b_dead = new_hp_b <= 0

    if a_dead or b_dead:
        if a_dead and b_dead:
            await _pvp_draw(uid_a, uid_b)
        elif b_dead:
            await pvp_end(winner_id=uid_a, loser_id=uid_b, stake=combat_a["stake"])
        else:
            await pvp_end(winner_id=uid_b, loser_id=uid_a, stake=combat_a["stake"])
        return

    text_a = "<b>🗡 Твои действия:</b>\n"
    if log_a:
        text_a += "\n".join(f"  {x}" for x in log_a)
    else:
        text_a += "  <i>— ничего —</i>"
    text_a += "\n\n<b>💀 Что делал соперник:</b>\n"
    if log_b:
        text_a += "\n".join(f"  {x}" for x in log_b)
    else:
        text_a += "  <i>— ничего —</i>"
    if dmg_a_to_b > 0:
        text_a += f"\n\n💥 <b>Ты нанёс: {dmg_a_to_b}</b>"
    if dmg_b_to_a > 0:
        text_a += f"\n💔 <b>Получил: {dmg_b_to_a}</b>"

    text_b = "<b>🗡 Твои действия:</b>\n"
    if log_b:
        text_b += "\n".join(f"  {x}" for x in log_b)
    else:
        text_b += "  <i>— ничего —</i>"
    text_b += "\n\n<b>💀 Что делал соперник:</b>\n"
    if log_a:
        text_b += "\n".join(f"  {x}" for x in log_a)
    else:
        text_b += "  <i>— ничего —</i>"
    if dmg_b_to_a > 0:
        text_b += f"\n\n💥 <b>Ты нанёс: {dmg_b_to_a}</b>"
    if dmg_a_to_b > 0:
        text_b += f"\n💔 <b>Получил: {dmg_a_to_b}</b>"

    user_a = await g.db.get_user(uid_a)
    user_b = await g.db.get_user(uid_b)
    combat_a = await g.db.get_combat(uid_a)
    combat_b = await g.db.get_combat(uid_b)

    await send_pvp_state(uid_a, user_a, combat_a, edit_message=None)
    await send_pvp_state(uid_b, user_b, combat_b, edit_message=None)

    try:
        await g.bot.send_message(uid_a, text_a, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        await g.bot.send_message(uid_b, text_b, parse_mode=ParseMode.HTML)
    except Exception:
        pass


@router.callback_query(F.data == "pvp_noop")
async def pvp_noop(c: CallbackQuery):
    await c.answer("⏳ Ждём соперника...", show_alert=False)


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


async def _pvp_draw(uid_a, uid_b):
    await g.db.end_combat(uid_a)
    await g.db.end_combat(uid_b)
    for uid in (uid_a, uid_b):
        u = await g.db.get_user(uid)
        nm = calc_max_hp(u)
        await g.db.update_hp_max(uid, nm, nm)
        try:
            await g.bot.send_message(uid,
                "🤝 <b>НИЧЬЯ!</b>\n\nОба героя пали одновременно. Ставки возвращены.",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def pvp_end(winner_id, loser_id, stake):
    wc = await g.db.get_combat(winner_id)
    lc = await g.db.get_combat(loser_id)
    w_rounds = wc.get("round_num", 1) if wc else 1
    w_dmg_dealt = wc.get("total_dmg_dealt", 0) if wc else 0
    w_dmg_taken = wc.get("total_dmg_taken", 0) if wc else 0
    l_dmg_dealt = lc.get("total_dmg_dealt", 0) if lc else 0
    l_dmg_taken = lc.get("total_dmg_taken", 0) if lc else 0

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
                
# Старый NPC-зачёт
await g.db.progress_quest(winner_id, "win_duels", 1)
# Новый — timed_quest_progress (то что в /quests)
try:
    from handlers.quests import progress_quest as quest_progress
    await quest_progress(winner_id, "win_duels", 1)
except Exception:
    pass

    summary_winner = (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>ИТОГИ ДУЭЛИ</b>\n"
        f"🎯 Раундов: <b>{w_rounds}</b>\n"
        f"🗡 Нанесено: <b>{w_dmg_dealt}</b>\n"
        f"💔 Получено: <b>{w_dmg_taken}</b>\n"
        f"💰 Выигрыш: <b>{real}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    summary_loser = (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>ИТОГИ ДУЭЛИ</b>\n"
        f"🎯 Раундов: <b>{w_rounds}</b>\n"
        f"🗡 Нанесено: <b>{l_dmg_dealt}</b>\n"
        f"💔 Получено: <b>{l_dmg_taken}</b>\n"
        f"💰 Потеряно: <b>{real}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    try:
        await g.bot.send_message(winner_id,
            f"🏆 <b>ПОБЕДА!</b> над {l['char_name']}\n"
            f"+{real}💰 · Репутация +1\n\n{summary_winner}",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        await g.bot.send_message(loser_id,
            f"💀 <b>Поражение</b> от {w['char_name']}\n"
            f"−{real}💰 · Репутация −1\n\n{summary_loser}",
            reply_markup=main_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        pass
