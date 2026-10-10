"""Картинки локаций и боссов — локальные файлы в assets/."""

import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================= ЛОКАЦИИ =================
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
    "crypt":     "assets/loc/crypt.jpg",
    "abyss":     "assets/loc/abyss.jpg",
}


# ================= БОССЫ =================
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


# ================= МАППИНГ ИМЁН БОССОВ =================
# Ключ — точное имя (как в world.py / world_bosses.py)
# Значение — код картинки в BOSS_FILES
BOSS_NAME_MAP = {
    "Древний Дракон":       "ancient_dragon",
    "Король Личей":         "lich_king",
    "Лесной Титан":         "forest_titan",
    "Морской Кракен":       "sea_kraken",
    "Дракончик":            "dragon_cub",
    "Повелитель Бездны":    "abyss_lord",
    "Лесной Король":        "forest_king",
    "Пожиратель Миров":     "world_devourer",
    # Региональные боссы подземелий
    "Вождь гоблинов":       "dragon_cub",
    "Древний лич":          "lich_king",
    "Король вампиров":      "lich_king",
    "Владыка Бездны":       "abyss_lord",
}


def get_location_image_path(loc_code):
    """Абсолютный путь к файлу локации или None."""
    rel = LOCATION_FILES.get(loc_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def get_boss_image_path(boss_code):
    """Абсолютный путь к файлу босса или None."""
    rel = BOSS_FILES.get(boss_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def find_boss_by_name(name):
    """Ищет код босса по имени. Возвращает код или None."""
    if not name:
        return None
    if name in BOSS_NAME_MAP:
        return BOSS_NAME_MAP[name]
    low = name.lower()
    for full, code in BOSS_NAME_MAP.items():
        if full.lower() in low or low in full.lower():
            return code
    return None


def get_boss_image_path_by_name(name):
    """Абсолютный путь к картинке босса по имени."""
    code = find_boss_by_name(name)
    if code:
        return get_boss_image_path(code)
    return None


def list_missing_locations():
    """Хелпер — какие локации без файла."""
    return [c for c in LOCATION_FILES if get_location_image_path(c) is None]


def list_missing_bosses():
    """Хелпер — какие боссы без файла."""
    return [c for c in BOSS_FILES if get_boss_image_path(c) is None]
