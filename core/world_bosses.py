"""Мировые боссы — общие цели для всех игроков."""

WORLD_BOSSES = {
    "ancient_dragon": {
        "name": "🐉 Древний Дракон",
        "level": 20,
        "hp": 20000,
        "attack_dmg": 130,       # урон по игроку в ответ
        "locations": ["cave", "mountains", "abyss"],
        "desc": "Крылатый ужас. Требует команды из 3+ игроков.",
    },
    "lich_king": {
        "name": "💀 Король Личей",
        "level": 25,
        "hp": 28000,
        "attack_dmg": 160,
        "locations": ["ruins", "crypt", "abyss"],
        "desc": "Повелитель мёртвых. Один не справишься.",
    },
    "forest_titan": {
        "name": "🌳 Лесной Титан",
        "level": 15,
        "hp": 12000,
        "attack_dmg": 90,
        "locations": ["forest", "glade", "swamp"],
        "desc": "Древний дух леса. Лучше с другом.",
    },
    "sea_kraken": {
        "name": "🐙 Морской Кракен",
        "level": 18,
        "hp": 16000,
        "attack_dmg": 110,
        "locations": ["sea", "island", "port"],
        "desc": "Щупальца, что топят корабли.",
    },
}

# Спавн в 14:00, 20:00, 02:00, 08:00 (МСК)
SPAWN_HOURS_MSK = [14, 20, 2, 8]
LIFETIME_MINUTES = 120  # живёт 2 часа

# Кулдаун между атаками игрока
ATTACK_COOLDOWN_SEC = 8

# Минимум HP для атаки (% от max)
MIN_HP_PCT = 0.25

# Награды
GOLD_PER_1K_DAMAGE = 100
XP_PER_1K_DAMAGE = 150
TOP1_BONUS_ITEM_CHANCE = 0.7
KILLER_BONUS_MULT = 1.5

# Штраф при смерти
DEATH_GOLD_LOSS_PCT = 0.10
