"""Картинки локаций и боссов.

Использует Unsplash Source (без ключа):
    https://source.unsplash.com/800x500/?{query}

Работает сразу. Позже можно заменить на:
- свои URL (с Vercel / GitHub / Supabase Storage)
- локальные файлы (send_photo с file_id)

Для замены — просто поменяй значения в словарях.
"""

# Запрос для Unsplash (ключевые слова на английском, т.к. сервис англоязычный)
LOCATION_QUERIES = {
    "village":    "medieval,village,fantasy,dawn",
    "tavern":     "tavern,medieval,interior,fireplace",
    "road":       "old,road,fields,sunset",
    "forest":     "dark,forest,fog,mystical",
    "glade":      "forest,glade,sunbeams,enchanted",
    "swamp":      "swamp,marsh,fog,dark",
    "ruins":      "ancient,ruins,stone,columns",
    "mountains":  "snowy,mountains,peaks,ice",
    "cave":       "cave,rocks,dark,torches",
    "port":       "seaport,harbor,ships,sunset",
    "sea":        "stormy,sea,waves,dark",
    "island":     "mysterious,island,fog,palms",
    "crypt":      "crypt,catacombs,stone,dark",
    "abyss":      "abyss,chasm,dark,glow",
}

# Для боссов
BOSS_QUERIES = {
    "ancient_dragon": "dragon,fantasy,red,sky",
    "lich_king":      "lich,undead,fantasy,dark",
    "forest_titan":   "titan,tree,fantasy,forest",
    "sea_kraken":     "kraken,sea,monster,storm",
    "dragon_cub":     "baby,dragon,fantasy,cute",
    "abyss_lord":     "demon,lord,fantasy,abyss",
    "forest_king":    "forest,king,tree,fantasy",
    "world_devourer": "monster,world,fantasy,shadow",
}


def get_location_image(loc_code, width=800, height=500):
    """Возвращает URL картинки локации.

    Если в LOCATION_QUERIES нет запроса — возвращает None.
    """
    q = LOCATION_QUERIES.get(loc_code)
    if not q:
        return None
    return f"https://source.unsplash.com/{width}x{height}/?{q}"


def get_boss_image(boss_code, width=800, height=500):
    """Возвращает URL картинки босса."""
    q = BOSS_QUERIES.get(boss_code)
    if not q:
        return None
    return f"https://source.unsplash.com/{width}x{height}/?{q}"
