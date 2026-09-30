"""Туториал для новых игроков."""
from aiogram.enums import ParseMode

from core import globals as g


async def run_tutorial(uid, chat_id):
    step, finished = await g.db.get_tutorial_step(uid)
    if finished:
        return
    if step == 0:
        await g.bot.send_message(chat_id,
            "👋 <b>Добро пожаловать в мир!</b>\n\n"
            "Ты — герой в мире Lineage. Мир состоит из 12 локаций, "
            "соединённых дорогами. Исследуй, сражайся, становись сильнее.",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 1)
    elif step == 1:
        await g.bot.send_message(chat_id,
            "🚶 <b>Путешествия</b>\n\n"
            "Кнопка <b>🚶 Идти</b> — перемещает между локациями.\n"
            "Стартовая — Начальная деревня.",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 2)
    elif step == 2:
        await g.bot.send_message(chat_id,
            "📜 <b>NPC и квесты</b>\n\n"
            "В локациях живут NPC — Кузнец, Старейшина, Лесник. "
            "Команда /npc — открыть список NPC и взять квест.",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 3)
    elif step == 3:
        await g.bot.send_message(chat_id,
            "🏛 <b>Гильдии</b>\n\n"
            "Собери 1000💰 и создай гильдию. Гильдия может захватывать локации.",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 4)
    elif step == 4:
        await g.bot.send_message(chat_id,
            "🌍 <b>События</b>\n\n"
            "В локациях случаются нашествия, клады и мор. "
            "Проверяй /world — там видно, где сейчас жарко.",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 5)
    elif step == 5:
        await g.bot.send_message(chat_id,
            "💡 <b>Советы</b>\n\n"
            "• Заходи каждый день → 🎁 Награда\n"
            "• ⚒️ Кузница — крафт и улучшение предметов\n"
            "• 🐾 Питомец помогает в бою\n"
            "• /duel — сражайся с другими игроками\n"
            "• /quests — ежедневные квесты\n\n"
            "Удачи, герой! 🎮",
            parse_mode=ParseMode.HTML)
        await g.db.set_tutorial_step(uid, 99, finished=True)
