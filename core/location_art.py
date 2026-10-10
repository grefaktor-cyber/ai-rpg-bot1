"""Картинки локаций и боссов — локальные файлы в assets/.

Как добавить новую:
1. Положи файл в assets/loc/ или assets/boss/
2. Добавь название в словарь ниже
3. Всё — бот сам подгрузит
"""

import os

# Базовая папка проекта (там где main.py)
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


def get_location_image_path(loc_code):
    """Возвращает абсолютный путь к файлу локации или None.

    Проверяет что файл реально существует.
    """
    rel = LOCATION_FILES.get(loc_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    if os.path.exists(full):
        return full
    return None


def get_boss_image_path(boss_code):
    """Возвращает абсолютный путь к файлу босса или None."""
    rel = BOSS_FILES.get(boss_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    if os.path.exists(full):
        return full
    return None


def list_missing_locations():
    """Хелпер — возвращает список локаций без файла (для диагностики)."""
    return [code for code in LOCATION_FILES
            if get_location_image_path(code) is None]


def list_missing_bosses():
    """Хелпер — возвращает список боссов без файла."""
    return [code for code in BOSS_FILES
            if get_boss_image_path(code) is None]
