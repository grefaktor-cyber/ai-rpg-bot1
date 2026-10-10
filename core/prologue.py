"""Кинематографичный пролог: 3 сцены через GigaChat + fallback.

Показывается один раз после создания героя.
Кэш — через achievement 'tutorial_done' (переиспользуем существующую таблицу).
"""
import asyncio
import logging
import random

from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS


PROLOGUE_FLAG = "tutorial_done"  # используем существующий achievement

# Сцены: (код локации, подпись снизу)
SCENE_LOCATIONS = [
    ("village", "🏘 Начальная деревня"),
    ("road",    "🛤 Старый тракт"),
    ("forest",  "🌲 Тёмный лес"),
]


FALLBACK_TEXTS = {
    "start": [
        "Ты открываешь глаза на жёсткой соломенной постели. За окном брезжит рассвет, "
        "петухи кричат, где-то скрипит телега. Ты — {char_name}, {race_name} из "
        "фракции «{faction_name}». Сегодня — твой первый день в этом мире.",

        "Ты сжимаешь рукоять {weapon_hint}. Старейшина говорил: «Там, за лесом, тьма. "
        "Но ты ещё не готов». Ты чувствуешь холодок в груди — не от страха, от "
        "предвкушения. Ты шёл к этому всю жизнь.",

        "Первый шаг — самый трудный. Ты выходишь за ворота. Ветер несёт запах дыма и "
        "чего-то древнего. Где-то там — боссы, подземелья, слава. А может, и смерть. "
        "Но ты не оборачиваешься.",
    ],
    "alt": [
        "Ты просыпаешься от далёкого воя. Деревня спит, но ты — нет. "
        "В голове — голос наставника: «{char_name}, ты {race_name}-{class_name}. "
        "Помни, кто ты». Ты встаёшь.",

        "За окном — туман. Ты собираешь нехитрые пожитки. {weapon_hint} привычно "
        "ложится в руку. Фракция «{faction_name}» возлагает на тебя надежды — "
        "или просто использует. Это ты узнаешь позже.",

        "На опушке ты замираешь. Тени между деревьями двигаются слишком ритмично. "
        "Ты делаешь шаг вперёд. Обратной дороги всё равно нет.",
    ],
}


WEAPON_HINTS = {
    "warrior":   "меча",
    "knight":    "меча и щита",
    "mage":      "посоха",
    "archer":    "лука",
    "guardian":  "копья-листа",
    "bard":      "лютни",
    "assassin":  "двух клинков",
    "necro":     "костяного посоха",
    "dancer":    "изогнутых клинков",
    "destroyer": "огромного топора",
    "tyrant":    "двух секир",
    "overlord":  "тяжёлого молота",
    "keeper":    "щита света",
}


def _build_ai_prompt(user):
    race = RACES.get(user.get("race", ""), {})
    cl = CLASSES.get(user.get("class", ""), {})
    fac = FACTIONS.get(user.get("faction", ""), {})

    race_name = race.get("name", "герой")
    class_name = cl.get("name", "воин")
    faction_name = fac.get("name", "странник")
    char_name = user.get("char_name", "Безымянный")

    return (
        "Ты — рассказчик в мрачном фэнтези-RPG.\n\n"
        f"Герой: {char_name}, {race_name}, класс {class_name}, "
        f"фракция «{faction_name}».\n\n"
        "Напиши короткий пролог из РОВНО 3 абзацев. Каждый абзац — "
        "2-3 предложения, атмосферно, мрачно, от второго лица («ты»).\n\n"
        "Абзац 1: герой просыпается в Начальной деревне на рассвете, "
        "чувствует себя новичком.\n"
        "Абзац 2: герой собирается, берёт оружие, вспоминает напутствие.\n"
        "Абзац 3: герой выходит за ворота, чувствует близость тьмы, "
        "делает первый шаг.\n\n"
        "Формат ответа — только 3 абзаца, разделённые пустой строкой. "
        "Без markdown, без заголовков, без кавычек. Только чистый текст."
    )


async def _generate_with_ai(user):
    """Пытается сгенерить через GigaChat. Возвращает список из 3 строк или None."""
    try:
        import ai
        prompt = _build_ai_prompt(user)
        raw = await ai.generate(
            user_id=user["user_id"],
            action=prompt,
        )
        if not raw or not isinstance(raw, str):
            return None

        # Чистим от markdown
        raw = raw.replace("**", "").replace("*", "").replace("#", "").strip()

        # Разбиваем на абзацы
        parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
        if len(parts) < 3:
            # Попробуем по одиночным \n
            parts = [p.strip() for p in raw.split("\n") if len(p.strip()) > 40]
        if len(parts) < 3:
            return None

        # Обрезаем до 400 символов каждый
        parts = [p[:400] for p in parts[:3]]
        return parts
    except Exception as e:
        logging.warning(f"[PROLOGUE AI] {type(e).__name__}: {e}")
        return None


def _fallback(user):
    """Возвращает 3 строки фикс-текста."""
    variant = random.choice([FALLBACK_TEXTS["start"], FALLBACK_TEXTS["alt"]])
    race = RACES.get(user.get("race", ""), {})
    cl = CLASSES.get(user.get("class", ""), {})
    fac = FACTIONS.get(user.get("faction", ""), {})

    ctx = {
        "char_name":    user.get("char_name", "Безымянный"),
        "race_name":    race.get("name", "герой"),
        "class_name":   cl.get("name", "воин"),
        "faction_name": fac.get("name", "странник"),
        "weapon_hint":  WEAPON_HINTS.get(user.get("class", ""), "оружия"),
    }
    return [p.format(**ctx) for p in variant]


async def _send_scene(chat_id, loc_code, caption, scene_num, total):
    """Отправляет одну сцену: фото + текст."""
    from core.location_art import get_location_image_path

    path = get_location_image_path(loc_code)
    header = f"🎬 <b>Пролог</b> · {scene_num}/{total}\n\n"
    full = header + caption

    if path:
        try:
            await g.bot.send_photo(
                chat_id,
                photo=FSInputFile(path),
                caption=full[:1000],
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception as e:
            logging.warning(f"[PROLOGUE PHOTO] {loc_code}: {e}")

    # fallback — только текст
    try:
        await g.bot.send_message(chat_id, full, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"[PROLOGUE TEXT] {e}")


async def maybe_show_prologue(chat_id, user):
    """Показывает пролог, если ещё не показан. True = показал (и вызвавший должен сделать return)."""
    uid = user["user_id"]

    # Проверяем — уже было?
    try:
        has = await g.db.has_achievement(uid, PROLOGUE_FLAG)
    except Exception as e:
        logging.warning(f"[PROLOGUE] has_achievement: {e}")
        # если не смогли проверить — не показываем (защита от дубля)
        return False

    if has:
        return False

    # Ставим флаг СРАЗУ — защита от двойного показа
    try:
        await g.db.add_achievement(uid, PROLOGUE_FLAG)
    except Exception as e:
        logging.warning(f"[PROLOGUE] add_achievement: {e}")

    # Генерируем текст
    parts = await _generate_with_ai(user)
    if not parts:
        parts = _fallback(user)

    # Показываем 3 сцены
    total = len(SCENE_LOCATIONS)
    for i, (loc_code, scene_label) in enumerate(SCENE_LOCATIONS):
        text = parts[i] if i < len(parts) else "..."
        caption = f"{scene_label}\n\n<i>{text}</i>"
        await _send_scene(chat_id, loc_code, caption, i + 1, total)
        if i < total - 1:
            await asyncio.sleep(2)

    # Финальная строка
    try:
        await g.bot.send_message(
            chat_id,
            "✨ <b>Твоё приключение начинается.</b>\n\n"
            "💡 <i>Опиши действие текстом или жми кнопки ниже.</i>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    return True
