"""Хендлеры мировых боссов."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.world_bosses import WORLD_BOSSES
from core.formulas import calc_damage, effective_stats, get_dmg_type, get_crit_bonus, racial_crit_bonus
from services.world_boss_service import attack_boss
import world as W
import random

router = Router()


def _hp_bar(hp, max_hp, length=15):
    if max_hp <= 0:
        return "░" * length
    filled = int((hp / max_hp) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)

@router.message(F.text == "🐉 Боссы")
async def boss_kb_cmd(m: Message):
    await boss_cmd(m)


@router.message(Command("boss"))
async def boss_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return

    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)

    if not boss:
        # Показываем всех активных в других локациях
        all_bosses = await g.db.get_all_active_world_bosses()
        text = "🐉 <b>Мировые боссы</b>\n\n"
        if all_bosses:
            text += "<b>Активны в мире:</b>\n"
            for b in all_bosses:
                bd = WORLD_BOSSES.get(b["boss_code"], {})
                loc_n = W.get_location(b["location_code"]).get("name", "?")
                text += f"• {bd.get('name', '?')} в «{loc_n}»\n"
                text += f"  HP: {b['current_hp']}/{b['max_hp']}\n\n"
            text += "<i>Иди в локацию и напиши /boss снова.</i>"
        else:
            text += "<i>Сейчас в мире тихо. Боссы появляются раз в 6 часов.</i>"
        await m.answer(text, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
        return

    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    bar = _hp_bar(boss["current_hp"], boss["max_hp"])
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)

    text = (f"🐉 <b>{boss_data.get('name', '?')}</b>\n"
            f"<i>{boss_data.get('desc', '')}</i>\n\n"
            f"{bar}\n"
            f"HP: <b>{boss['current_hp']}/{boss['max_hp']}</b>\n"
            f"Ур. {boss_data.get('level', '?')}\n\n"
            f"<b>Топ по урону:</b>\n")
    if damage_list:
        for i, d in enumerate(damage_list):
            medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "•"))
            text += f"{medal} {d['username']} — {d['damage']}\n"
    else:
        text += "<i>Ещё никто не бил.</i>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boss_attack")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="boss_refresh")],
    ])
    await m.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "boss_refresh")
async def boss_refresh_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    loc_code = u.get("location_code", "village")
    boss = await g.db.get_active_world_boss(loc_code)
    if not boss:
        await c.answer("Босс больше не активен", show_alert=True)
        return

    boss_data = WORLD_BOSSES.get(boss["boss_code"], {})
    bar = _hp_bar(boss["current_hp"], boss["max_hp"])
    damage_list = await g.db.get_boss_damage_list(boss["id"], limit=5)

    text = (f"🐉 <b>{boss_data.get('name', '?')}</b>\n"
            f"<i>{boss_data.get('desc', '')}</i>\n\n"
            f"{bar}\n"
            f"HP: <b>{boss['current_hp']}/{boss['max_hp']}</b>\n"
            f"Ур. {boss_data.get('level', '?')}\n\n"
            f"<b>Топ по урону:</b>\n")
    for i, d in enumerate(damage_list):
        medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "•"))
        text += f"{medal} {d['username']} — {d['damage']}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boss_attack")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="boss_refresh")],
    ])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer("🔄")


@router.callback_query(F.data == "boss_attack")
async def boss_attack_cb(c: CallbackQuery):
    u = await g.db.get_user(c.from_user.id)
    if not u["char_name"]:
        await c.answer("Сначала создай героя", show_alert=True); return

    # Расчёт урона как в бою
    eff = effective_stats(u)
    base = calc_damage(u)
    crit_chance = eff["dex"] + racial_crit_bonus(u) + get_crit_bonus(u)
    if u.get("pet_type") == "owl":
        crit_chance += 15
    is_crit = random.randint(1, 100) <= crit_chance
    dmg = base
    if is_crit:
        dmg = int(dmg * 2)

    ok, info = await attack_boss(c.from_user.id, dmg)
    if not ok:
        await c.answer("Босс больше не активен", show_alert=True)
        return

    crit_txt = " 💥 КРИТ!" if is_crit else ""
    await c.answer(f"⚔️ -{dmg} HP{crit_txt}", show_alert=False)

    # Обновляем экран
    if info.get("killed"):
        try:
            await c.message.edit_text("🏆 Босс побеждён! Награды выданы.")
        except Exception:
            pass
    else:
        await boss_refresh_cb(c)
