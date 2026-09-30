"""Старт: /start, согласие, создание героя, главное меню, /newchar."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton)
from aiogram.enums import ParseMode

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS, classes_for_race
from core.formulas import (
    calc_stats, calc_max_hp, calc_max_mp, faction_mult,
)
from core.keyboards import (
    main_kb, race_selection_kb, faction_selection_kb, pvp_kb,
)
from core.texts import CONSENT_TEXT
from config import ADMIN_IDS
import world as W


router = Router()


def _consent_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Согласен (18+)", callback_data="consent_yes"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no"),
    ]])


@router.message(Command("start"))
async def start(m: Message):
    args = m.text.split()
    referrer_id = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = await g.db.get_user(m.from_user.id, m.from_user.username or "")

    if referrer_id and user["referred_by"] == 0:
        if await g.db.set_referrer(m.from_user.id, referrer_id):
            await m.answer("🎉 Вы пришли по приглашению!")
            try:
                await g.bot.send_message(referrer_id,
                    "🎉 По вашей ссылке пришёл новый игрок! +10 к максимуму энергии.")
            except Exception:
                pass
            user = await g.db.get_user(m.from_user.id)

    if not user["consent_given"]:
        await m.answer(CONSENT_TEXT, reply_markup=_consent_kb(), parse_mode=ParseMode.HTML)
        return

    if not user["race"] or user["race"] not in RACES:
        await show_race_selection(m); return
    if not user["class"] or user["class"] not in CLASSES:
        await show_class_selection(m, user["race"]); return
    if not user["faction"]:
        await show_faction_selection(m); return
    if not user["char_name"]:
        await m.answer("✏️ Как зовут вашего героя? (2–20 символов)")
        return

    combat = await g.db.get_combat(m.from_user.id)
    if combat:
        if combat.get("is_pvp"):
            await m.answer("⚔️ Ты в дуэли!", reply_markup=pvp_kb(combat["my_turn"]))
        else:
            from services.combat_service import send_combat_state
            await send_combat_state(m.chat.id, user, combat, "Ты в бою!")
        return

    await show_main_menu(m, user)


@router.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    await g.db.give_consent(c.from_user.id)
    await c.message.edit_text("✅ Согласие получено. Создадим героя!",
                              parse_mode=ParseMode.HTML)
    await show_race_selection(c.message)


@router.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text("❌ Без согласия бот не сохранит прогресс.")


# ================= НОВЫЙ ГЕРОЙ =================
@router.message(Command("newchar"))
async def newchar_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("У тебя ещё нет героя. Начни через /start."); return
    if await g.db.get_combat(m.from_user.id):
        await m.answer("⚔️ Сначала закончи бой!"); return

    # Показать предупреждение
    warn = (f"⚠️ <b>Создать нового героя?</b>\n\n"
            f"Текущий герой: <b>{u['char_name']}</b> "
            f"({RACES.get(u['race'], {}).get('name', '?')}, "
            f"{CLASSES.get(u['class'], {}).get('name', '?')}, ур. {u['level']})\n\n"
            f"<b>Что будет сброшено:</b>\n"
            f"• Имя, раса, класс, фракция\n"
            f"• Уровень, XP, HP, MP, статы\n"
            f"• Золото, материалы, инвентарь\n"
            f"• Питомец, гильдия, скилы\n"
            f"• Достижения, репутация, PvP-статистика\n\n"
            f"<b>Что сохранится:</b>\n"
            f"• Энергия и её максимум\n"
            f"• Премиум\n"
            f"• Рефералы\n\n"
            f"<i>Это действие нельзя отменить!</i>")

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Создать нового",
                             callback_data="newchar_confirm"),
        InlineKeyboardButton(text="❌ Отмена",
                             callback_data="newchar_cancel"),
    ]])
    await m.answer(warn, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "newchar_confirm")
async def newchar_confirm_cb(c: CallbackQuery):
    await g.db.reset_character(c.from_user.id)
    try:
        await c.message.edit_text(
            "🔄 <b>Герой сброшен.</b>\n\nВыбери расу:",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
    await show_race_selection(c.message)


@router.callback_query(F.data == "newchar_cancel")
async def newchar_cancel_cb(c: CallbackQuery):
    try:
        await c.message.edit_text("✅ Отменено. Герой сохранён.")
    except Exception:
        pass
    await c.answer()


# ================= СОЗДАНИЕ ГЕРОЯ =================
async def show_race_selection(m):
    # Показать обычные всем, премиум — только премиум-игрокам
    u = await g.db.get_user(m.from_user.id)
    is_prem = bool(u.get("is_premium"))
    available = {}
    for code, r in RACES.items():
        if r.get("premium") and not is_prem:
            continue
        available[code] = r
    hint = ""
    if not is_prem:
        hint = "\n\n💎 <i>Премиум-расы откроются с подпиской.</i>"
    await g.bot.send_message(m.chat.id, "🧝 <b>Выбери расу:</b>" + hint,
                             reply_markup=race_selection_kb(available),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("race_"))
async def on_race(c: CallbackQuery):
    code = c.data.replace("race_", "")
    if code not in RACES:
        await c.answer("Ошибка"); return
    # Проверка премиума
    if RACES[code].get("premium"):
        u = await g.db.get_user(c.from_user.id)
        if not u.get("is_premium"):
            await c.answer("💎 Только для премиум-игроков", show_alert=True); return
    await g.db.set_race(c.from_user.id, code)
    await g.db.set_class(c.from_user.id, "")
    await c.message.edit_text(f"✅ Раса: <b>{RACES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_class_selection(c.message, code)


async def show_class_selection(m, race_code):
    classes = classes_for_race(race_code)
    if not classes:
        await g.bot.send_message(m.chat.id, "❌ Для этой расы нет классов.")
        return
    rows = []
    for code, cl in classes.items():
        rows.append([InlineKeyboardButton(
            text=f"{cl['name']} — {cl['desc']}",
            callback_data=f"class_{code}"
        )])
    await g.bot.send_message(m.chat.id, "⚔️ <b>Выбери класс:</b>",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("class_"))
async def on_class(c: CallbackQuery):
    code = c.data.replace("class_", "")
    if code not in CLASSES:
        await c.answer("Ошибка"); return
    user = await g.db.get_user(c.from_user.id)
    if user["race"] not in CLASSES[code]["races"]:
        await c.answer("Этот класс недоступен твоей расе", show_alert=True)
        return
    await g.db.set_class(c.from_user.id, code)
    stats = calc_stats(user["race"], code)
    user_tmp = dict(user)
    user_tmp["class"] = code
    for k in ["str", "dex", "con", "int", "wit", "men"]:
        user_tmp[f"stat_{k}"] = stats[k]
    hp = calc_max_hp(user_tmp)
    mp = calc_max_mp(user_tmp)
    await g.db.update_stats(c.from_user.id, stats, hp, mp)
    await c.message.edit_text(f"✅ Класс: <b>{CLASSES[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await show_faction_selection(c.message)


async def show_faction_selection(m):
    await g.bot.send_message(m.chat.id, "🏛 <b>Выбери фракцию:</b>",
                             reply_markup=faction_selection_kb(FACTIONS),
                             parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("faction_"))
async def on_faction(c: CallbackQuery):
    code = c.data.replace("faction_", "")
    if code not in FACTIONS:
        await c.answer("Ошибка"); return
    await g.db.set_faction(c.from_user.id, code)
    await c.message.edit_text(f"✅ Фракция: <b>{FACTIONS[code]['name']}</b>",
                              parse_mode=ParseMode.HTML)
    await g.bot.send_message(c.from_user.id,
                             "✏️ Напиши <b>имя героя</b> (2–20 символов).",
                             parse_mode=ParseMode.HTML)


# ================= ГЛАВНОЕ МЕНЮ =================
async def show_main_menu(m, user):
    loc_code = user.get("location_code", "village")
    loc = W.get_location(loc_code) or {}
    event = await g.db.get_active_event(loc_code)
    owner = await g.db.get_location_owner(loc_code)
    is_admin = user["user_id"] in ADMIN_IDS
    admin_tag = " 🛠 <i>ADMIN</i>" if is_admin else ""

    header = f"🎮 <b>С возвращением, {user['char_name']}!</b>{admin_tag}\n\n"
    header += f"⭐ Ур. {user['level']} · XP: {user['xp']}\n"
    header += f"❤️ HP: {user['hp']}/{user['max_hp']}"
    if user.get("max_mp", 0) > 0:
        header += f" · 💧 MP: {user.get('mp', 0)}/{user.get('max_mp', 0)}"
    header += "\n"
    if user.get("is_premium"):
        header += "⚡ Энергия: ∞\n"
    else:
        header += f"⚡ Энергия: {user.get('energy', 0)}/{user.get('energy_max', 20)}\n"
    header += f"💰 Золото: {user['gold']}\n"
    header += f"📍 <b>{loc.get('name', '?')}</b>"
    if owner:
        header += f" 🏴 [{owner.get('guild_tag', '?')}]"
    header += "\n"
    if event:
        header += f"\n{event['event_name']}: <i>{event['event_desc']}</i>\n"
    header += "\nОпиши действие или жми кнопки 👇"
    await m.answer(header, reply_markup=main_kb(), parse_mode=ParseMode.HTML)
