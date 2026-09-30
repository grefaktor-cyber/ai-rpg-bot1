"""Рассылка сообщений игрокам в локации."""
from aiogram.enums import ParseMode

from core import globals as g


async def broadcast_to_location(location_code, text, exclude_uid=0):
    """Отправить текст всем игрокам в локации, кроме exclude_uid."""
    players = await g.db.get_players_at_location(location_code, exclude_uid)
    for p in players:
        try:
            await g.bot.send_message(p["user_id"], text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
