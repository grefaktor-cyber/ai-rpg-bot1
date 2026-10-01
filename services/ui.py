"""Утилиты UI: автоочистка меню."""
import logging

from aiogram.enums import ParseMode


# Запоминаем последнее меню бота: uid -> message_id
_last_menu = {}

# Все reply-кнопки меню (для удаления сообщения игрока)
MAIN_MENU_BUTTONS = {
    "🎮 Игра", "👥 Социум", "📊 Прогресс", "🌍 Мир",
    "🐉 Боссы", "❓ Помощь",
    # старые кнопки (если остались в кэше у игроков)
    "🎒 Инвентарь", "🛒 Магазин", "⭐ Профиль", "🏆 Достижения",
    "📋 Квесты", "🗺 Карта", "🚶 Идти", "👥 Кто здесь",
    "🐾 Питомец", "🏰 Подземелья", "⚒️ Кузница", "🏛 Гильдия",
    "✨ Скилы", "🎁 Награда", "🏅 Рейтинг", "💎 Премиум",
}


async def send_menu(m, text, kb=None, uid=None):
    """Отправить меню с автоудалением предыдущего.

    1. Удаляет предыдущее меню бота (если было).
    2. Удаляет сообщение игрока, если это была reply-кнопка.
    3. Отправляет новое меню.
    4. Запоминает его.
    """
    uid = uid or m.from_user.id
    chat_id = m.chat.id

    # 1. Удаляем предыдущее меню бота
    prev_id = _last_menu.pop(uid, None)
    if prev_id:
        try:
            await m.bot.delete_message(chat_id, prev_id)
        except Exception as e:
            logging.debug(f"Не удалось удалить меню {prev_id}: {e}")

    # 2. Удаляем сообщение игрока с reply-кнопкой
    text_btn = (getattr(m, "text", "") or "").strip()
    if text_btn in MAIN_MENU_BUTTONS:
        try:
            await m.bot.delete_message(chat_id, m.message_id)
        except Exception as e:
            logging.debug(f"Не удалось удалить сообщение игрока: {e}")

    # 3. Отправляем новое + 4. запоминаем
    try:
        sent = await m.bot.send_message(
            chat_id, text, reply_markup=kb, parse_mode=ParseMode.HTML,
        )
        _last_menu[uid] = sent.message_id
        return sent
    except Exception as e:
        logging.error(f"send_menu error: {e}")
        return None


async def edit_or_send(c, text, kb=None):
    """Для callback: пытается edit_text, иначе send_message + запоминает."""
    try:
        await c.message.edit_text(text, reply_markup=kb,
                                   parse_mode=ParseMode.HTML)
        return c.message
    except Exception:
        try:
            sent = await c.message.answer(text, reply_markup=kb,
                                            parse_mode=ParseMode.HTML)
            return sent
        except Exception:
            return None




async def close_menu(c: CallbackQuery):
    """Удалить сообщение с inline-меню при нажатии «Закрыть».
    Если удалить нельзя (например, уже удалено) — просто убираем кнопки.
    """
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
    """Сбросить запомненное меню (при бое)."""
    _last_menu.pop(uid, None)
