"""Картинки локаций и боссов — локальные файлы в assets/."""

import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


LOCATION_FILES = {
    "village":   "assets/loc/village.jpg",
    "tavern":    "assets/loc/tavern.jpg",
    "road":      "assets/loc/road.jpg",
    "forest":    "assets/loc/forest.jpg",
    "glade":     "assets/loc/glade.jpg",
    "swamp":     "assets/loc/swamp.jpg",
    "ruins":     "assets/loc/ruins.jpg",
    "mountains": "assets/loc/mountains.jpg",
    "cave":      "assets/loc/cave.jpg",
    "port":      "assets/loc/port.jpg",
    "sea":       "assets/loc/sea.jpg",
    "island":    "assets/loc/island.jpg",
}


BOSS_FILES = {
    "ancient_dragon": "assets/boss/ancient_dragon.jpg",
    "lich_king":      "assets/boss/lich_king.jpg",
    "forest_titan":   "assets/boss/forest_titan.jpg",
    "sea_kraken":     "assets/boss/sea_kraken.jpg",
    "dragon_cub":     "assets/boss/dragon_cub.jpg",
    "abyss_lord":     "assets/boss/abyss_lord.jpg",
    "forest_king":    "assets/boss/forest_king.jpg",
    "world_devourer": "assets/boss/world_devourer.jpg",
}


# Точные имена из combat['enemy_name']
BOSS_NAME_MAP = {
    "Древний Дракон":    "ancient_dragon",
    "Король Личей":      "lich_king",
    "Лесной Титан":      "forest_titan",
    "Морской Кракен":    "sea_kraken",
    "Дракончик":         "dragon_cub",
    "Повелитель Бездны": "abyss_lord",
    "Лесной Король":     "forest_king",
    "Пожиратель Миров":  "world_devourer",
    "Вождь гоблинов":    "dragon_cub",
    "Древний лич":       "lich_king",
    "Король вампиров":   "lich_king",
    "Владыка Бездны":    "abyss_lord",
}

# Расширенный поиск по ключевым словам (падежи, "босс" и т.д.)
BOSS_KEYWORDS = [
    # (подстрока в lowercase, код картинки)
    ("пожирател",   "world_devourer"),
    ("world devour", "world_devourer"),
    ("повелител бездн", "abyss_lord"),
    ("владыка бездн",   "abyss_lord"),
    ("abyss lord",      "abyss_lord"),
    ("лесной корол",    "forest_king"),
    ("forest king",     "forest_king"),
    ("древн дракон",    "ancient_dragon"),
    ("ancient dragon",  "ancient_dragon"),
    ("корол лич",       "lich_king"),
    ("древн лич",       "lich_king"),
    ("lich king",       "lich_king"),
    ("лесной титан",    "forest_titan"),
    ("forest titan",    "forest_titan"),
    ("морской кракен",  "sea_kraken"),
    ("sea kraken",      "sea_kraken"),
    ("корол вампир",    "lich_king"),
    ("вождь гоблин",    "dragon_cub"),
    ("дракончик",       "dragon_cub"),
    ("dragon cub",      "dragon_cub"),
]


def get_location_image_path(loc_code):
    rel = LOCATION_FILES.get(loc_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def get_boss_image_path(boss_code):
    rel = BOSS_FILES.get(boss_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def find_boss_by_name(name):
    """Ищет код босса по имени. Точное → ключевые слова → частичное."""
    if not name:
        return None

    # 1. Точное совпадение
    if name in BOSS_NAME_MAP:
        return BOSS_NAME_MAP[name]

    low = name.lower().strip()

    # 2. Поиск по ключевым словам (регистронезависимо, падежи)
    for keyword, code in BOSS_KEYWORDS:
        if keyword in low:
            return code

    # 3. Частичное совпадение по имени
    for full, code in BOSS_NAME_MAP.items():
        fl = full.lower()
        if fl in low or low in fl:
            return code

    return None


def get_boss_image_path_by_name(name):
    code = find_boss_by_name(name)
    if code:
        return get_boss_image_path(code)
    return None


def list_missing_locations():
    return [c for c in LOCATION_FILES if get_location_image_path(c) is None]


def list_missing_bosses():
    return [c for c in BOSS_FILES if get_boss_image_path(c) is None]
