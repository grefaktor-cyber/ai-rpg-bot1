"""Утилиты UI: автоочистка меню + FakeMessage + картинки + баннеры + анимации."""
import asyncio
import logging

from aiogram.enums import ParseMode, ChatAction
from aiogram.types import CallbackQuery, FSInputFile

from core import globals as g


_last_menu = {}     # uid -> message_id (меню)
_last_banner = {}   # uid -> (message_id, loc_code) — баннер локации

MAIN_MENU_BUTTONS = {
    "🎮 Игра", "👥 Социум", "📊 Прогресс", "🌍 Мир",
    "🐉 Боссы", "❓ Помощь",
    "🎒 Инвентарь", "🛒 Магазин", "⭐ Профиль", "🏆 Достижения",
    "📋 Квесты", "🗺 Карта", "🚶 Идти", "👥 Кто здесь",
    "🐾 Питомец", "🏰 Подземелья", "⚒️ Кузница", "🏛 Гильдия",
    "✨ Скилы", "🎁 Награда", "🏅 Рейтинг", "💎 Премиум",
}

CAPTION_LIMIT = 1000


# ================= АНИМАЦИИ =================
async def typing(chat_id):
    """Показывает «печатает…»."""
    try:
        await g.bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass


async def uploading_photo(chat_id):
    """Показывает «загружает фото…»."""
    try:
        await g.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
    except Exception:
        pass


class FakeMessage:
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


# ================= ОТПРАВКА МЕНЮ =================
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


async def send_menu_from_chat(chat_id, uid, text, kb=None):
    """Вариант для отправки из chat_id (без Message-объекта)."""
    prev_id = _last_menu.pop(uid, None)
    if prev_id:
        try:
            await g.bot.delete_message(chat_id, prev_id)
        except Exception:
            pass

    try:
        sent = await g.bot.send_message(
            chat_id, text, reply_markup=kb, parse_mode=ParseMode.HTML,
        )
        _last_menu[uid] = sent.message_id
        return sent
    except Exception as e:
        logging.error(f"send_menu_from_chat error: {e}")
        return None


async def send_banner(chat_id, uid, loc_code, caption):
    """Отправляет/обновляет баннер локации сверху.

    Если локация та же — не трогает. Если другая — удаляет старый, шлёт новый.
    """
    from core.location_art import get_location_image_path

    existing = _last_banner.get(uid)

    if existing and existing[1] == loc_code:
        return existing[0]

    if existing:
        try:
            await g.bot.delete_message(chat_id, existing[0])
        except Exception:
            pass

    path = get_location_image_path(loc_code)
    if not path:
        _last_banner.pop(uid, None)
        return None

    await uploading_photo(chat_id)

    try:
        sent = await g.bot.send_photo(
            chat_id,
            photo=FSInputFile(path),
            caption=caption[:CAPTION_LIMIT],
            parse_mode=ParseMode.HTML,
        )
        _last_banner[uid] = (sent.message_id, loc_code)
        return sent.message_id
    except Exception as e:
        logging.warning(f"[BANNER] {loc_code}: {e}")
        _last_banner.pop(uid, None)
        return None


def forget_banner(uid):
    _last_banner.pop(uid, None)


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


# ================= КАРТИНКИ =================
async def send_location_photo(chat_id, loc_code, caption, kb=None):
    """Фото локации из локального файла. Fallback — текст."""
    from core.location_art import get_location_image_path

    path = get_location_image_path(loc_code)
    if path:
        try:
            await g.bot.send_photo(
                chat_id,
                photo=FSInputFile(path),
                caption=caption[:CAPTION_LIMIT],
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logging.warning(f"[LOC PHOTO] {loc_code} ({path}): {e}")

    try:
        await g.bot.send_message(
            chat_id, caption, reply_markup=kb, parse_mode=ParseMode.HTML
        )
        return False
    except Exception as e:
        logging.error(f"[LOC PHOTO FALLBACK] {loc_code}: {e}")
        return False


async def send_boss_photo(chat_id, boss_code, caption, kb=None):
    """Фото босса по коду."""
    from core.location_art import get_boss_image_path

    path = get_boss_image_path(boss_code)
    if path:
        try:
            await g.bot.send_photo(
                chat_id,
                photo=FSInputFile(path),
                caption=caption[:CAPTION_LIMIT],
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logging.warning(f"[BOSS PHOTO] {boss_code} ({path}): {e}")

    try:
        await g.bot.send_message(
            chat_id, caption, reply_markup=kb, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"[BOSS PHOTO FALLBACK] {boss_code}: {e}")
    return False


async def send_boss_photo_by_name(chat_id, boss_name, caption, kb=None):
    """Фото босса по имени. Возвращает True если фото ушло."""
    from core.location_art import get_boss_image_path_by_name

    path = get_boss_image_path_by_name(boss_name)

    if not path:
        logging.warning(f"[BOSS PHOTO] Нет картинки для '{boss_name}'")
        return False

    logging.warning(f"[BOSS PHOTO] Отправляю '{boss_name}' → {path}")

    try:
        await g.bot.send_photo(
            chat_id,
            photo=FSInputFile(path),
            caption=caption[:CAPTION_LIMIT],
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        logging.warning(f"[BOSS PHOTO] УСПЕХ '{boss_name}'")
        return True
    except Exception as e:
        logging.warning(f"[BOSS PHOTO] ОШИБКА '{boss_name}': {type(e).__name__}: {e}")

    try:
        await g.bot.send_photo(chat_id, photo=FSInputFile(path))
        await g.bot.send_message(
            chat_id, caption, reply_markup=kb, parse_mode=ParseMode.HTML
        )
        return True
    except Exception as e2:
        logging.warning(f"[BOSS PHOTO] Fallback тоже упал: {e2}")
        return False


# ================= РАСЫ И КЛАССЫ =================
async def send_race_photo_by_name(chat_id, race_name, caption, kb=None):
    """Фото расы по имени."""
    from core.race_class_art import get_race_image_path_by_name

    path = get_race_image_path_by_name(race_name)
    if not path:
        logging.warning(f"[RACE PHOTO] Нет картинки для '{race_name}'")
        return False

    logging.warning(f"[RACE PHOTO] Отправляю '{race_name}' → {path}")
    try:
        await g.bot.send_photo(
            chat_id,
            photo=FSInputFile(path),
            caption=caption[:CAPTION_LIMIT],
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logging.warning(f"[RACE PHOTO] ОШИБКА '{race_name}': {e}")
        return False


async def send_class_photo_by_name(chat_id, class_name, caption, kb=None):
    """Фото класса по имени."""
    from core.race_class_art import get_class_image_path_by_name

    path = get_class_image_path_by_name(class_name)
    if not path:
        logging.warning(f"[CLASS PHOTO] Нет картинки для '{class_name}'")
        return False

    logging.warning(f"[CLASS PHOTO] Отправляю '{class_name}' → {path}")
    try:
        await g.bot.send_photo(
            chat_id,
            photo=FSInputFile(path),
            caption=caption[:CAPTION_LIMIT],
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logging.warning(f"[CLASS PHOTO] ОШИБКА '{class_name}': {e}")
        return False


# ================= ПРОГРЕСС-БАР И АНИМАЦИЯ XP =================
def visual_bar(current, total, length=15, filled="█", empty="░"):
    """Текстовый прогресс-бар."""
    if total <= 0:
        return empty * length
    pct = min(1.0, max(0.0, current / total))
    n = int(pct * length)
    return filled * n + empty * (length - n)


async def animate_xp_gain(chat_id, message_id, user_name, xp_before, xp_after,
                          next_xp, length=15):
    """Анимация заполнения XP-бара при повышении уровня."""
    steps = 5
    for i in range(steps + 1):
        pct = i / steps
        cur = int(xp_before + (xp_after - xp_before) * pct)
        bar = visual_bar(cur, next_xp, length=length)
        text = (
            f"⭐ <b>Повышение уровня!</b>\n\n"
            f"<b>{user_name}</b>\n"
            f"⭐ [{bar}] {cur}/{next_xp} XP"
        )
        try:
            await g.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        if i < steps:
            await asyncio.sleep(0.25)
