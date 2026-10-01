"""Хендлеры мировых боссов."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.world_bosses import WORLD_BOSSES, ATTACK_COOLDOWN_SEC, MIN_HP_PCT
from services.world_boss_service import attack_boss
import world as W

router = Router()


def _hp_bar(hp, max_hp, length=15):
    if max_hp <= 0:
        return "░" * length
    filled = int((hp / max_hp) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def _boss_text(boss, damage_list, u):
    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    bar = _hp_bar(boss["current_hp"], boss["max_hp"])

    dmg_type = boss_data.get("dmg_type", "phys")
    dmg_type_icon = "🔮 Магия" if dmg_type == "magic" else "⚔️ Физика"
    text += (f"🐉 <b>{boss_data.get('name', '?')}</b> "
            f"(Ур. {boss_data.get('level', '?')})\n"
            f"<i>{boss_data.get('desc', '')}</i>\n\n"
            f"{bar}\n"
            f"HP: <b>{boss['current_hp']}/{boss['max_hp']}</b>\n"
            f"⚔️ Урон: ~{boss_data.get('attack_dmg', 100)} ({dmg_type_icon})\n"
            f"<i>Твоя {'M.Def' if dmg_type == 'magic' else 'P.Def'} защищает</i>\n\n")

    # HP игрока
    hp_pct = int((u["hp"] / max(1, u["max_hp"])) * 100)
    text += f"❤️ Твой HP: <b>{u['hp']}/{u['max_hp']}</b> ({hp_pct}%)\n"
    if hp_pct < int(MIN_HP_PCT * 100):
        text += f"⚠️ <b>HP < {int(MIN_HP_PCT*100)}% — атака заблокирована!</b>\n"
    text += "\n"

    text += f"<b>Топ по урону:</b>\n"
    if damage_list:
        for i, d in enumerate(damage_list):
            medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "•"))
            text += f"{medal} {d['username']} — {d['damage']}\n"
    else:
        text += "<i>Ещё никто не бил.</i>\n"
    return text


def _boss_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boss_attack")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="boss_refresh")],
    ])


@router.message(Command("boss"))
@router.message(F.text == "🐉 Боссы")
async def boss_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)

    if not boss:
        all_bosses = await g.db.get_all_active_world_bosses()
        text = "🐉 <b>Мировые боссы</b>\n\n"
        if all_bosses:
            text += "<b>Активны в мире:</b>\n"
            for b in all_bosses:
                bd = WORLD_BOSSES.get(b["boss_code"], {})
                loc_n = W.get_location(b["location_code"]).get("name", "?")
                text += f"• {bd.get('name', '?')} в «{loc_n}»\n"
                text += f"  HP: {b['current_hp']}/{b['max_hp']}\n\n"
            text += "<i>Иди в локацию босса и напиши /boss снова.</i>"
        else:
            text += ("<i>Сейчас в мире тихо.</i>\n\n"
                     "🕐 <b>Спавн: 14:00, 20:00, 02:00, 08:00 (МСК)</b>")
        await m.answer(text, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return

    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)
    text = _boss_text(boss, damage_list, u)
    await m.answer(text, reply_markup=_boss_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "boss_refresh")
async def boss_refresh_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        await c.answer("Босс больше не активен", show_alert=True)
        return

    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)
    text = _boss_text(boss, damage_list, u)
    try:
        await c.message.edit_text(text, reply_markup=_boss_kb(),
                                   parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer("🔄")


@router.callback_query(F.data == "boss_attack")
async def boss_attack_cb(c: CallbackQuery):
    uid = c.from_user.id
    u = await g.db.get_user(uid)

    ok, info = await attack_boss(uid)

    if not ok:
        err = info.get("error")
        if err == "cooldown":
            await c.answer(f"⏳ Кулдаун: {info['seconds']}с",
                           show_alert=True)
        elif err == "low_hp":
            await c.answer(
                f"⚠️ HP {info['hp']}/{info['max_hp']} "
                f"(нужно {info['pct']}%). Подлечись!",
                show_alert=True)
        elif err == "no_boss":
            await c.answer("Босс больше не активен", show_alert=True)
        else:
            await c.answer("Ошибка", show_alert=True)
        return

    if info.get("player_died"):
        await c.answer("💀 Ты пал от босса!", show_alert=True)
        try:
            await c.message.answer(
                f"💀 <b>Ты пал от лап босса!</b>\n\n"
                f"Потеряно <b>{info['lost_gold']}💰</b>\n"
                f"Ты очнулся в Начальной деревне.",
                reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return

    crit_txt = " 💥 КРИТ!" if info.get("is_crit") else ""
    msg = f"⚔️ -{info['my_damage']} боссу{crit_txt}\n💔 -{info['boss_atk']} тебе"
    await c.answer(msg, show_alert=False)

    if info.get("killed"):
        try:
            await c.message.edit_text("🏆 Босс побеждён! Награды выданы.")
        except Exception:
            pass
    else:
        await boss_refresh_cb(c)
