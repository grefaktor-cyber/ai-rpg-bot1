from gigachat import GigaChat
import asyncio
import logging
import re
import world as W

SYSTEM_PROMPT = """Ты — мастер интерактивной RPG в стиле тёмного фэнтези (Lineage 2).
Ведёшь игрока по ФИКСИРОВАННОМУ миру. Локации мира уже определены — их нельзя менять или придумывать.

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
- Пиши ярко, коротко: 3-6 предложений.
- Учитывай расу, класс, фракцию, экипировку и питомца игрока.
- Помни всё, что игрок делал раньше.

ГЛАВНОЕ ПРАВИЛО ПРО ЛОКАЦИИ:
- Игрок находится в конкретной локации. В контексте указано её название, описание, соседи.
- Ты описываешь ТОЛЬКО текущую локацию. НЕ придумывай новые места.
- Если игрок хочет перейти в другую локацию — он использует кнопку «🚶 Идти» (интерфейс).
- Если игрок пишет «иду в X» и X — соседняя локация, система сама перенесёт игрока (тег не нужен).
- Если игрок пишет «иду в X» и X — НЕ соседняя локация, ответь: «Отсюда туда не попасть. Отсюда есть путь только в: [список соседей]».
- НЕ ставь [LOCATION:] сам — за переходы отвечает система.

БОЕВАЯ СИСТЕМА:
- Если игрок ВСТУПАЕТ В БОЙ с врагом или NPC враждебен — добавь в конце:
  [ENEMY: имя врага | LEVEL: N | HP: M]
- N близко к уровню игрока (±1-2). M = N × 20.
- Для БОССА флаг BOSS:
  [ENEMY: имя босса | LEVEL: N | HP: M | BOSS]
- Когда ставишь [ENEMY] — НЕ ставь другие теги.

ТЕГИ (только когда НЕ идёт бой):
- [ITEM: название] — игрок получил предмет.
- [DAMAGE: число] — игрок получил урон.
- [HEAL: число] — игрок восстановил HP.
- [GOLD: число] — игрок нашёл золото.
- [MATERIAL: iron/leather/dust/crystal] — игрок нашёл материал (редко, 20%).
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон", "суицид", "самоубийств",
    "убить себя", "покончить с собой", "теракт", "взорвать", "бомба",
    "взрывчатк", "оружие массового", "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

PET_NAMES = {"wolf": "Волк", "owl": "Сова", "dragon": "Дракончик", "phoenix": "Феникс"}

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


def _build_char_context(user, event=None, location_owner=None):
    if not user.get("race"):
        return ""
    loc_code = user.get("location_code", "village")
    loc = W.get_location(loc_code) or {}
    neighbors = W.get_neighbors(loc_code)
    npcs_here = W.get_npcs_in_location(loc_code)

    lines = [
        "\n\nПЕРСОНАЖ ИГРОКА:",
        f"Имя: {user.get('char_name', 'Безымянный')}",
        f"Раса: {user.get('race', '?')}",
        f"Класс: {user.get('class', '?')}",
    ]
    if user.get("faction") == "light":
        lines.append("Фракция: Орден Света")
    elif user.get("faction") == "dark":
        lines.append("Фракция: Тёмное Братство")

    lines += [
        f"Уровень: {user.get('level', 1)}",
        f"HP: {user.get('hp', 100)}/{user.get('max_hp', 100)}",
        f"STR:{user.get('stat_str', 5)} DEX:{user.get('stat_dex', 5)} CON:{user.get('stat_con', 5)} "
        f"INT:{user.get('stat_int', 5)} WIT:{user.get('stat_wit', 5)} MEN:{user.get('stat_men', 5)}",
        f"Золото: {user.get('gold', 0)}",
        f"Экипировка: оружие={user.get('equipped_weapon') or 'нет'}, "
        f"броня={user.get('equipped_armor') or 'нет'}, "
        f"аксессуар={user.get('equipped_accessory') or 'нет'}",
    ]
    if user.get("pet_name"):
        pn = PET_NAMES.get(user.get("pet_type"), "Питомец")
        lines.append(f"Питомец: {user.get('pet_name')} ({pn}, ур. {user.get('pet_level', 1)})")

    # === ЛОКАЦИЯ ===
    lines.append("\n\nТЕКУЩАЯ ЛОКАЦИЯ:")
    lines.append(f"Код: {loc_code}")
    lines.append(f"Название: {loc.get('name', '?')}")
    lines.append(f"Описание: {loc.get('desc', '')}")
    lines.append(f"Тип: {loc.get('type', 'wild')}")
    lines.append(f"Уровень входа: {loc.get('level_req', 1)}+")
    if neighbors:
        lines.append(f"Соседние локации (отсюда можно пойти только туда):")
        for code, info in neighbors:
            lines.append(f"  • {info['name']} (код {code}, ур.{info['level_req']}+)")
    else:
        lines.append("Соседних локаций нет (тупик).")
    if npcs_here:
        lines.append("NPC в этой локации:")
        for code, info in npcs_here:
            lines.append(f"  • {info['name']}")
    if loc.get("enemies"):
        lines.append(f"Обычные враги здесь: {', '.join(loc['enemies'])}")
    if loc.get("boss"):
        lines.append(f"БОСС локации: {loc['boss']['name']} (ур. {loc['boss']['level']})")

    if location_owner:
        lines.append(f"\nВладелец локации: гильдия «{location_owner.get('guild_name', '?')}»")

    if event:
        lines.append(f"\n⚠️ АКТИВНОЕ СОБЫТИЕ: {event.get('event_name')} — {event.get('event_desc')}")

    return "\n".join(lines)


def _strip_all_tags(text):
    return re.sub(
        r"\[[^\[\]]*?(?:ENEMY|ITEM|LOCATION|BOSS|DAMAGE|HEAL|GOLD|MATERIAL)[^\[\]]*?\]",
        "", text, flags=re.IGNORECASE | re.DOTALL
    ).strip()


def _extract_enemy(text):
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
    pattern = rf"\[[^\[\]]*?{tag}:?\s*([^\]\n]+?)\s*\]"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None, text
    value = m.group(1).strip()
    text = text[:m.start()] + text[m.end():]
    return value, text.strip()


def _extract_int(text, tag):
    pattern = rf"\[[^\[\]]*?{tag}:?\s*(\d+)\s*\]"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return 0, text
    value = int(m.group(1))
    text = text[:m.start()] + text[m.end():]
    return value, text.strip()


async def generate(story, user_action, arc=1, user=None, event=None, location_owner=None):
    if _is_blocked(user_action):
        return {"text": "🚫 Этот запрос нарушает правила игры.",
                "item": None, "location": None, "enemy": None,
                "material": None, "damage": 0, "heal": 0, "gold": 0}

    arc_note = ""
    if arc % 20 == 0 and user:
        arc_note = (f"\n\nВАЖНО: Ключевой момент! Введи БОССА — сильного врага. "
                    f"Уровень босса = {user.get('level', 1) + 2}, HP = уровень × 30. "
                    f"В конце ответа добавь ТОЧНО такой тег: "
                    f"[ENEMY: имя босса | LEVEL: N | HP: M | BOSS]")

    char_ctx = _build_char_context(user, event, location_owner) if user else ""
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
                "material": None, "damage": 0, "heal": 0, "gold": 0}
    except Exception as e:
        logging.error(f"GigaChat error: {e}")
        return {"text": "⚠️ Ошибка нейросети. Попробуй позже.",
                "item": None, "location": None, "enemy": None,
                "material": None, "damage": 0, "heal": 0, "gold": 0}

    result = {"text": text, "item": None, "location": None, "enemy": None,
              "material": None, "damage": 0, "heal": 0, "gold": 0}

    enemy, text = _extract_enemy(text)
    if enemy:
        result["enemy"] = enemy
    else:
        for tag, key in [("ITEM", "item"), ("LOCATION", "location")]:
            val, text = _extract_simple(text, tag)
            if val:
                result[key] = val
        mat, text = _extract_simple(text, "MATERIAL")
        if mat:
            mat = mat.lower().strip()
            if mat in ("iron", "leather", "dust", "crystal"):
                result["material"] = mat
        for tag, key in [("DAMAGE", "damage"), ("HEAL", "heal"), ("GOLD", "gold")]:
            val, text = _extract_int(text, tag)
            if val:
                result[key] = val

    text = _strip_all_tags(text)
    result["text"] = text.strip()

    if _is_blocked(result["text"]):
        return {"text": "🚫 Сюжет ушёл в недопустимую тему.",
                "item": None, "location": None, "enemy": None,
                "material": None, "damage": 0, "heal": 0, "gold": 0}

    return result
