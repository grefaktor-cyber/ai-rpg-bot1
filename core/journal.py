"""Хелперы для дневника игрока: форматирование, типы событий."""

EVENT_ICONS = {
    "boss":     "🐉",
    "level":    "⭐",
    "guild":    "🏛",
    "capture":  "🏴",
    "dungeon":  "🏰",
    "location": "📍",
    "duel":     "⚔️",
    "craft":    "⚒️",
    "purchase": "💎",
    "death":    "💀",
    "event":    "•",
}


def format_journal_entry(entry):
    """Красивая строка для дневника."""
    icon = EVENT_ICONS.get(entry.get("entry_type", "event"), "•")
    text = entry.get("entry_text", "")
    # Дата
    ts = entry.get("created_at")
    date_str = ""
    if ts and hasattr(ts, "strftime"):
        date_str = ts.strftime("%d.%m %H:%M")
    line = f"{icon} {text}"
    if date_str:
        line += f"\n   <i>{date_str}</i>"
    return line


def journal_context_for_ai(journal_entries, limit=10):
    """Краткая сводка дневника для промпта ИИ."""
    if not journal_entries:
        return ""
    lines = ["\n\nДНЕВНИК ИГРОКА (ключевые события):"]
    for e in journal_entries[:limit]:
        icon = EVENT_ICONS.get(e.get("entry_type", "event"), "•")
        lines.append(f"  {icon} {e.get('entry_text', '')}")
    lines.append("ВАЖНО: используй эти события в сюжете, ссылайся на них.")
    return "\n".join(lines)
