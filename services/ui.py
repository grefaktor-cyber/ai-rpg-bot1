"""Утилиты UI: автоочистка меню + FakeMessage + локальные картинки."""
import logging

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, FSInputFile

from core import globals as g


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
    """Обёртка для вызова xxx_cmd(m: Message) из callback."""
    def __init__(self, original_message, from_user, text=""):
        self.chat = original_message.chat
        self.from_user = from_user
        self.message_id = original_message.message_id
        self.bot = original_message.bot
        self.text = text
        self._real = original_message

    async def answer(self, text, **kwargs):
        return await self._real.answer(text, **kwargs)

    async def delete(self):
        try:
            return await self._real.delete()
        except Exception:
            return None


def fake_message(c: CallbackQuery, text=""):
    return FakeMessage(c.message, c.from_user, text=text)


async def send_menu(m, text, kb=None, uid=None):
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
    _last_menu.pop(uid, None)


# ================= КАРТИНКИ ИЗ ЛОКАЛЬНЫХ ФАЙЛОВ =================
async def send_location_photo(chat_id, loc_code, caption, kb=None):
    """Отправляет фото локации из локального файла.

    Если файл не найден или ошибка отправки — падает в send_message.
    Никогда не роняет хендлер.
    """
    from core.location_art import get_location_image_path

    path = get_location_image_path(loc_code)
    if path:
        try:
            await g.bot.send_photo(
                chat_id,
                photo=FSInputFile(path),
                caption=caption,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception as e:
            logging.warning(f"[LOC PHOTO] {loc_code} ({path}): {e}")

    # Fallback — обычный текст
    try:
        await g.bot.send_message(
            chat_id, caption, reply_markup=kb, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"[LOC PHOTO FALLBACK] {loc_code}: {e}")


async def send_boss_photo(chat_id, boss_code, caption, kb=None):
    """Отправляет фото босса из локального файла. Fallback — текст."""
    from core.location_art import get_boss_image_path

    path = get_boss_image_path(boss_code)
    if path:
        try:
            await g.bot.send_photo(
                chat_id,
                photo=FSInputFile(path),
                caption=caption,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception as e:
            logging.warning(f"[BOSS PHOTO] {boss_code} ({path}): {e}")

    try:
        await g.bot.send_message(
            chat_id, caption, reply_markup=kb, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"[BOSS PHOTO FALLBACK] {boss_code}: {e}")
