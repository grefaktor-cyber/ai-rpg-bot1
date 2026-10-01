"""Мировые боссы — общие цели для всех игроков."""

WORLD_BOSSES = {
    "ancient_dragon": {
        "name": "🐉 Древний Дракон",
        "level": 20,
        "hp": 15000,
        "atk_mult": 1.5,
        "locations": ["cave", "mountains", "abyss"],
        "desc": "Крылатый ужас, чьё дыхание плавит камень.",
    },
    "lich_king": {
        "name": "💀 Король Личей",
        "level": 25,
        "hp": 20000,
        "atk_mult": 1.7,
        "locations": ["ruins", "crypt", "abyss"],
        "desc": "Повелитель мёртвых. Его армия растёт с каждым вздохом.",
    },
    "forest_titan": {
        "name": "🌳 Лесной Титан",
        "level": 15,
        "hp": 12000,
        "atk_mult": 1.3,
        "locations": ["forest", "glade", "swamp"],
        "desc": "Древний дух леса, защищающий свои владения.",
    },
    "sea_kraken": {
        "name": "🐙 Морской Кракен",
        "level": 18,
        "hp": 14000,
        "atk_mult": 1.4,
        "locations": ["sea", "island", "port"],
        "desc": "Щупальца, что топят корабли в одну секунду.",
    },
}

# Респавн раз в 6 часов, живёт 1 час
SPAWN_INTERVAL_HOURS = 6
LIFETIME_MINUTES = 60

# Награды
GOLD_PER_1K_DAMAGE = 50
XP_PER_1K_DAMAGE = 80
TOP1_BONUS_ITEM_CHANCE = 0.5    # 50% что топ-1 получит предмет
KILLER_BONUS_MULT = 1.5          # +50% золота за последний удар
