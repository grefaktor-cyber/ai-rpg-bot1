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

ПРАВИЛА ОТВЕТА:
- НИКОГДА не предлагай варианты выбора списком («1. Да», «2. Нет»).
- Заканчивай ответ ОТКРЫТЫМ вопросом: «Что будешь делать?», «Твой ход.»
- Игрок может написать ЛЮБОЕ действие. Свобода — суть игры.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Учитывай расу, класс и экипировку игрока.
- Помни всё, что игрок делал раньше.

КРИТИЧНО ПРО ТЕГИ:
- Тег пишется СТРОГО так: квадратная скобка, слово, двоеточие, значение, квадратная скобка.
- БЕЗ посторонних символов перед словом: НЕ «¡ ENEMY», НЕ «! ENEMY», а только «ENEMY».
- БЕЗ пробела перед закрывающей скобкой: НЕ «HP: 40 ]», а «HP: 40]».
- Тег ставится ОДИН РАЗ в самом конце ответа. Максимум один тег за раз.

БОЕВАЯ СИСТЕМА:
- Если игрок ВСТУПАЕТ В БОЙ — добавь в конце ответа:
  [ENEMY: имя врага | LEVEL: N | HP: M]
- N — уровень близко к уровню игрока (±1-2). M = N × 20.
- Для БОССА добавь флаг BOSS:
  [ENEMY: имя босса | LEVEL: N | HP: M | BOSS]
- Когда ставишь [ENEMY] — НЕ ставь другие теги.
- Не ставь [ENEMY] на каждое действие. Только когда бой НАЧИНАЕТСЯ.

ТЕГИ (только когда НЕ идёт бой):
- [ITEM: название] — игрок получил предмет.
- [LOCATION: название] — игрок перешёл в новую локацию.
- [DAMAGE: число] — игрок получил урон.
- [HEAL: число] — игрок восстановил HP.
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


def _strip_all_tags(text):
    """Удаляет ВСЕ теги (любой мусор перед словом, пробелы до ])."""
    return re.sub(
        r"\[[^\[\]]*?(?:ENEMY|ITEM|LOCATION|BOSS|DAMAGE|HEAL|GOLD)[^\[\]]*?\]",
        "", text, flags=re.IGNORECASE | re.DOTALL
    ).strip()


def _extract_enemy(text):
    """
    Ищет ENEMY-тег.
    Устойчиво к: [¡ ENEMY:, [! ENEMY:, [ ENEMY:, пробел перед ], переносы строк.
    """
    pattern = (
        r"\[[^\[\]]*?ENEMY:?\s*"
        r"([^|\]\n]+?)\s*\|\s*"
        r"LEVEL:?\s*(\d+)\s*\|\s*"
        r"HP:?\s*(\d+)"
        r"(?:\s*\|\s*BOSS)?"
        r"\s*\]"
    )
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None, text
    enemy = {
        "name": m.group(1).strip(),
        "level": max(1, min(50, int(m.group(2)))),
        "hp": max(20, min(500, int(m.group(3)))),
        "is_boss": "boss" in m.group(0).lower(),
    }
    text = text[:m.start()] + text[m.end():]
    return enemy, text.strip()


def _extract_simple(text, tag):
    """ITEM / LOCATION — устойчиво к мусору и пробелам."""
    pattern = rf"\[[^\[\]]*?{tag}:?\s*([^\]\n]+?)\s*\]"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None, text
    value = m.group(1).strip()
    text = text[:m.start()] + text[m.end():]
    return value, text.strip()


def _extract_int(text, tag):
    """DAMAGE / HEAL / GOLD — устойчиво к мусору."""
    pattern = rf"\[[^\[\]]*?{tag}:?\s*(\d+)\s*\]"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return 0, text
    value = int(m.group(1))
    text = text[:m.start()] + text[m.end():]
    return value, text.strip()


async def generate(story, user_action, arc=1, user=None):
    if _is_blocked(user_action):
        return {"text": "🚫 Этот запрос нарушает правила игры.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}

    arc_note = ""
    if arc % 20 == 0 and user:
        arc_note = (f"\n\nВАЖНО: Ключевой момент! Введи БОССА — сильного врага. "
                    f"Уровень босса = {user.get('level', 1) + 2}, HP = уровень × 30. "
                    f"В конце ответа добавь ТОЧНО такой тег: "
                    f"[ENEMY: имя босса | LEVEL: N | HP: M | BOSS]")

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

    # Сначала ENEMY — если бой, остальные теги игнорируем
    enemy, text = _extract_enemy(text)
    if enemy:
        result["enemy"] = enemy
    else:
        for tag, key in [("ITEM", "item"), ("LOCATION", "location")]:
            val, text = _extract_simple(text, tag)
            if val:
                result[key] = val
        for tag, key in [("DAMAGE", "damage"), ("HEAL", "heal"), ("GOLD", "gold")]:
            val, text = _extract_int(text, tag)
            if val:
                result[key] = val

    # Страховка: чистим всё, что похоже на оставшиеся теги
    text = _strip_all_tags(text)
    result["text"] = text.strip()

    if _is_blocked(result["text"]):
        return {"text": "🚫 Сюжет ушёл в недопустимую тему.",
                "item": None, "location": None, "enemy": None,
                "damage": 0, "heal": 0, "gold": 0}

    return result
