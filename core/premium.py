"""Премиум-тарифы и эксклюзивные предметы за Telegram Stars."""


# ================= ПОДПИСКИ =================
SUBSCRIPTIONS = {
    "daily": {
        "name": "⚡ Дневной",
        "price": 15,
        "duration_hours": 24,
        "desc": "Безлимит энергии на 24 часа",
    },
    "weekly": {
        "name": "🌙 Недельный",
        "price": 60,
        "duration_hours": 24 * 7,
        "desc": "Безлимит + ×2 регенерация",
    },
    "monthly": {
        "name": "👑 Месячный",
        "price": 150,
        "duration_hours": 24 * 30,
        "desc": "Безлимит + ×2 регенерация + скидка 10% в магазине",
    },
    "yearly": {
        "name": "💎 Годовой",
        "price": 1200,
        "duration_hours": 24 * 365,
        "desc": "Всё из месячного на год + эксклюзивный питомец",
    },
    "forever": {
        "name": "⚡ Вечный",
        "price": 5000,
        "duration_hours": -1,
        "desc": "Безлимит навсегда + все эксклюзивы + титул «Основатель»",
    },
}


# ================= ЭКСКЛЮЗИВНЫЕ РАСЫ =================
EXCLUSIVE_RACES = {
    "prit":  {"name": "🎭 Плут",  "price": 300, "desc": "+20% золота, −15% HP"},
    "demon": {"name": "😈 Демон", "price": 350, "desc": "+15% маг. урона, слаб к свету"},
    "angel": {"name": "😇 Ангел", "price": 350, "desc": "+20% лечения, −15% физ. урона"},
}


# ================= ЭКСКЛЮЗИВНЫЕ КЛАССЫ =================
EXCLUSIVE_CLASSES = {
    "keeper": {
        "name": "🛡 Хранитель",
        "price": 500,
        "desc": "Групповое лечение, защита союзников",
    },
}


# ================= ЭКСКЛЮЗИВНАЯ ЭКИПИРОВКА =================
EXCLUSIVE_ITEMS = {
    "Клинок Судьбы":    {"price": 500, "type": "weapon", "bonus": {"str": 15}, "extra": "крит +5%"},
    "Эгида Богов":      {"price": 500, "type": "shield", "bonus": {"con": 15}, "extra": "блок 15%"},
    "Венец Владыки":    {"price": 450, "type": "helmet", "bonus": {"int": 15}, "extra": "+30% золота"},
    "Лук Апокалипсиса": {"price": 550, "type": "weapon", "bonus": {"dex": 15}, "extra": "крит +8%"},
}


# ================= ЭКСКЛЮЗИВНЫЕ ПИТОМЦЫ =================
EXCLUSIVE_PETS = {
    "lion":     {"name": "🦁 Небесный лев",    "price": 450, "desc": "+15 STR/DEX/CON"},
    "ephoenix": {"name": "🦅 Феникс вечности", "price": 500, "desc": "1 возрождение за бой"},
    "edragon":  {"name": "🐲 Древний дракон",  "price": 600, "desc": "Атака 25×ур. каждый раунд"},
}


# ================= КОСМЕТИКА =================
COSMETICS = {
    "title_immortal": {"name": "🏆 Титул «Бессмертный»",  "price": 300},
    "title_lord":     {"name": "👑 Титул «Владыка Мира»", "price": 500},
    "aura":           {"name": "✨ Аура Избранного",      "price": 400},
    "emblem":         {"name": "🎭 Именной герб",         "price": 350},
}


# ================= РАСХОДНИКИ =================
CONSUMABLES = {
    "revive_potion": {"name": "💚 Зелье возрождения",   "price": 15, "desc": "Полное HP в бою"},
    "treasure":      {"name": "🎁 Сундук сокровищ",     "price": 25, "desc": "Случайный предмет"},
    "xp_scroll":     {"name": "📜 Свиток опыта",        "price": 30, "desc": "+500 XP сразу"},
    "immortal_gem":  {"name": "💎 Кристалл бессмертия", "price": 50, "desc": "1 раз не умереть"},
}


# ================= НАБОРЫ =================
BUNDLES = {
    "lord_bundle":    {"name": "👑 Набор Владыки",      "price": 600,  "save": 100},
    "warrior_bundle": {"name": "🎖 Набор Воина",         "price": 900,  "save": 100},
    "start_bundle":   {"name": "🌟 Эксклюзивный старт",  "price": 900,  "save": 150},
    "full_bundle":    {"name": "💎 Полный набор",        "price": 2000, "save": 400},
}


# ================= СКИДКИ =================
DISCOUNTS = {
    "first_month": 0.50,
    "renewal":     0.20,
    "referral":    0.10,
    "seasonal":    0.30,
}


def get_price(base_price, discount_key=None):
    if discount_key and discount_key in DISCOUNTS:
        return int(base_price * (1 - DISCOUNTS[discount_key]))
    return base_price
