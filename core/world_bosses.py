"""Мировые боссы — общие цели для всех игроков."""

WORLD_BOSSES = {
    "ancient_dragon": {
        "name": "🐉 Древний Дракон",
        "level": 20,
        "hp": 25000,
        "attack_dmg": 180,           # базовый урон ДО учёта P.Def
        "dmg_type": "phys",          # физический урон (режется P.Def)
        "locations": ["cave", "mountains", "abyss"],
        "desc": "Крылатый ужас. Требует команды 3+ игроков.",
    },
    "lich_king": {
        "name": "💀 Король Личей",
        "level": 25,
        "hp": 35000,
        "attack_dmg": 220,
        "dmg_type": "magic",         # магический урон (режется M.Def)
        "locations": ["ruins", "crypt", "abyss"],
        "desc": "Повелитель мёртвых. Один не справишься.",
    },
    "forest_titan": {
        "name": "🌳 Лесной Титан",
        "level": 15,
        "hp": 15000,
        "attack_dmg": 120,
        "dmg_type": "phys",
        "locations": ["forest", "glade", "swamp"],
        "desc": "Древний дух леса. Лучше с другом.",
    },
    "sea_kraken": {
        "name": "🐙 Морской Кракен",
        "level": 18,
        "hp": 20000,
        "attack_dmg": 150,
        "dmg_type": "phys",
        "locations": ["sea", "island", "port"],
        "desc": "Щупальца, что топят корабли.",
    },
}

# Спавн в 15:00, 21:00, 03:00, 09:00 (МСК)
SPAWN_HOURS_MSK = [15, 21, 3, 9]
LIFETIME_MINUTES = 120

# Кулдаун между атаками
ATTACK_COOLDOWN_SEC = 8

# Минимум HP для атаки
MIN_HP_PCT = 0.30

# Награды
GOLD_PER_1K_DAMAGE = 100
XP_PER_1K_DAMAGE = 150
TOP1_BONUS_ITEM_CHANCE = 0.7
KILLER_BONUS_MULT = 1.5

# Штраф при смерти
DEATH_GOLD_LOSS_PCT = 0.10
