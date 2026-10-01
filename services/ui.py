"""Утилиты UI: автоочистка меню + FakeMessage для вызова cmd из callback."""
import logging

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery


_last_menu = {}

MAIN_MENU_BUTTONS = {
    "🎮 Игра", "👥 Социум", "📊 Прогресс", "🌍 Мир",
    "🐉 Боссы", "❓ Помощь",
    "🎒 Инвентарь", "🛒 Магазин", "⭐ Профиль", "🏆 Достижения",
    "📋 Квесты", "🗺 Карта", "🚶 Идти", "👥 Кто здесь",
    "🐾 Питомец", "🏰 Подземелья", "⚒️ Кузница", "🏛 Гильдия",
    "✨ Скилы", "🎁 Награда", "🏅 Рейтинг", "💎 Премиум",
}


class FakeMessage:
    """Обёртка для вызова `xxx_cmd(m: Message)` из callback.

    from_user — настоящий игрок (c.from_user), а не бот (c.message.from_user).
    Все остальные атрибуты берутся из оригинального сообщения бота.
    """
    def __init__(self, original_message, from_user):
        self.chat = original_message.chat
        self.from_user = from_user
        self.message_id = original_message.message_id
        self.bot = original_message.bot
        self.text = ""
        self._real = original_message

    async def answer(self, text, **kwargs):
        return await self._real.answer(text, **kwargs)

    async def delete(self):
        try:
            return await self._real.delete()
        except Exception:
            return None


def fake_message(c: CallbackQuery):
    """Создать FakeMessage из callback."""
    return FakeMessage(c.message, c.from_user)


async def send_menu(m, text, kb=None, uid=None):
    """Отправить меню с автоудалением предыдущего."""
    uid = uid or m.from_user.id
    chat_id = m.chat.id

    prev_id = _last_menu.pop(uid, None)
    if prev_id:
        try:
            await m.bot.delete_message(chat_id, prev_id)
        except Exception as e:
            logging.debug(f"Не удалось удалить меню {prev_id}: {e}")

    text_btn = (getattr(m, "text", "") or "").strip()
    if text_btn in MAIN_MENU_BUTTONS:
        try:
            await m.bot.delete_message(chat_id, m.message_id)
        except Exception as e:
            logging.debug(f"Не удалось удалить сообщение игрока: {e}")

    try:
        sent = await m.bot.send_message(
            chat_id, text, reply_markup=kb, parse_mode=ParseMode.HTML,
        )
        _last_menu[uid] = sent.message_id
        return sent
    except Exception as e:
        logging.error(f"send_menu error: {e}")
        return None


async def close_menu(c: CallbackQuery):
    """Удалить сообщение с inline-меню при «Закрыть»."""
    try:
        await c.message.delete()
        return True
    except Exception:
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return False


def forget_menu(uid):
    """Сбросить запомненное меню."""
    _last_menu.pop(uid, None)
