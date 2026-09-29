"""Скилы и мана — заготовка на Этап 2."""


# ================= МАНА =================
def get_max_mp(user):
    """Максимум маны."""
    return 50 + user.get("stat_int", 5) * 5 + user.get("level", 1) * 3


def get_mp_regen_in_combat(user):
    """Регенерация MP за раунд боя — 5%."""
    return int(get_max_mp(user) * 0.05)


def get_mp_regen_per_action(user):
    """Регенерация MP за действие вне боя — 20%."""
    return int(get_max_mp(user) * 0.20)


# ================= СКИЛЫ ПО КЛАССАМ (заготовка) =================
# Формат: код_класса → {код_скила: {...}}
# Пока только для Воина — остальные добавим на Этапе 2.

SKILLS = {
    "warrior": {
        "power_strike": {
            "name": "Мощный удар",
            "level_req": 1,
            "mp_cost": 15,
            "multiplier": 2.0,
            "type": "attack",
            "desc": "STR × 2.0 урона",
        },
        "battle_cry": {
            "name": "Боевой клич",
            "level_req": 3,
            "mp_cost": 20,
            "multiplier": 0.0,
            "type": "buff",
            "desc": "+30% урона на 3 раунда",
        },
        "stance": {
            "name": "Стойка",
            "level_req": 5,
            "mp_cost": 10,
            "multiplier": 0.0,
            "type": "defense",
            "desc": "−50% урона в раунде",
        },
    },
}


# ================= РАСОВЫЕ СКИЛЫ (заготовка) =================
RACIAL_SKILLS = {
    "human":    {"name": "Воля",       "desc": "+20% HP при <30%"},
    "elf":      {"name": "Глаз ястреба","desc": "+15% крита"},
    "dark_elf": {"name": "Тень",       "desc": "Первый удар — крит"},
    "orc":      {"name": "Берсерк",    "desc": "+30% урона при <50% HP"},
    "prit":     {"name": "Хитрость",   "desc": "+20% золота с убийств"},
    "demon":    {"name": "Адское пламя","desc": "+15% урона магии"},
    "angel":    {"name": "Небесный щит","desc": "+20% лечения"},
}


# ================= ПАССИВНЫЕ СКИЛЫ =================
PASSIVE_SKILLS = {
    "human":    {"name": "Приспособление", "desc": "+5% ко всем действиям"},
    "elf":      {"name": "Ловкость",       "desc": "+10% DEX"},
    "dark_elf": {"name": "Жажда силы",     "desc": "+10% INT"},
    "orc":      {"name": "Живучесть",      "desc": "+15% max HP"},
    "prit":     {"name": "Воровство",      "desc": "+15% золота"},
    "demon":    {"name": "Тёмный огонь",   "desc": "+10% маг. урона"},
    "angel":    {"name": "Милосердие",     "desc": "+15% лечения"},
}
