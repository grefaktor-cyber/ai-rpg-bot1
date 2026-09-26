from gigachat import GigaChat
import asyncio
import logging
import re

SYSTEM_PROMPT = """Ты — мастер интерактивной RPG в стиле тёмного фэнтези (Lineage 2).
Ведёшь игрока по вымышленному миру. У игрока есть раса, класс, характеристики и экипировка.

СТРОГИЕ ЗАПРЕТЫ:
- Не упоминай реальных политиков, партии, действующих государственных деятелей.
- Не описывай реальные политические события, выборы, протесты, военные конфликты.
- Не пропагандируй наркотики, суицид, насилие, экстремизм, терроризм.
- Не генерируй инструкции по изготовлению оружия, взрывчатки, наркотиков.
- Не разжигай ненависть по признаку пола, расы, религии, национальности.
- Если игрок просит запрещённое — вежливо откажись и переведи сюжет в безопасное русло.

ПРАВИЛА ОТВЕТА (ОЧЕНЬ ВАЖНО):
- НИКОГДА не предлагай варианты выбора списком («1. Да», «2. Нет», «А или Б»).
- НИКОГДА не пиши «Что ты сделаешь? 1)... 2)...».
- НИКОГДА не ограничивай игрока двумя-тремя вариантами.
- Заканчивай ответ ОТКРЫТЫМ вопросом: «Что будешь делать?», «Куда направишься?», «Твой ход.»
- Игрок может написать ЛЮБОЕ действие — атаковать, убежать, поговорить, обыскать,
  спрятаться, помолиться, украсть, обмануть, подружиться. Свобода — суть игры.
- Не подсказывай «правильный» путь и не веди игрока за руку.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Учитывай расу, класс и экипировку игрока в описаниях и реакциях NPC.
- Экипировка даёт бонусы: хорошее оружие усиливает атаку, броня защищает, аксессуары дают особые эффекты. Обыгрывай это в сюжете.
- Помни всё, что игрок делал раньше.
- Описывай последствия поступков честно: глупость — плохой исход, хитрость — хороший.

ТЕГИ (добавляй в конец ответа, если применимо):
- [ITEM: название] — если игрок нашёл/получил предмет.
- [LOCATION: название] — если игрок перешёл в новую локацию.
- [BOSS: название] — если игрок победил босса.
- [DAMAGE: число] — если игрок получил урон (например, [DAMAGE: 15]).
- [HEAL: число] — если игрок восстановил HP (например, [HEAL: 20]).
- [GOLD: число] — если игрок нашёл золото (например, [GOLD: 25]).
Не добавляй теги, если событие не произошло.
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон", "суицид", "самоубийств",
    "убить себя", "покончить с собой", "теракт", "взорвать", "бомба",
    "взрывчатк", "оружие массового", "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

_client = None


def _get_client():
    global _client
    if _client is None:
        from config import GIGACHAT_CREDENTIALS
        _client = GigaChat(credentials=GIGACHAT_CREDENTIALS,
                           verify_ssl_certs=False, model="GigaChat-2")
    return _client


def _is_blocked(text):
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)


def _build_char_context(user):
    if not user.get("race"):
        return ""
    return (
        f"\n\nПЕРСОНАЖ ИГРОКА:\n"
        f"Имя: {user.get('char_name', 'Безымянный')}\n"
        f"Раса: {user.get('race', '?')}\n"
        f"Класс: {user.get('class', '?')}\n"
        f"Уровень: {user.get('level', 1)}\n"
        f"HP: {user.get('hp', 100)}/{user.get('max_hp', 100)}\n"
        f"STR:{user.get('stat_str', 5)} DEX:{user.get('stat_dex', 5)} CON:{user.get('stat_con', 5)} "
        f"INT:{user.get('stat_int', 5)} WIT:{user.get('stat_wit', 5)} MEN:{user.get('stat_men', 5)}\n"
        f"Золото: {user.get('gold', 0)}\n"
        f"Экипировка: оружие={user.get('equipped_weapon') or 'нет'}, "
        f"броня={user.get('equipped_armor') or 'нет'}, "
        f"аксессуар={user.get('equipped_accessory') or 'нет'}\n"
        f"Текущая локация: {user.get('location', '?')}\n"
    )


async def generate(story, user_action, arc=1, user=None):
    if _is_blocked(user_action):
        return {"text": "🚫 Этот запрос нарушает правила игры. Попробуй другое действие — например, «осматриваюсь».",
                "item": None, "location": None, "boss": None,
                "damage": 0, "heal": 0, "gold": 0}

    arc_note = ""
    if arc % 20 == 0:
        arc_note = ("\n\nВАЖНО: Это ключевой момент сюжета! Введи босса — опиши встречу с сильным врагом "
                    "(дракон, демон, древний лич, военачальник). Игрок должен сразиться. "
                    "Заверши ответ тегом [BOSS: имя]. Не предлагай вариантов выбора — пусть игрок сам решает, как действовать.")

    char_ctx = _build_char_context(user) if user else ""
    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}{char_ctx}\n\nИГРОК: {user_action}\n\nМАСТЕР:{arc_note}"

    def _sync_call():
        client = _get_client()
        response = client.chat({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            "temperature": 0.7, "max_tokens": 500,
        })
        return response.choices[0].message.content

    loop = asyncio.get_event_loop()
    try:
        text = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=30.0)
    except asyncio.TimeoutError:
        return {"text": "⏳ Нейросеть не ответила. Попробуй ещё раз.", "item": None,
                "location": None, "boss": None, "damage": 0, "heal": 0, "gold": 0}
    except Exception as e:
        logging.error(f"GigaChat error: {e}")
        return {"text": "⚠️ Ошибка нейросети. Попробуй позже.", "item": None,
                "location": None, "boss": None, "damage": 0, "heal": 0, "gold": 0}

    result = {"text": text, "item": None, "location": None, "boss": None,
              "damage": 0, "heal": 0, "gold": 0}

    m = re.search(r"\[ITEM:\s*(.+?)\]", result["text"])
    if m:
        result["item"] = m.group(1).strip()
        result["text"] = re.sub(r"\[ITEM:\s*.+?\]", "", result["text"]).strip()

    m = re.search(r"\[LOCATION:\s*(.+?)\]", result["text"])
    if m:
        result["location"] = m.group(1).strip()
        result["text"] = re.sub(r"\[LOCATION:\s*.+?\]", "", result["text"]).strip()

    m = re.search(r"\[BOSS:\s*(.+?)\]", result["text"])
    if m:
        result["boss"] = m.group(1).strip()
        result["text"] = re.sub(r"\[BOSS:\s*.+?\]", "", result["text"]).strip()

    m = re.search(r"\[DAMAGE:\s*(\d+)\]", result["text"])
    if m:
        result["damage"] = int(m.group(1))
        result["text"] = re.sub(r"\[DAMAGE:\s*\d+\]", "", result["text"]).strip()

    m = re.search(r"\[HEAL:\s*(\d+)\]", result["text"])
    if m:
        result["heal"] = int(m.group(1))
        result["text"] = re.sub(r"\[HEAL:\s*\d+\]", "", result["text"]).strip()

    m = re.search(r"\[GOLD:\s*(\d+)\]", result["text"])
    if m:
        result["gold"] = int(m.group(1))
        result["text"] = re.sub(r"\[GOLD:\s*\d+\]", "", result["text"]).strip()

    if _is_blocked(result["text"]):
        return {"text": "🚫 Сюжет ушёл в недопустимую тему. Опиши другое действие.",
                "item": None, "location": None, "boss": None,
                "damage": 0, "heal": 0, "gold": 0}

    return result
