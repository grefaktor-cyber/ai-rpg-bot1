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
- Заканчивай ответ ОТКРЫТЫМ вопросом: «Что будешь делать?», «Твой ход.»
- Игрок может написать ЛЮБОЕ действие. Свобода — суть игры.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Учитывай расу, класс и экипировку игрока.
- Помни всё, что игрок делал раньше.
- Описывай последствия честно.

БОЕВАЯ СИСТЕМА (ВАЖНО):
- Если игрок ВСТУПАЕТ В БОЙ или встречает враждебное существо — добавь в конец ответа тег:
  [ENEMY: имя врага | LEVEL: число | HP: число]
- Уровень врага делай близким к уровню игрока (±1-2), HP = уровень × 20.
- Для БОССА (важный сюжетный враг) — добавь флаг BOSS:
  [ENEMY: имя босса | LEVEL: число | HP: число | BOSS]
  Босс должен быть на 2-3 уровня выше игрока, HP = уровень × 30.
- КОГДА ставишь тег [ENEMY: ...] — НЕ ставь [DAMAGE:] или [HEAL:] — бой рассчитается системой.
- Не ставь [ENEMY:] на каждое действие. Только когда действительно начинается бой.
- Вступление в бой описывай красочно: как выглядит враг, что он делает, как настроен.

ТЕГИ (добавляй только когда НЕ идёт бой):
- [ITEM: название] — игрок нашёл/получил предмет.
- [LOCATION: название] — игрок перешёл в новую локацию.
- [DAMAGE: число] — игрок получил урон (вне боя).
- [HEAL: число] — игрок восстановил HP (вне боя).
- [GOLD: число] — игрок нашёл золото.
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
        f"Локация: {user.get('location', '?')}\n"
    )


async def generate(story, user_action, arc=1, user=None):
    if _is_blocked(user_action):
        return {"text": "🚫 Этот запрос нарушает правила игры.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}

    arc_note = ""
    if arc % 20 == 0 and user:
        arc_note = (f"\n\nВАЖНО: Ключевой момент! Введи БОССА — сильного врага, "
                    f"подходящего сюжету (дракон, демон, древний лич). "
                    f"Уровень босса = {user.get('level', 1) + 2}, HP = уровень × 30. "
                    f"Обязательно добавь тег [ENEMY: имя | LEVEL: N | HP: M | BOSS]. "
                    f"Не предлагай вариантов выбора.")

    char_ctx = _build_char_context(user) if user else ""
    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}{char_ctx}\n\nИГРОК: {user_action}\n\nМАСТЕР:{arc_note}"

    def _sync_call():
        client = _get_client()
        response = client.chat({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            "temperature": 0.75, "max_tokens": 500,
        })
        return response.choices[0].message.content

    loop = asyncio.get_event_loop()
    try:
        text = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=30.0)
    except asyncio.TimeoutError:
        return {"text": "⏳ Нейросеть не ответила. Попробуй ещё раз.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}
    except Exception as e:
        logging.error(f"GigaChat error: {e}")
        return {"text": "⚠️ Ошибка нейросети. Попробуй позже.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}

    result = {"text": text, "item": None, "location": None, "enemy": None,
              "damage": 0, "heal": 0, "gold": 0}

    # ENEMY-тег: имя | LEVEL: N | HP: M | (BOSS)
    m = re.search(r"\[ENEMY:\s*(.+?)\s*\|\s*LEVEL:\s*(\d+)\s*\|\s*HP:\s*(\d+)(\s*\|\s*BOSS)?\]",
                  result["text"], re.IGNORECASE)
    if m:
        result["enemy"] = {
            "name": m.group(1).strip(),
            "level": max(1, min(50, int(m.group(2)))),
            "hp": max(20, min(500, int(m.group(3)))),
            "is_boss": bool(m.group(4)),
        }
        result["text"] = re.sub(
            r"\[ENEMY:\s*.+?\s*\|\s*LEVEL:\s*\d+\s*\|\s*HP:\s*\d+(\s*\|\s*BOSS)?\]",
            "", result["text"], flags=re.IGNORECASE
        ).strip()
    else:
        # Только если боя нет — парсим остальные теги
        for tag, key, cast in [
            (r"\[ITEM:\s*(.+?)\]", "item", str),
            (r"\[LOCATION:\s*(.+?)\]", "location", str),
        ]:
            mm = re.search(tag, result["text"])
            if mm:
                result[key] = cast(mm.group(1).strip())
                result["text"] = re.sub(tag, "", result["text"]).strip()

        for tag, key in [
            (r"\[DAMAGE:\s*(\d+)\]", "damage"),
            (r"\[HEAL:\s*(\d+)\]", "heal"),
            (r"\[GOLD:\s*(\d+)\]", "gold"),
        ]:
            mm = re.search(tag, result["text"])
            if mm:
                result[key] = int(mm.group(1))
                result["text"] = re.sub(tag, "", result["text"]).strip()

    if _is_blocked(result["text"]):
        return {"text": "🚫 Сюжет ушёл в недопустимую тему.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}

    result["text"] = result["text"].strip()
    return result
