"""Глобальный доступ к bot и db для хендлеров."""

bot = None
db = None


def set_globals(bot_instance, db_instance):
    global bot, db
    bot = bot_instance
    db = db_instance
