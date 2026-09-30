"""Игровые данные: расы, классы, фракции, магазин (из equipment), питомцы, подземелья, крафт."""
from core.equipment import SHOP  # ← SHOP теперь в equipment.py

# ================= РАСЫ =================
RACES = {
    # ---- Обычные (доступны всем) ----
    "human":    {"name": "Человек",     "desc": "Универсал.", "premium": False,
                 "stats": {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5}},
    "elf":      {"name": "Эльф",        "desc": "Ловкий, мудрый.", "premium": False,
                 "stats": {"str": 4, "dex": 6, "con": 4, "int": 6, "wit": 6, "men": 4}},
    "dark_elf": {"name": "Тёмный эльф", "desc": "Сильная магия.", "premium": False,
                 "stats": {"str": 5, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 4}},
    "orc":      {"name": "Орк",         "desc": "Могучий воин.", "premium": False,
                 "stats": {"str": 7, "dex": 4, "con": 7, "int": 3, "wit": 5, "men": 4}},

    # ---- Премиум (только с подпиской) ----
    "demon":    {"name": "😈 Демон",    "desc": "Маг тьмы, агрессивный.", "premium": True,
                 "stats": {"str": 6, "dex": 4, "con": 4, "int": 7, "wit": 6, "men": 3}},
    "angel":    {"name": "😇 Ангел",    "desc": "Целитель и защитник.", "premium": True,
                 "stats": {"str": 4, "dex": 5, "con": 4, "int": 6, "wit": 6, "men": 5}},
    "prit":     {"name": "🎭 Плут",     "desc": "Ловкач, воровство, крит.", "premium": True,
                 "stats": {"str": 4, "dex": 7, "con": 4, "int": 5, "wit": 6, "men": 4}},
}

CLASSES = {
    "warrior": {"name": "Воин", "desc": "Мастер меча.",
                "races": ["human"],
                "bonus": {"str": 3, "con": 3}, "role": "fighter", "dmg_type": "phys"},
    "knight":  {"name": "Рыцарь", "desc": "Танк и защитник.",
                "races": ["human", "angel"],
                "bonus": {"str": 2, "con": 3, "men": 1}, "role": "tank", "dmg_type": "phys"},
    "mage":    {"name": "Маг", "desc": "Боевая магия.",
                "races": ["human", "demon"],
                "bonus": {"int": 4, "wit": 2}, "role": "mage", "dmg_type": "magic"},
    "archer":   {"name": "Лучник", "desc": "Стрелок.",
                 "races": ["elf", "prit"],
                 "bonus": {"str": 3, "dex": 3}, "role": "agile", "dmg_type": "agile"},
    "guardian": {"name": "Страж", "desc": "Защитник природы.",
                 "races": ["elf", "angel"],
                 "bonus": {"str": 1, "dex": 2, "con": 2, "wit": 1}, "role": "tank", "dmg_type": "agile"},
    "bard":     {"name": "Певчий", "desc": "Магия поддержки.",
                 "races": ["elf", "angel"],
                 "bonus": {"int": 2, "wit": 2, "men": 2}, "role": "mage", "dmg_type": "magic"},
    "assassin": {"name": "Убийца", "desc": "Скрытность и крит.",
                 "races": ["dark_elf", "demon", "prit"],
                 "bonus": {"str": 2, "dex": 4}, "role": "agile", "dmg_type": "agile"},
    "necro":    {"name": "Некромант", "desc": "Тёмная магия.",
                 "races": ["dark_elf", "demon"],
                 "bonus": {"int": 4, "wit": 2}, "role": "mage", "dmg_type": "magic"},
    "dancer":   {"name": "Танцор", "desc": "Быстрые атаки.",
                 "races": ["dark_elf", "prit"],
                 "bonus": {"str": 3, "dex": 2, "men": 1}, "role": "universal", "dmg_type": "agile"},
    "destroyer": {"name": "Разрушитель", "desc": "Максимальный урон.",
                  "races": ["orc"],
                  "bonus": {"str": 5, "con": 1}, "role": "fighter", "dmg_type": "phys"},
    "tyrant":    {"name": "Тиранин", "desc": "Быстрые атаки.",
                  "races": ["orc"],
                  "bonus": {"str": 4, "dex": 2}, "role": "agile", "dmg_type": "agile"},
    "overlord":  {"name": "Владыка", "desc": "Гибрид воина и мага.",
                  "races": ["orc"],
                  "bonus": {"str": 2, "con": 1, "int": 2, "wit": 1}, "role": "universal", "dmg_type": "magic"},
}


def classes_for_race(race_code):
    return {c: info for c, info in CLASSES.items() if race_code in info["races"]}

ROLE_HP_BONUS = {"tank": 20, "fighter": 15, "universal": 10, "agile": 5, "mage": 10}

FACTIONS = {
    "light": {"name": "Орден Света",     "desc": "+10% HP, скидка 10%",
              "hp_mult": 1.10, "shop_mult": 0.90, "gold_mult": 0.90, "dmg_mult": 1.00},
    "dark":  {"name": "Тёмное Братство", "desc": "+15% урона, +20% золота",
              "hp_mult": 0.80, "shop_mult": 1.00, "gold_mult": 1.20, "dmg_mult": 1.15},
}

PETS = {
    "wolf":    {"name": "Волк",      "price": 500,  "desc": "Атака +5×(ур)", "bonus": {"str": 2, "dex": 1}},
    "owl":     {"name": "Сова",      "price": 500,  "desc": "+15% крита",   "bonus": {"wit": 2, "int": 1}},
    "dragon":  {"name": "Дракончик", "price": 2000, "desc": "Атака через ход", "bonus": {"str": 3, "con": 1}},
    "phoenix": {"name": "Феникс",    "price": 3000, "desc": "Лечит 5% HP каждый раунд", "bonus": {"men": 3, "con": 2}},
    
    # ---- Эксклюзивные (только за Stars) ----
    "lion":    {"name": "🦁 Небесный лев",    "price": 99999,
                "desc": "+15 STR/DEX/CON", "premium": True,
                "bonus": {"str": 15, "dex": 15, "con": 15}},
    "ephoenix":{"name": "🦅 Феникс вечности", "price": 99999,
                "desc": "1 возрождение за бой", "premium": True,
                "bonus": {"men": 5, "con": 5}},
    "edragon": {"name": "🐲 Древний дракон",  "price": 99999,
                "desc": "Атака 25×ур. каждый раунд", "premium": True,
                "bonus": {"str": 10, "int": 10}},
}

DUNGEONS = {
    "goblin_cave": {
        "name": "Пещера гоблинов", "level_req": 1, "entry": 50,
        "rooms": 6, "reward_mult": 1.2,
        "enemies": ["Гоблин-разведчик", "Гоблин-воин", "Гоблин-шаман",
                    "Гоблин-воин", "Гоблин-вождь", "Вождь гоблинов"],
    },
    "old_ruins": {
        "name": "Древние руины", "level_req": 4, "entry": 200,
        "rooms": 7, "reward_mult": 2.0,
        "enemies": ["Скелет-страж", "Скелет-маг", "Каменный голем",
                    "Проклятый рыцарь", "Скелет-маг", "Древний лич-страж",
                    "Древний лич"],
    },
    "crypt": {
        "name": "Проклятый склеп", "level_req": 9, "entry": 600,
        "rooms": 8, "reward_mult": 4.0,
        "enemies": ["Вампир-новичок", "Призрак", "Вампир-воин", "Некромант",
                    "Тёмный жрец", "Королевский вампир", "Тёмный лорд",
                    "Король вампиров"],
    },
    "abyss": {
        "name": "Бездна", "level_req": 16, "entry": 2000,
        "rooms": 8, "reward_mult": 8.0,
        "enemies": ["Демон-воин", "Демон-маг", "Пожиратель душ", "Архидемон",
                    "Тёмный жрец", "Повелитель Бездны", "Древний дракон",
                    "Владыка Бездны"],
    },
}

CRAFT_RECIPES = {
    "Стальной меч":     {"base": "Железный меч",   "count": 3, "mat": "iron",    "mat_count": 5},
    "Кольчуга":         {"base": "Кожаная броня",  "count": 3, "mat": "leather", "mat_count": 5},
    "Латы рыцаря":      {"base": "Кольчуга",       "count": 2, "mat": "iron",    "mat_count": 15},
    "Клинок тьмы":      {"base": "Стальной меч",   "count": 2, "mat": "crystal", "mat_count": 10},
    "Мантия мага":      {"base": "Кожаная броня",  "count": 2, "mat": "dust",    "mat_count": 8},
    "Амулет мудреца":   {"base": "Амулет удачи",   "count": 2, "mat": "crystal", "mat_count": 5},
    "Кольцо силы":      {"base": "Амулет удачи",   "count": 1, "mat": "iron",    "mat_count": 3},
    "Кольцо ловкости":  {"base": "Амулет удачи",   "count": 1, "mat": "dust",    "mat_count": 3},
    "Перстень мудрости":{"base": "Амулет удачи",   "count": 1, "mat": "crystal", "mat_count": 3},
}

MATERIAL_NAMES = {"iron": "железо", "leather": "кожа", "dust": "магическая пыль", "crystal": "кристалл"}

DROP_TABLE = ["Кожаная броня", "Железный меч", "Амулет удачи", "Кольцо силы",
              "Кольцо ловкости", "Перстень мудрости", "Посох мага", "Лук охотника"]

ACHIEVEMENTS = {
    "first_step": "🌟 Первый шаг", "explorer_5": "🗺 Исследователь — 5 локаций",
    "explorer_10": "🗺 Странник — 10 локаций", "explorer_all": "🌍 Покоритель мира",
    "collector_5": "🎒 Коллекционер", "level_5": "⭐ Опытный — 5 уровень",
    "level_10": "👑 Ветеран — 10 уровень", "level_20": "🔥 Легенда — 20 уровень",
    "first_boss": "⚔️ Убийца боссов", "boss_5": "🐉 Легенда — 5 боссов",
    "referral_3": "👥 Друг друзей", "daily_7": "🎁 Верный игрок",
    "rich": "💰 Богач", "equipped": "⚔️ Снаряжён", "survivor": "💀 Выживший",
    "first_blood": "🩸 Первая кровь", "duelist": "🗡 Дуэлянт",
    "arena_king": "⚜️ Гроза арены", "coward": "🏳️ Трус",
    "graffiti": "✍️ Летописец", "social": "👥 Общительный",
    "pet_owner": "🐾 Хозяин", "pet_10": "🐕 Друг навек",
    "dungeon_1": "🏰 Пещерный ход", "dungeon_5": "🏰 Покоритель подземелий",
    "crafter": "⚒️ Кузнец", "upgrader": "🔨 Улучшатель",
    "guild_founder": "🏛 Основатель гильдии", "guild_member": "🏛 Член гильдии",
    "conqueror": "⚔️ Захватчик", "event_hunter": "🎯 Охотник за событиями",
    "quest_master": "📜 Мастер квестов",
    "tutorial_done": "🎓 Ученик",
}

POTION_PRICE = 25
POTION_HEAL = 30
MP_POTION_PRICE = 25
MP_POTION_RESTORE = 40


def classes_for_race(race_code):
    """Классы, доступные расе."""
    return {c: info for c, info in CLASSES.items() if race_code in info["races"]}
