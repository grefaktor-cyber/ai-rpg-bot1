"""Картинки рас и классов — локальные файлы в assets/."""

import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================= РАСЫ =================
RACE_FILES = {
    "human":    "assets/race/human.jpg",
    "elf":      "assets/race/elf.jpg",
    "dark_elf": "assets/race/dark_elf.jpg",
    "orc":      "assets/race/orc.jpg",
    "demon":    "assets/race/demon.jpg",
    "angel":    "assets/race/angel.jpg",
    "prit":     "assets/race/prit.jpg",
}


# ================= КЛАССЫ =================
CLASS_FILES = {
    "warrior":   "assets/class/warrior.jpg",
    "knight":    "assets/class/knight.jpg",
    "mage":      "assets/class/mage.jpg",
    "archer":    "assets/class/archer.jpg",
    "guardian":  "assets/class/guardian.jpg",
    "bard":      "assets/class/bard.jpg",
    "assassin":  "assets/class/assassin.jpg",
    "necro":     "assets/class/necro.jpg",
    "dancer":    "assets/class/dancer.jpg",
    "destroyer": "assets/class/destroyer.jpg",
    "tyrant":    "assets/class/tyrant.jpg",
    "overlord":  "assets/class/overlord.jpg",
    "keeper":    "assets/class/keeper.jpg",
}


def get_race_image_path(race_code):
    rel = RACE_FILES.get(race_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def get_class_image_path(class_code):
    rel = CLASS_FILES.get(class_code)
    if not rel:
        return None
    full = os.path.join(_BASE, rel)
    return full if os.path.exists(full) else None


def get_race_image_path_by_name(name):
    """Ищет по имени, но у нас имена = коды, поэтому просто маппинг ниже."""
    return None  # используем код напрямую


def get_class_image_path_by_name(name):
    """Ищет по имени, но у нас имена = коды, поэтому просто маппинг ниже."""
    return None  # используем код напрямую


def list_missing_races():
    return [c for c in RACE_FILES if get_race_image_path(c) is None]


def list_missing_classes():
    return [c for c in CLASS_FILES if get_class_image_path(c) is None]
