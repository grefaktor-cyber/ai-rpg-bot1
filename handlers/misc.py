"""Команды: /help, /ref, /revoke, /reset, /tutorial + кнопка Помощь."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.texts import HELP_TEXT

router = Router()

_bot_username = None


async def _get_bot_username():
    global _bot_username
    if _bot_username is None:
        me = await g.bot.get_me()
        _bot_username = me.username
    return _bot_username


def _help_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Бой", callback_data="help_combat"),
         InlineKeyboardButton(text="✨ Скилы", callback_data="help_skills")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="help_economy"),
         InlineKeyboardButton(text="🌍 Мир", callback_data="help_world")],
        [InlineKeyboardButton(text="🏛 Гильдии", callback_data="help_guild"),
         InlineKeyboardButton(text="💎 Премиум", callback_data="help_premium")],
        [InlineKeyboardButton(text="🔗 Реф-ссылка", callback_data="ref_show"),
         InlineKeyboardButton(text="❌ Закрыть", callback_data="help_close")],
    ])


# ================= ПОМОЩЬ =================
@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_cmd(m: Message):
    await m.answer(HELP_TEXT, reply_markup=_help_menu_kb(),
                   parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "help_close")
async def help_close_cb(c):
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data == "help_back")
async def help_back(c):
    try:
        await c.message.edit_text(HELP_TEXT, reply_markup=_help_menu_kb(),
                                  parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("help_"))
async def help_topic(c):
    topic = c.data.replace("help_", "")
    if topic in ("close", "back"):
        await c.answer(); return

    topics = {
        "combat": (
            "⚔️ <b>Бой</b>\n\n"
            "Пиши действие — ИИ опишет сцену и запустит бой.\n"
            "Например: <code>атакую гоблина</code>\n\n"
            "<b>В бою кнопки:</b>\n"
            "• ⚔️ Атака — базовый удар\n"
            "• 🛡 Защита — блок 50% урона + реген 5% HP\n"
            "• ✨ Скил — тратит MP\n"
            "• 💚 Зелье — +30 HP за 25💰\n"
            "• 🔮 Зелье MP — +40 MP за 25💰\n"
            "• 🏃 Бежать — 50% (не от боссов)\n\n"
            "<b>Урон зависит от:</b>\n"
            "• Тип (физ/ловкий/маг) × P.Def/M.Def\n"
            "• Крит (DEX + бонусы сета)\n"
            "• Экипировки"
        ),
        "skills": (
            "✨ <b>Скилы</b>\n\n"
            "Открой <b>✨ Скилы</b> — увидишь 3 слота.\n\n"
            "<b>Настроить:</b>\n"
            "1. «🎯 Настроить слоты» → выбери слот\n"
            "2. Выбери скил из списка\n\n"
            "<b>Прокачка:</b>\n"
            "• Каждый уровень даёт <b>+1 очко умений</b>\n"
            "• «⬆️ Прокачать скилы» → ур.1 → 3\n"
            "• За уровень скила <b>+15% к эффекту</b>\n\n"
            "<b>MP:</b>\n"
            "• +5% в бою (в раунд)\n"
            "• +20% вне боя (за действие)"
        ),
        "economy": (
            "💰 <b>Экономика</b>\n\n"
            "<b>Заработок:</b>\n"
            "• Убийство монстров (уровень × 10)\n"
            "• Боссов (×3)\n"
            "• Квесты NPC\n"
            "• Продажа (/sell — 60% цены)\n\n"
            "<b>Траты:</b>\n"
            "• Магазин (🛒)\n"
            "• Кузница (⚒️)\n"
            "• Подземелья (🏰)\n"
            "• Зелья (25💰)\n\n"
            "<b>Обмен:</b>\n"
            "• /trade Имя — обмен\n"
            "• /pay Имя Сумма — золото\n"
            "• /drop + /pickup"
        ),
        "world": (
            "🌍 <b>Мир</b>\n\n"
            "<b>12 локаций</b>, соединённых дорогами.\n"
            "Переход — 🚶 Идти или /travel.\n\n"
            "<b>События</b> (проверь /world):\n"
            "• 🔴 Нашествие — +30% XP\n"
            "• 💰 Клад — +100% золота\n"
            "• 🕊 Затишье — меньше врагов\n"
            "• ☠️ Мор — враги сильнее\n"
            "• ✨ Благословение — +50% XP\n\n"
            "<b>Боссы</b> — уникальные враги.\n"
            "Дают ×3 награды."
        ),
        "guild": (
            "🏛 <b>Гильдии</b>\n\n"
            "<b>Создать:</b> /guild → 1000💰\n"
            "<b>Пригласить:</b> /guild_invite Ник\n"
            "<b>Захватить локацию:</b> 3+ члена здесь\n\n"
            "Захват даёт <b>+15% золота и +10% XP</b>."
        ),
        "premium": (
            "💎 <b>Премиум</b>\n\n"
            "Открой <b>💎 Премиум</b> в меню.\n\n"
            "<b>Что даёт:</b>\n"
            "• Безлимит энергии\n"
            "• ×2 регенерация\n"
            "• Премиум-расы (Демон, Ангел, Плут)\n\n"
            "Оплата — Telegram Stars."
        ),
    }
    text = topics.get(topic)
    if not text:
        await c.answer("Раздел не найден"); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back")]])
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await c.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()


# ================= РЕФЕРАЛЬНАЯ ССЫЛКА =================
@router.message(Command("ref"))
async def ref_cmd(m: Message):
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    await _show_ref(m.chat.id, u)


@router.callback_query(F.data == "ref_show")
async def ref_show_cb(c):
    u = await g.db.get_user(c.from_user.id)
    await _show_ref(c.message.chat.id, u)
    await c.answer()


async def _show_ref(chat_id, u):
    username = await _get_bot_username()
    link = f"https://t.me/{username}?start=ref_{u['user_id']}"
    count = u.get("referral_count", 0)
    energy_bonus = count * 10
    text = (
        f"👥 <b>Приглашение друзей</b>\n\n"
        f"За каждого друга по твоей ссылке:\n"
        f"• <b>+10 к максимуму энергии</b> навсегда\n"
        f"• +1 к счётчику\n\n"
        f"<b>Твоя ссылка:</b>\n"
        f"<code>{link}</code>\n\n"
        f"📊 Приглашено: <b>{count}</b>\n"
        f"⚡ Бонус: <b>+{energy_bonus}</b> к максимуму\n\n"
        f"<i>Скопируй ссылку и отправь другу.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📤 Поделиться",
            url=f"https://t.me/share/url?url={link}&text=Играю в RPG с нейросетью!"
        ),
    ]])
    await g.bot.send_message(chat_id, text, reply_markup=kb,
                             parse_mode=ParseMode.HTML)


# ================= ПРОЧЕЕ =================
@router.message(Command("revoke"))
async def revoke(m: Message):
    await g.db.revoke_consent(m.from_user.id)
    await m.answer("🗑 Согласие отозвано.")


@router.message(Command("reset"))
async def reset(m: Message):
    await g.db.update_story(m.from_user.id, "")
    await m.answer("🔄 История сброшена.")


@router.message(Command("tutorial"))
async def tutorial_cmd(m: Message):
    from handlers.onboarding import offer_tutorial
    u = await g.db.get_user(m.from_user.id)
    if not u["char_name"]:
        await m.answer("Сначала создай героя."); return
    await offer_tutorial(m.chat.id, m.from_user.id, force=True)
