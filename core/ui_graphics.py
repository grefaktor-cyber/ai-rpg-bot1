"""Игровая визуализация: прогресс-бары, карточки, иконки.

Использование:
    from core.ui_graphics import (
        bar, hp_bar, mp_bar, xp_bar, energy_bar,
        player_card, enemy_card, combat_card,
        race_icon, class_icon, faction_icon, grade_icon,
        DANGER_COLORS, rarity_icon,
    )
"""

# ================= ЦВЕТА ПО ОПАСНОСТИ =================
DANGER_COLORS = {
    "safe":    ("🟢", "Отлично"),     # HP > 80%
    "normal":  ("🟡", "Нормально"),   # HP 50-80%
    "danger":  ("🟠", "Опасно"),      # HP 30-50%
    "critical":("🔴", "Критично"),    # HP < 30%
}

# ================= ГРЕЙДЫ =================
GRADE_ICONS = {
    "common": "⚪",
    "D": "🔷",
    "C": "🔶",
    "B": "💎",
    "A": "💠",
    "S": "👑",
}

# ================= РАСЫ =================
RACE_ICONS = {
    "human":    "🧑",
    "elf":      "🧝",
    "dark_elf": "🧛",
    "orc":      "🪓",
    "demon":    "😈",
    "angel":    "😇",
    "prit":     "🎭",
}

# ================= КЛАССЫ =================
CLASS_ICONS = {
    "warrior":    "⚔️",
    "knight":     "🛡️",
    "mage":       "🔮",
    "archer":     "🏹",
    "guardian":   "🌳",
    "bard":       "🎵",
    "assassin":   "🗡️",
    "necro":      "💀",
    "dancer":     "💃",
    "destroyer":  "🔥",
    "tyrant":     "🐯",
    "overlord":   "👑",
    "keeper":     "🔱",
}

# ================= ФРАКЦИИ =================
FACTION_ICONS = {
    "light": "☀️",
    "dark":  "🌑",
}


# ================= ПРОГРЕСС-БАР =================
def bar(current, maximum, length=15, filled="█", empty="░"):
    """Универсальный прогресс-бар.
    bar(70, 100, 10) → [███████░░░]
    """
    if maximum <= 0:
        return empty * length
    ratio = max(0.0, min(1.0, current / maximum))
    filled_len = int(ratio * length)
    return filled * filled_len + empty * (length - filled_len)


def _danger_icon(current, maximum):
    if maximum <= 0:
        return "⚪"
    pct = current / maximum
    if pct > 0.80:
        return "🟢"
    if pct > 0.50:
        return "🟡"
    if pct > 0.30:
        return "🟠"
    return "🔴"


def hp_bar(current, maximum, length=15, show_pct=True):
    """HP-бар с цветовым маркером.
    ❤️ 🟢 [████████████░░░] 1200/1500 (80%)
    """
    b = bar(current, maximum, length)
    line = f"❤️ {_danger_icon(current, maximum)} <b>[{b}]</b> {current}/{maximum}"
    if show_pct and maximum > 0:
        pct = int((current / maximum) * 100)
        line += f" ({pct}%)"
    return line


def mp_bar(current, maximum, length=15, show_pct=False):
    """MP-бар."""
    b = bar(current, maximum, length)
    line = f"💧 <b>[{b}]</b> {current}/{maximum}"
    if show_pct and maximum > 0:
        line += f" ({int((current / maximum) * 100)}%)"
    return line


def xp_bar(current, next_level, length=20):
    """XP-бар."""
    b = bar(current, next_level, length)
    pct = int((current / max(1, next_level)) * 100)
    return f"⭐ <b>[{b}]</b> {current}/{next_level} XP ({pct}%)"


def energy_bar(current, maximum, length=15):
    """Energy-бар (или ∞ для премиум)."""
    if current >= 9999:
        return f"⚡ ∞ Безлимит"
    b = bar(current, maximum, length)
    return f"⚡ <b>[{b}]</b> {current}/{maximum}"


def mini_bar(current, maximum, length=8):
    """Короткий бар для инлайн-строк."""
    return bar(current, maximum, length)


# ================= ИКОНКИ =================
def race_icon(race_code):
    return RACE_ICONS.get(race_code, "🧑")


def class_icon(class_code):
    return CLASS_ICONS.get(class_code, "⚔️")


def faction_icon(faction_code):
    return FACTION_ICONS.get(faction_code, "☀️")


def grade_icon(grade):
    return GRADE_ICONS.get(grade, "⚪")


def rarity_icon(rarity_pct):
    """Редкость по проценту выпадения (чем меньше %, тем реже)."""
    if rarity_pct <= 1:
        return "🌟"  # легендарка
    if rarity_pct <= 5:
        return "💎"  # эпик
    if rarity_pct <= 15:
        return "🔷"  # редкий
    if rarity_pct <= 40:
        return "🔹"  # необычный
    return "⚪"


# ================= КАРТОЧКИ =================
def player_card(user, compact=False):
    """Карточка игрока для боя/меню.
    compact=True — короткая версия (для строки в бою).
    """
    race_ico = race_icon(user.get("race", ""))
    class_ico = class_icon(user.get("class", ""))
    faction_ico = faction_icon(user.get("faction", ""))

    name = user.get("char_name", "?")
    level = user.get("level", 1)

    if compact:
        return (f"{class_ico} <b>{name}</b> "
                f"(Ур. {level}) {race_ico}{faction_ico}")

    lines = [
        f"{class_ico} <b>{name}</b> {race_ico}{faction_ico}",
        f"⭐ Ур. <b>{level}</b>",
        hp_bar(user.get("hp", 0), user.get("max_hp", 1), length=15),
    ]
    if user.get("max_mp", 0) > 0:
        lines.append(mp_bar(user.get("mp", 0), user.get("max_mp", 1),
                             length=15))
    return "\n".join(lines)


def enemy_card(combat):
    """Карточка врага для боя."""
    name = combat.get("enemy_name", "?")
    level = combat.get("enemy_level", 1)
    hp = combat.get("enemy_hp", 0)
    max_hp = combat.get("enemy_max_hp", 1)
    is_boss = combat.get("is_boss", 0)

    boss_tag = " 🐉 <b>БОСС</b>" if is_boss else ""
    danger = _danger_icon(hp, max_hp)

    lines = [
        f"⚔️ <b>{name}</b> (Ур. {level}){boss_tag}",
        f"{danger} <b>[{bar(hp, max_hp, 15)}]</b> {hp}/{max_hp}",
    ]
    return "\n".join(lines)


def combat_card(user, combat, round_num=None, event=None):
    """Полная карточка боя — враг + игрок + раунд."""
    lines = []
    if round_num is not None:
        header = f"⚔️ <b>РАУНД {round_num}</b>"
        if event:
            header += f" · {event.get('event_name', '')}"
        lines.append(header)
        lines.append("")
    lines.append(enemy_card(combat))
    lines.append("")
    lines.append(player_card(user))
    return "\n".join(lines)


# ================= ЦВЕТНЫЕ ТЕГИ =================
def hp_status(current, maximum):
    """Возвращает кортеж (иконка, текст, нужен ли алерт)."""
    if maximum <= 0:
        return ("⚪", "—", False)
    pct = current / maximum
    if pct > 0.80:
        return ("🟢", "Отлично", False)
    if pct > 0.50:
        return ("🟡", "Нормально", False)
    if pct > 0.30:
        return ("🟠", "Опасно", True)
    return ("🔴", "Критично", True)
