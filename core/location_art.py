"""Картинки локаций и боссов.

Источник: LoremFlickr (не требует ключа, стабильный)
    https://loremflickr.com/800/500/forest,fog

Позже можно заменить на свои URL — просто подмени словари.
"""

# Ключевые слова для тематических картинок
LOCATION_QUERIES = {
    "village":    "medieval,village",
    "tavern":     "tavern,fireplace",
    "road":       "road,landscape",
    "forest":     "forest,fog",
    "glade":      "forest,sunbeams",
    "swamp":      "swamp,marsh",
    "ruins":      "ruins,ancient",
    "mountains":  "mountains,snow",
    "cave":       "cave,rocks",
    "port":       "harbor,ships",
    "sea":        "sea,storm",
    "island":     "island,palm",
    "crypt":      "crypt,dark",
    "abyss":      "canyon,dark",
}

BOSS_QUERIES = {
    "ancient_dragon": "dragon,art",
    "lich_king":      "skeleton,dark",
    "forest_titan":   "tree,giant",
    "sea_kraken":     "octopus,sea",
    "dragon_cub":     "dragon,small",
    "abyss_lord":     "demon,dark",
    "forest_king":    "forest,king",
    "world_devourer": "monster,dark",
}


def get_location_image(loc_code, width=800, height=500):
    q = LOCATION_QUERIES.get(loc_code)
    if not q:
        return None
    return f"https://loremflickr.com/{width}/{height}/{q}"


def get_boss_image(boss_code, width=800, height=500):
    q = BOSS_QUERIES.get(boss_code)
    if not q:
        return None
    return f"https://loremflickr.com/{width}/{height}/{q}"
