"""Кинематографичный пролог: 3 сцены через GigaChat + fallback.

Показывается один раз после создания героя.
Флаг — в таблице tutorial_progress (finished=1).
"""
import asyncio
import logging
import random

from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from core import globals as g
from core.game_data import RACES, CLASSES, FACTIONS


# Сцены: (код локации, подпись снизу)
SCENE_LOCATIONS = [
    ("village", "🏘 Начальная деревня, рассвет"),
    ("road",    "🛤 Старый тракт"),
    ("forest",  "🌲 Тёмный лес"),
]


# ============ FALLBACK ТЕКСТЫ ============
FALLBACKS = [
    [
        "Ты открываешь глаза на жёсткой соломенной постели. За окном брезжит рассвет, "
        "где-то кричит петух, скрипит телега. Ты — {char_name}, {race_name}, "
        "{class_name} из фракции «{faction_name}». Сегодня — твой первый день в этом мире.",

        "Ты сжимаешь рукоять {weapon_hint}. Старейшина говорил: «Там, за лесом, тьма. "
        "Но ты ещё не готов». Ты чувствуешь холодок в груди — не от страха, от "
        "предвкушения. Ты шёл к этому всю жизнь.",

        "Первый шаг — самый трудный. Ты выходишь за ворота. Ветер несёт запах дыма и "
        "чего-то древнего. Где-то там — боссы, подземелья, слава. А может, и смерть. "
        "Но ты не оборачиваешься.",
    ],
    [
        "Ты просыпаешься от далёкого воя. Деревня спит, но ты — нет. "
        "В голове — голос наставника: «{char_name}, ты {race_name}. Помни, кто ты». "
        "Ты встаёшь, разминая плечи.",

        "За окном — туман. Ты собираешь нехитрые пожитки. {weapon_hint} привычно "
        "ложится в руку. Фракция «{faction_name}» возлагает на тебя надежды — "
        "или просто использует. Это ты узнаешь позже.",

        "На опушке ты замираешь. Тени между деревьями двигаются слишком ритмично. "
        "Ты делаешь шаг вперёд. Обратной дороги всё равно нет.",
    ],
]


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


def _clean_name(name):
    """Убирает эмодзи и лишние пробелы из имени расы."""
    if not name:
        return "герой"
    parts = name.strip().split(maxsplit=1)
    if len(parts) == 2 and not parts[0][0].isalnum():
        return parts[1]
    return name.strip()


def _build_system_prompt():
    return (
        "Ты — мастер настольной RPG в стиле тёмного фэнтези. "
        "Пишешь атмосферные прологи для игроков. "
        "Твой стиль: мрачный, поэтичный, от второго лица («ты»). "
        "Без пафоса, без штампов, без объяснений правил. "
        "Только художественный текст."
    )


def _build_user_prompt(user):
    race = RACES.get(user.get("race", ""), {})
    cl = CLASSES.get(user.get("class", ""), {})
    fac = FACTIONS.get(user.get("faction", ""), {})

    race_name = _clean_name(race.get("name", "герой"))
    class_name = cl.get("name", "воин")
    faction_name = fac.get("name", "странник")
    char_name = user.get("char_name", "Безымянный")

    return (
        f"Герой: {char_name}, {race_name}, класс {class_name}, "
        f"фракция «{faction_name}».\n\n"
        "Напиши пролог РОВНО из 3 абзацев. Каждый абзац — 2-3 предложения. "
        "От второго лица («ты»).\n\n"
        "Абзац 1: герой просыпается в Начальной деревне на рассвете, чувствует "
        "себя новичком, вспоминает кто он.\n"
        "Абзац 2: герой собирается, берёт оружие, вспоминает напутствие наставника.\n"
        "Абзац 3: герой выходит за ворота, чувствует близость тьмы, делает первый шаг.\n\n"
        "ТРЕБОВАНИЯ:\n"
        "- Разделяй абзацы пустой строкой.\n"
        "- Без markdown, без кавычек, без заголовков.\n"
        "- Не упоминай HP, MP, уровни, предметы.\n"
        "- Не заканчивай вопросами.\n"
        "- Только 3 абзаца, каждый до 400 символов."
    )


async def _call_gigachat(user):
    """Прямой вызов GigaChat через клиент из ai.py."""
    try:
        import ai
    except Exception as e:
        logging.warning(f"[PROLOGUE] не смог импортировать ai: {e}")
        return None

    loop = asyncio.get_event_loop()

    def _sync():
        client = ai._get_client()
        resp = client.chat({
            "messages": [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user",   "content": _build_user_prompt(user)},
            ],
            "temperature": 0.9,
            "max_tokens": 700,
        })
        return resp.choices[0].message.content

    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _sync),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logging.warning("[PROLOGUE] GigaChat timeout")
        return None
    except Exception as e:
        logging.warning(f"[PROLOGUE] GigaChat error: {type(e).__name__}: {e}")
        return None

    if not text:
        return None

    # Проверка на отказ
    low = text.lower()
    for marker in ("не обладаю собственным мнением",
                   "не могу", "не буду", "как языковая модель"):
        if marker in low:
            logging.warning("[PROLOGUE] отказ GigaChat")
            return None

    # Чистка
    text = text.replace("**", "").replace("*", "").replace("#", "").strip()

    # Разбиваем на абзацы
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(parts) < 3:
        parts = [p.strip() for p in text.split("\n") if len(p.strip()) > 40]

    if len(parts) < 3:
        return None

    parts = [p[:400] for p in parts[:3]]
    return parts


def _fallback(user):
    race = RACES.get(user.get("race", ""), {})
    cl = CLASSES.get(user.get("class", ""), {})
    fac = FACTIONS.get(user.get("faction", ""), {})

    ctx = {
        "char_name":    user.get("char_name", "Безымянный"),
        "race_name":    _clean_name(race.get("name", "герой")),
        "class_name":   cl.get("name", "воин"),
        "faction_name": fac.get("name", "странник"),
        "weapon_hint":  WEAPON_HINTS.get(user.get("class", ""), "оружия"),
    }
    variant = random.choice(FALLBACKS)
    return [p.format(**ctx) for p in variant]


async def _send_scene(chat_id, loc_code, caption, num, total):
    from core.location_art import get_location_image_path

    path = get_location_image_path(loc_code)
    header = f"🎬 <b>Пролог</b> · {num}/{total}\n\n"
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

    try:
        await g.bot.send_message(chat_id, full, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"[PROLOGUE TEXT] {e}")


async def maybe_show_prologue(chat_id, user):
    """Показывает пролог, если ещё не показан. Возвращает True если показал."""
    uid = user["user_id"]

    # Уже показывали?
    try:
        step, finished = await g.db.get_tutorial_step(uid)
    except Exception as e:
        logging.warning(f"[PROLOGUE] get_tutorial_step: {e}")
        return False

    if finished:
        return False

    # Ставим флаг СРАЗУ — защита от двойного вызова
    try:
        await g.db.set_tutorial_step(uid, 1, finished=True)
    except Exception as e:
        logging.warning(f"[PROLOGUE] set_tutorial_step: {e}")

    logging.warning(f"[PROLOGUE] Показываю пролог для {uid} ({user.get('char_name')})")

    # Текст
    parts = await _call_gigachat(user)
    source = "GigaChat"
    if not parts:
        parts = _fallback(user)
        source = "fallback"
    logging.warning(f"[PROLOGUE] Источник: {source}")

    # Сцены
    total = len(SCENE_LOCATIONS)
    for i, (loc_code, scene_label) in enumerate(SCENE_LOCATIONS):
        text = parts[i] if i < len(parts) else "..."
        caption = f"{scene_label}\n\n<i>{text}</i>"
        await _send_scene(chat_id, loc_code, caption, i + 1, total)
        if i < total - 1:
            await asyncio.sleep(2)

    # Финал
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
