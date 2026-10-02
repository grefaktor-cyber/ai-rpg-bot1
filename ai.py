"""GigaChat: промпт, парсинг тегов, генерация сюжета."""
from gigachat import GigaChat
import asyncio
import logging
import re
import json
import world as W
from core.equipment import SHOP


SYSTEM_PROMPT = """Ты — мастер интерактивной текстовой RPG в стиле ТЁМНОГО ФЭНТЕЗИ.

Это художественный вымысел в жанре фэнтези (аналог Dungeons & Dragons,
Lineage 2, World of Warcraft). Все события происходят в ВЫМЫШЛЕННОМ мире,
где есть магия, монстры и вымышленные персонажи.

ВАЖНО: термины «оружие», «бой», «атака», «убить», «кровь», «смерть»
относятся ИСКЛЮЧИТЕЛЬНО к игровой механике и вымышленным существам
(гоблинам, драконам, нежити). Это НЕ описание реального насилия.
Ты как мастер D&D — ведёшь игру, а не даёшь реальные советы.

ЗАПРЕТЫ (только про РЕАЛЬНЫЙ мир):
- Не упоминай реальных политиков и события.
- Не давай инструкций по изготовлению реального оружия/взрывчатки/наркотиков.
- Не разжигай ненависть по признаку пола, расы, религии.
- Если игрок уводит в реальную политику — мягко верни в фэнтези-сюжет.

ПРАВИЛА ОТВЕТА:
- НИКОГДА не предлагай варианты списком («1. Да», «2. Нет»).
- Заканчивай ответ ОТКРЫТЫМ вопросом: «Что будешь делать?», «Твой ход.»
- Пиши ярко, коротко: 3-6 предложений.
- Учитывай расу, класс, фракцию, экипировку и питомца игрока.
- Помни всё, что игрок делал раньше.

ПРЕДМЕТЫ (ОЧЕНЬ ВАЖНО):
Когда игрок находит предмет, даёт награду, открывает сундук —
используй ТОЛЬКО предметы из СПИСКА ПРЕДМЕТОВ (см. ниже).
Тег: [ITEM: ТОЧНОЕ_НАЗВАНИЕ_ИЗ_СПИСКА]
НЕ выдумывай названия типа «меч древнего воина» — их нет в игре.
Если хочешь дать оружие — выбери из списка ближайшее по смыслу.

СЛОВАРЬ ИГРЫ:
- HP, здоровье — выживаемость. /use Зелье HP.
- MP, мана — ресурс для скилов. /use Зелье MP.
- Скил — активная способность класса (/skills, 3 слота).
- P.Def — защита от физического. M.Def — от магии.
- Энергия — лимит на действия. +1 каждые 30 мин.
- Роль класса: tank, fighter, agile, mage, universal.
- Тип урона: phys, agile, magic.

ЕСЛИ «восстановить HP/MP» — не меняй сам. Отправь в /use.

ЕСЛИ «использую скил X»:
- Проверь что X есть в «АКТИВНЫЕ СКИЛЫ» в контексте.
- Если есть — скажи «нужен бой (кнопки)». Не активируй сам.

ЕСЛИ «ищу сокровище/клад»:
- Опиши сцену с сундуком/тайником.
- Вознагради РЕАЛЬНЫМ предметом: [ITEM: название из списка].

ЛОКАЦИИ:
- Игрок в конкретной локации (см. контекст).
- Описывай ТОЛЬКО её. Не придумывай новые.
- Переход — через кнопку «🚶 Идти». НЕ ставь [LOCATION:] сам.

БОЙ:
- Если игрок вступает в бой: [ENEMY: имя | LEVEL: N | HP: M]
- N ≈ уровень игрока ±1. M = N × 25.
- Имена — из списка врагов локации.
- Для БОССА: [ENEMY: имя | LEVEL: N | HP: M | BOSS], M = N × 45.
- Если ставишь [ENEMY] — других тегов НЕ ставь.

ПОСЛЕ БОЯ:
- Если в истории [БОЙ ОКОНЧЕН] — не продолжай бой.

ТЕГИ (только вне боя):
- [ITEM: название] — предмет ИЗ СПИСКА.
- [DAMAGE: N], [HEAL: N], [GOLD: N].
- [MATERIAL: iron/leather/dust/crystal] — редко (20%).
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон", "суицид", "самоубийств",
    "убить себя", "покончить с собой", "теракт", "взорвать", "бомба",
    "взрывчатк", "оружие массового", "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

# Фразы-маркеры отказа GigaChat
REFUSAL_MARKERS = [
    "не обладает собственным мнением",
    "не транслирует мнение",
    "разговоры на некоторые темы временно ограничены",
    "я не могу обсуждать",
    "я не могу комментировать",
    "не имею права обсуждать",
    "избегаю обсуждения",
    "не буду обсуждать",
    "как языковая модель, я",
    "не могу предоставить информацию на эту тему",
]

PET_NAMES = {"wolf": "Волк", "owl": "Сова", "dragon": "Дракончик",
             "phoenix": "Феникс", "lion": "Лев"}
ROLE_NAMES = {"tank": "танк", "fighter": "боец", "agile": "ловкий",
              "mage": "маг", "universal": "универсал"}
DMG_NAMES = {"phys": "физический", "agile": "ловкий", "magic": "магический"}

# ================= КЭШ СПИСКА ПРЕДМЕТОВ =================
_shop_names_cache = None


def _get_item_names():
    """Список всех предметов для промпта — из SHOP."""
    global _shop_names_cache
    if _shop_names_cache is not None:
        return _shop_names_cache
    names = []
    for name, data in SHOP.items():
        if data.get("premium"):
            continue
        price = data.get("price", 0)
        itype = data.get("type", "?")
        names.append(f"{name} ({itype}, {price}💰)")
    _shop_names_cache = names
    return names


def _build_items_block():
    """Блок со списком предметов для промпта."""
    names = _get_item_names()
    if not names:
        return ""
    # Ограничим до 40 чтобы не раздувать промпт
    chunk = names[:40]
    return ("\n\nСПИСОК ПРЕДМЕТОВ (используй ТОЧНЫЕ названия):\n" +
            "\n".join(f"  • {n}" for n in chunk) +
            "\n\nЕсли хочешь дать что-то другое — используй один из этих предметов.\n")


# ================= SANITIZE ПРОМПТА =================
_SANITIZE_MAP = {
    "убить": "победить",
    "убийство": "победа",
    "убей": "победи",
    "оружие": "снаряжение",
    "оружием": "снаряжением",
    "бой": "схватка",
    "бою": "схватке",
    "боя": "схватки",
    "кровь": "энергия",
    "крови": "энергии",
    "убиваю": "сражаюсь",
    "атака": "удар",
    "атакую": "наношу удар",
    "стреляю": "бью",
    "выстрел": "удар",
}


def _sanitize_text(text):
    """Заменяет триггерные слова перед отправкой в GigaChat."""
    if not text:
        return text
    result = text
    for bad, good in _SANITIZE_MAP.items():
        # Заменяем только целые слова (регистронезависимо)
        pattern = re.compile(r"\b" + re.escape(bad) + r"\b", re.IGNORECASE)
        result = pattern.sub(good, result)
    return result


def _is_refusal(text):
    """Проверяет, отказался ли GigaChat отвечать."""
    if not text:
        return False
    low = text.lower()
    return any(marker in low for marker in REFUSAL_MARKERS)


# ================= FALLBACK ОТВЕТЫ =================
_FALLBACKS = {
    "combat": (
        "Ты бросаешься в схватку. Твой удар достигает цели, враг отшатывается, "
        "но тут же контратакует. Между вами мелькают искры — клинок звенит о клинок. "
        "Позиция пока равная. Что будешь делать?"
    ),
    "search": (
        "Ты внимательно осматриваешь окрестности. Под старым камнем что-то блеснуло. "
        "Наклонившись, ты видишь небольшой тайник — внутри лежит что-то ценное. "
        "Ты осторожно достаёшь находку. Что будешь делать дальше?"
    ),
    "talk": (
        "Ты обращаешься к собеседнику. Он внимательно слушает, кивая в такт твоим словам. "
        "В его глазах мелькает интерес — кажется, твои слова нашли отклик. "
        "Он готов продолжить разговор. Что спросишь?"
    ),
    "move": (
        "Ты делаешь несколько шагов вперёд. Земля под ногами мягко пружинит, "
        "воздух наполнен запахами травы и влажной земли. Впереди виднеется "
        "что-то интересное. Продолжаешь путь?"
    ),
    "default": (
        "Ты совершаешь задуманное. Вокруг всё остаётся спокойным, но ты чувствуешь — "
        "мир реагирует на твои действия. Где-то вдалеке раздаётся тихий звук. "
        "Что будешь делать дальше?"
    ),
}


def _fallback_response(action):
    """Генерирует игровой ответ при отказе GigaChat."""
    low = action.lower()
    if any(w in low for w in ("атак", "бой", "бью", "удар", "драт", "сраж")):
        return _FALLBACKS["combat"]
    if any(w in low for w in ("ищу", "осмотр", "кладо", "сокровищ", "тайник", "обыск")):
        return _FALLBACKS["search"]
    if any(w in low for w in ("говор", "спрашив", "бесед", "болта", "отвеч")):
        return _FALLBACKS["talk"]
    if any(w in low for w in ("иду", "двига", "переход", "шага")):
        return _FALLBACKS["move"]
    return _FALLBACKS["default"]


# ================= КЛИЕНТ =================
import time

_client = None
_last_call = 0


def _get_client():
    global _client, _last_call
    now = time.time()
    if _client is None or (now - _last_call) > 600:
        from config import GIGACHAT_CREDENTIALS
        _client = GigaChat(credentials=GIGACHAT_CREDENTIALS,
                           verify_ssl_certs=False, model="GigaChat-2")
    _last_call = now
    return _client


def _is_blocked(text):
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)


# ================= КОНТЕКСТ ПЕРСОНАЖА =================
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

    try:
        from core.formulas import get_role, get_dmg_type, calc_p_def, calc_m_def
        role = get_role(user)
        dmg_t = get_dmg_type(user)
        lines.append(f"Роль класса: {ROLE_NAMES.get(role, role)}")
        lines.append(f"Тип урона: {DMG_NAMES.get(dmg_t, dmg_t)}")
        pdef = calc_p_def(user)
        mdef = calc_m_def(user)
        lines.append(f"P.Def: {pdef} · M.Def: {mdef}")
    except Exception:
        pass

    lines += [
        f"Уровень: {user.get('level', 1)}",
        f"HP: {user.get('hp', 100)}/{user.get('max_hp', 100)}",
    ]
    if user.get("max_mp", 0) > 0:
        lines.append(f"MP: {user.get('mp', 0)}/{user.get('max_mp', 0)}")
    lines.append(
        f"STR:{user.get('stat_str', 5)} DEX:{user.get('stat_dex', 5)} CON:{user.get('stat_con', 5)} "
        f"INT:{user.get('stat_int', 5)} WIT:{user.get('stat_wit', 5)} MEN:{user.get('stat_men', 5)}"
    )
    lines += [
        f"Золото: {user.get('gold', 0)}",
        f"Экипировка: оружие={user.get('equipped_weapon') or 'нет'}, "
        f"броня={user.get('equipped_armor') or 'нет'}, "
        f"аксессуар={user.get('equipped_accessory') or 'нет'}",
    ]
    if user.get("pet_name"):
        pn = PET_NAMES.get(user.get("pet_type"), "Питомец")
        lines.append(f"Питомец: {user.get('pet_name')} ({pn}, ур. {user.get('pet_level', 1)})")

    try:
        active = json.loads(user.get("active_skills") or "[]")
        active = [x for x in active if x][:3]
        if active:
            from core.skills import get_skill
            names = []
            for code in active:
                s = get_skill(code)
                if s:
                    names.append(f"{s['name']} ({s['mp_cost']} MP)")
            if names:
                lines.append(f"\nАКТИВНЫЕ СКИЛЫ (3 слота):")
                for n in names:
                    lines.append(f"  • {n}")
    except Exception:
        pass

    # Дневник
    try:
        journal = user.get("journal_entries") or []
        if journal:
            lines.append("\n\nДНЕВНИК ИГРОКА (ключевые события):")
            for e in journal[:8]:
                from core.journal import EVENT_ICONS
                icon = EVENT_ICONS.get(e.get("entry_type", "event"), "•")
                lines.append(f"  {icon} {e.get('entry_text', '')}")
    except Exception:
        pass

    # Память локации
    try:
        loc_events = user.get("location_events") or []
        loc_name = loc.get("name", "")
        if loc_events and loc_name:
            from core.journal import location_context_for_ai
            lines.append(location_context_for_ai(loc_events, loc_name))
    except Exception:
        pass

    # Локация
    lines.append("\n\nТЕКУЩАЯ ЛОКАЦИЯ:")
    lines.append(f"Код: {loc_code}")
    lines.append(f"Название: {loc.get('name', '?')}")
    lines.append(f"Описание: {loc.get('desc', '')}")
    lines.append(f"Тип: {loc.get('type', 'wild')}")
    lines.append(f"Уровень входа: {loc.get('level_req', 1)}+")
    if neighbors:
        lines.append("Соседние локации:")
        for code, info in neighbors:
            lines.append(f"  • {info['name']} (код {code}, ур.{info['level_req']}+)")
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


# ================= ПАРСИНГ =================
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


def _validate_item(item_name):
    """Проверяет есть ли предмет в SHOP. Возвращает точное имя или None."""
    if not item_name:
        return None
    # Точное совпадение
    if item_name in SHOP:
        return item_name
    # Регистр
    low = item_name.lower()
    for name in SHOP.keys():
        if name.lower() == low:
            return name
    # Частичное совпадение (содержит)
    for name in SHOP.keys():
        if low in name.lower() or name.lower() in low:
            return name
    return None


# ================= ГЛАВНАЯ ФУНКЦИЯ =================
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
    items_block = _build_items_block()

    # Санитизируем action перед отправкой
    safe_action = _sanitize_text(user_action)

    context = (f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}{char_ctx}"
               f"{items_block}\n\nИГРОК: {safe_action}\n\nМАСТЕР:{arc_note}")

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

    # === ОБРАБОТКА ОТКАЗА GIGACHAT ===
    if _is_refusal(text):
        logging.warning(f"GigaChat refusal on action: {user_action[:100]}")
        text = _fallback_response(user_action)

    result = {"text": text, "item": None, "location": None, "enemy": None,
              "material": None, "damage": 0, "heal": 0, "gold": 0}

    enemy, text = _extract_enemy(text)
    if enemy:
        result["enemy"] = enemy
    else:
        # Валидация предмета — только из SHOP
        item_val, text = _extract_simple(text, "ITEM")
        if item_val:
            validated = _validate_item(item_val)
            if validated:
                result["item"] = validated
            else:
                logging.info(f"GigaChat выдумал предмет «{item_val}» — отброшен")

        loc_val, text = _extract_simple(text, "LOCATION")
        if loc_val:
            result["location"] = loc_val

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
