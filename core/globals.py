"""Глобальный доступ к bot и db для хендлеров.
Нужен, чтобы не передавать их через аргументы.
"""

bot = None
db = None


def set_globals(bot_instance, db_instance):
    """Вызывается один раз при старте из main.py."""
    global bot, db
    bot = bot_instance
    db = db_instance
