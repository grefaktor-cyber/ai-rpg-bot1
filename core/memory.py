"""Память мира — 4 слоя контекста для ИИ с автоочисткой.

Слой 1: активная история (последние 30 действий) — полный текст
Слой 2: сводка (действия 31–150) — 1 строка на 10 действий
Слой 3: дневник (ключевые события) — короткие записи
Слой 4: архив (всё старое) — не отправляется в ИИ

Общий размер контекста для GigaChat всегда ~5000 символов.
"""


# ================= ЛИМИТЫ =================
STORY_MAX_CHARS = 3000          # активная история
SUMMARY_MAX_CHARS = 500         # сводка
JOURNAL_MAX_RECORDS = 10        # последние записи дневника
JOURNAL_RECORD_MAX = 100        # длина одной записи
WORLD_EVENTS_MAX = 5            # события локации для ИИ
WORLD_EVENTS_TTL_DAYS = 7       # срок хранения событий


# ================= СЛОЙ 1: АКТИВНАЯ ИСТОРИЯ =================
def trim_story(story, max_chars=STORY_MAX_CHARS):
    """Обрезает story до последних N символов по границе сообщения."""
    if not story or len(story) <= max_chars:
        return story or ""
    # Ищем границу по последнему "МАСТЕР:" или "ИГРОК:"
    trimmed = story[-max_chars:]
    # Сдвигаем до ближайшего перевода строки
    first_nl = trimmed.find("\n")
    if first_nl > 0 and first_nl < 200:
        trimmed = trimmed[first_nl + 1:]
    return trimmed.strip()


# ================= СЛОЙ 2: СВОДКА =================
def build_summary_prompt(old_summary, new_story):
    """Промпт для GigaChat, чтобы сделать сводку.
    Вызывается раз в 10 действий, если story > 3000 символов.
    """
    return (
        f"Предыдущая сводка:\n{old_summary or '(нет)'}\n\n"
        f"Новые действия игрока:\n{new_story}\n\n"
        f"Сделай КРАТКУЮ сводку в 2-3 предложениях: что игрок сделал, "
        f"что нашёл, куда дошёл. Только факты, без эпитетов. "
        f"Ответь одним абзацем на русском, не более 500 символов."
    )


# ================= СЛОЙ 3: ДНЕВНИК =================
# Типы ключевых событий для дневника
JOURNAL_EVENTS = {
    "boss_kill":    "Убил босса",
    "level_up":     "Достиг уровня",
    "new_location": "Посетил",
    "quest_done":   "Выполнил квест",
    "guild_join":   "Вступил в гильдию",
    "guild_create": "Основал гильдию",
    "location_cap": "Захватил локацию",
    "achievement":  "Получил достижение",
    "item_rare":    "Нашёл редкий предмет",
    "duel_win":     "Победил в дуэли",
}


def format_journal_entry(event_type, value):
    """Создать запись дневника."""
    prefix = JOURNAL_EVENTS.get(event_type, event_type)
    text = f"{prefix} {value}"[:JOURNAL_RECORD_MAX]
    return text


def trim_journal(entries):
    """Оставить только последние N записей дневника."""
    if not entries:
        return []
    return entries[-JOURNAL_MAX_RECORDS:]


# ================= СЛОЙ 4: АРХИВ =================
# Не отправляется в ИИ. Используется только для /journal.
# Просто помечаем всё старое как archived=1 в БД.


# ================= СБОРКА КОНТЕКСТА ДЛЯ ИИ =================
def build_memory_context(user, world_events=None, journal=None):
    """Собирает краткий блок памяти для промпта GigaChat.
    
    Возвращает строку, которую нужно добавить в контекст.
    """
    parts = []

    summary = user.get("story_summary")
    if summary:
        parts.append(f"📖 ПАМЯТЬ ИГРОКА:\n{summary[:SUMMARY_MAX_CHARS]}")

    if journal:
        recent = journal[-JOURNAL_MAX_RECORDS:]
        if recent:
            lines = "\n".join(f"• {e}" for e in recent)
            parts.append(f"📔 ДНЕВНИК (последние события):\n{lines}")

    if world_events:
        recent_events = world_events[:WORLD_EVENTS_MAX]
        if recent_events:
            lines = "\n".join(f"• {e}" for e in recent_events)
            parts.append(f"🌍 ЧТО ПРОИСХОДИЛО ЗДЕСЬ:\n{lines}")

    return "\n\n".join(parts) if parts else ""


# ================= ОЧИСТКА =================
def should_trim(user):
    """Пора ли обрезать story и делать сводку?"""
    story = user.get("story", "")
    return len(story) > STORY_MAX_CHARS


def should_update_summary(user):
    """Пора ли обновить сводку (каждые 10 действий после 30)?"""
    action_count = user.get("action_count", 0)
    return action_count > 30 and action_count % 10 == 0
