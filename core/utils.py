"""Общие утилиты для всего бота."""


def parse_item(s):
    """'Стальной меч+2' → ('Стальной меч', 2).
    'Меч' → ('Меч', 0)."""
    if not s:
        return "", 0
    import re as _re
    m = _re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def hp_bar(current, maximum, length=10):
    """Визуальная полоска HP: ████████░░"""
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def danger_emoji(player_level, enemy_level, is_boss):
    """Цветовая оценка опасности врага."""
    if is_boss:
        return "🐉"
    diff = enemy_level - player_level
    if diff <= -3:
        return "🟢"
    if diff <= -1:
        return "🟡"
    if diff <= 1:
        return "🟠"
    if diff <= 3:
        return "🔴"
    return "💀"


def faction_mult(user, key):
    """Множитель фракции (hp_mult, gold_mult, shop_mult, dmg_mult)."""
    FACTIONS = {
        "light": {"hp_mult": 1.10, "shop_mult": 0.90, "gold_mult": 0.90, "dmg_mult": 1.00},
        "dark":  {"hp_mult": 0.80, "shop_mult": 1.00, "gold_mult": 1.20, "dmg_mult": 1.15},
    }
    f = FACTIONS.get(user.get("faction", ""))
    if not f:
        return 1.0
    return f.get(key, 1.0)


def calc_stats(race_code, class_code):
    """Базовые статы от расы + бонус класса."""
    RACES = {
        "human":    {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5},
        "elf":      {"str": 4, "dex": 6, "con": 4, "int": 6, "wit": 6, "men": 4},
        "dark_elf": {"str": 5, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 4},
        "orc":      {"str": 7, "dex": 4, "con": 7, "int": 3, "wit": 5, "men": 4},
        "prit":     {"str": 4, "dex": 7, "con": 4, "int": 5, "wit": 6, "men": 4},
        "demon":    {"str": 6, "dex": 4, "con": 4, "int": 7, "wit": 6, "men": 3},
        "angel":    {"str": 4, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 5},
    }
    CLASSES = {
        "warrior":   {"str": 3, "con": 3},
        "knight":    {"str": 2, "con": 3, "men": 1},
        "mage":      {"int": 4, "wit": 2},
        "archer":    {"str": 3, "dex": 3},
        "assassin":  {"str": 2, "dex": 4},
        "necro":     {"int": 4, "wit": 2},
        "dancer":    {"str": 3, "dex": 2, "men": 1},
        "destroyer": {"str": 5, "con": 1},
        "tyrant":    {"str": 4, "dex": 2},
        "overlord":  {"str": 2, "con": 1, "int": 2, "wit": 1},
        "priest":    {"men": 3, "wit": 3},
        "bard":      {"int": 2, "wit": 2, "men": 2},
        "guardian":  {"str": 1, "dex": 2, "con": 2, "wit": 1},
        "hunter":    {"str": 2, "dex": 2, "con": 2},
        "defender":  {"str": 3, "con": 2, "men": 1},
        "keeper":    {"str": 3, "dex": 1, "con": 4, "int": 1, "wit": 2, "men": 4},
    }
    race = RACES.get(race_code, RACES["human"]).copy()
    for k, v in CLASSES.get(class_code, {}).items():
        race[k] = race.get(k, 0) + v
    return race
