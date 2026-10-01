"""Всплывающие уведомления (отдельные сообщения)."""
import logging

from aiogram.enums import ParseMode

from core import globals as g


async def notify(chat_id, kind, text, subtitle=""):
    """Отправить компактное уведомление.

    kind: "level" | "item" | "achievement" | "boss" | "death" | "quest"
    """
    icons = {
        "level":       "⭐",
        "item":        "🎁",
        "achievement": "🏆",
        "boss":        "🐉",
        "death":       "💀",
        "quest":       "📜",
        "drop":        "💎",
    }
    titles = {
        "level":       "УРОВЕНЬ",
        "item":        "НОВЫЙ ПРЕДМЕТ",
        "achievement": "ДОСТИЖЕНИЕ",
        "boss":        "БОСС ПОВЕРЖЕН",
        "death":       "ТЫ ПАЛ В БОЮ",
        "quest":       "КВЕСТ ВЫПОЛНЕН",
        "drop":        "РЕДКИЙ ДРОП",
    }
    icon = icons.get(kind, "✨")
    title = titles.get(kind, "СОБЫТИЕ")

    msg = f"{icon} <b>{title}</b>\n"
    msg += f"{text}"
    if subtitle:
        msg += f"\n<i>{subtitle}</i>"

    try:
        await g.bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"notify error: {e}")


async def notify_level(chat_id, level, hp, mp):
    await notify(
        chat_id, "level",
        f"Уровень <b>{level}</b>!",
        f"❤️ HP: {hp} · 💧 MP: {mp} · +1 очко умений"
    )


async def notify_item(chat_id, item_name):
    await notify(chat_id, "item", f"<b>{item_name}</b>", "Проверь 🎒 Инвентарь")


async def notify_achievement(chat_id, achievement_name):
    await notify(chat_id, "achievement", f"<b>{achievement_name}</b>")


async def notify_boss(chat_id, boss_name):
    await notify(chat_id, "boss", f"<b>{boss_name}</b>", "Полная награда получена")


async def notify_quest(chat_id, quest_title, gold, xp):
    await notify(
        chat_id, "quest",
        f"<b>{quest_title}</b>",
        f"+{gold}💰 · +{xp} XP"
    )


async def notify_drop(chat_id, item_name, source=""):
    sub = f"Источник: {source}" if source else ""
    await notify(chat_id, "drop", f"<b>{item_name}</b>", sub)


async def notify_book(chat_id, book_name):
    await notify(
        chat_id, "drop",
        f"<b>{book_name}</b>",
        "Изучи через ✨ Скилы → 📖 Изучить книгу"
    )


async def notify_recipe(chat_id, recipe_name):
    await notify(
        chat_id, "drop",
        f"<b>📜 Рецепт: {recipe_name}</b>",
        "Открой ⚒️ Кузница → 📜 Рецепты"
    )
