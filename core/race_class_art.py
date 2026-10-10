"""Картинки рас и классов — локальные файлы в assets/."""

import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================= РАСЫ =================
RACE_FILES = {
    "human":     "assets/race/human.jpg",
    "elf":       "assets/race/elf.jpg",
    "dark_elf":  "assets/race/dark_elf.jpg",
    "orc":       "assets/race/orc.jpg",
    "demon":     "assets/race/demon.jpg",
    "angel":     "assets/race/angel.jpg",
    "rogue":     "assets/race/rogue.jpg",
}

# Русские названия → код
RACE_NAME_MAP = {
    "Человек":      "human",
    "Эльф":         "elf",
    "Тёмный эльф":  "dark_elf",
    "Темный эльф":  "dark_elf",
    "Орк":          "orc",
    "Демон":        "demon",
    "Ангел":        "angel",
    "Плут":         "rogue",
}


# ================= КЛАССЫ =================
CLASS_FILES = {
    "warrior":  "assets/class/warrior.jpg",
    "knight":   "assets/class/knight.jpg",
    "keeper":   "assets/class/keeper.jpg",
    "archer":   "assets/class/archer.jpg",
    "mage":     "assets/class/mage.jpg",
    "necro":    "assets/class/necro.jpg",
    "bard":     "assets/class/bard.jpg",
    "overlord": "assets/class/overlord.jpg",
}

# Русские названия → код
CLASS_NAME_MAP = {
    "Воин":         "warrior",
    "Рыцарь":       "knight",
    "Хранитель":    "keeper",
    "Лучник":       "archer",
    "Маг":          "mage",
    "Некромант":    "necro",
    "Бард":         "bard",
    "Владыка":      "overlord",
}


# ================= ФУНКЦИИ =================
def get_race_image_path(race_code):
    """Абсолютный путь к файлу расы или None."""
    rel = RACE_FILES.get(race_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def get_class_image_path(class_code):
    """Абсолютный путь к файлу класса или None."""
    rel = CLASS_FILES.get(class_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def find_race_code(name):
    """Ищет код расы по русскому названию."""
    if not name:
        return None
    if name in RACE_NAME_MAP:
        return RACE_NAME_MAP[name]
    low = name.lower()
    for rn, code in RACE_NAME_MAP.items():
        if rn.lower() in low or low in rn.lower():
            return code
    return None


def find_class_code(name):
    """Ищет код класса по русскому названию."""
    if not name:
        return None
    if name in CLASS_NAME_MAP:
        return CLASS_NAME_MAP[name]
    low = name.lower()
    for cn, code in CLASS_NAME_MAP.items():
        if cn.lower() in low or low in cn.lower():
            return code
    return None


def get_race_image_path_by_name(name):
    code = find_race_code(name)
    if code:
        return get_race_image_path(code)
    return None


def get_class_image_path_by_name(name):
    code = find_class_code(name)
    if code:
        return get_class_image_path(code)
    return None


def list_missing_races():
    return [c for c in RACE_FILES if get_race_image_path(c) is None]


def list_missing_classes():
    return [c for c in CLASS_FILES if get_class_image_path(c) is None]
