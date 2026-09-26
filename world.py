# ================= МИР LINEAGE-2 =================
# 12 локаций, соединённых в граф. Игрок ходит только между соседями.

LOCATIONS = {
    "village": {
        "name": "Начальная деревня",
        "desc": "Небольшая деревня у подножия холмов. Дым из труб, кузница, шум рынка.",
        "exits": ["tavern", "road", "forest"],
        "level_req": 1, "type": "safe",
        "npcs": ["blacksmith", "elder"],
        "enemies": [],
        "boss": None,
    },
    "tavern": {
        "name": "Таверна «Пьяный гоблин»",
        "desc": "Тёплое место с запахом жареного мяса и эля. Слухи, песни, тёмные сделки.",
        "exits": ["village"],
        "level_req": 1, "type": "safe",
        "npcs": ["bork"],
        "enemies": [],
        "boss": None,
    },
    "road": {
        "name": "Большой тракт",
        "desc": "Пыльная дорога между деревней и портом. Караваны, разбойники, случайные встречи.",
        "exits": ["village", "forest", "port"],
        "level_req": 1, "type": "wild",
        "npcs": [],
        "enemies": ["Разбойник", "Бродячий пёс", "Гоблин-разведчик"],
        "boss": None,
    },
    "forest": {
        "name": "Тёмный лес",
        "desc": "Древние деревья смыкаются над головой. Ветра почти нет. Пахнет мхом и хвоей.",
        "exits": ["village", "road", "glade", "swamp"],
        "level_req": 2, "type": "wild",
        "npcs": ["ranger"],
        "enemies": ["Гоблин", "Лесной волк", "Гигантский паук"],
        "boss": {"name": "Древень", "level": 5, "respawn_min": 30},
    },
    "glade": {
        "name": "Волчья поляна",
        "desc": "Открытая поляна среди леса. Трава вытоптана, всюду следы волков.",
        "exits": ["forest", "ruins"],
        "level_req": 3, "type": "wild",
        "npcs": ["hermit"],
        "enemies": ["Волк-вожак", "Оборотень-новичок"],
        "boss": None,
    },
    "swamp": {
        "name": "Гиблое болото",
        "desc": "Топь с туманом. Пахнет гнилью. Тихо, только кваканье и чавканье под ногами.",
        "exits": ["forest", "ruins"],
        "level_req": 4, "type": "wild",
        "npcs": [],
        "enemies": ["Болотный гад", "Утопленник", "Ведьма-отшельница"],
        "boss": {"name": "Болотный Ходок", "level": 7, "respawn_min": 45},
    },
    "ruins": {
        "name": "Древние руины",
        "desc": "Развалины старой крепости. Колонны, обломки стен, глубокая тишина.",
        "exits": ["glade", "swamp", "mountains"],
        "level_req": 5, "type": "wild",
        "npcs": [],
        "enemies": ["Скелет-страж", "Проклятый рыцарь", "Каменный голем"],
        "boss": {"name": "Лич-хранитель", "level": 10, "respawn_min": 60},
    },
    "mountains": {
        "name": "Ледяные горы",
        "desc": "Снежные пики, ледяной ветер. Здесь выживают только сильнейшие.",
        "exits": ["ruins", "cave"],
        "level_req": 8, "type": "wild",
        "npcs": [],
        "enemies": ["Ледяной волк", "Горный тролль", "Дух метели"],
        "boss": {"name": "Ледяной Великан", "level": 13, "respawn_min": 90},
    },
    "cave": {
        "name": "Пещера дракона",
        "desc": "Глубокие туннели, пахнет серой. Эхо шагов уходит в темноту.",
        "exits": ["mountains"],
        "level_req": 12, "type": "dungeon",
        "npcs": [],
        "enemies": ["Драконыш", "Огненный элементаль", "Чешуйчатый страж"],
        "boss": {"name": "Дракон Ксарг", "level": 18, "respawn_min": 120},
    },
    "port": {
        "name": "Портовый город",
        "desc": "Шумный торговый город. Корабли, склады, моряки, контрабандисты.",
        "exits": ["road", "sea"],
        "level_req": 5, "type": "safe",
        "npcs": ["captain"],
        "enemies": [],
        "boss": None,
    },
    "sea": {
        "name": "Морской порт",
        "desc": "Пирс, уходящий в море. Волны бьют о сваи. Ветер солёный.",
        "exits": ["port", "island"],
        "level_req": 8, "type": "wild",
        "npcs": [],
        "enemies": ["Пират", "Морской змей", "Утопший матрос"],
        "boss": None,
    },
    "island": {
        "name": "Остров духов",
        "desc": "Туманный остров. Здесь время идёт иначе. Голоса шёпчут из ниоткуда.",
        "exits": ["sea"],
        "level_req": 15, "type": "wild",
        "npcs": [],
        "enemies": ["Дух-воин", "Призрак-маг", "Страж-нежить"],
        "boss": {"name": "Король Духов", "level": 22, "respawn_min": 180},
    },
}

# ================= NPC =================
NPCS = {
    "blacksmith": {
        "name": "Кузнец Гуннар", "location": "village",
        "greeting": "Хм, новичок? Работа есть — принеси мне шкуры и железо. А заодно проверь себя в Тёмном лесу.",
        "quests": ["q_iron"],
    },
    "elder": {
        "name": "Старейшина Морвен", "location": "village",
        "greeting": "Тьма растёт на востоке. Помоги нам — и деревня тебя не забудет.",
        "quests": ["q_wolves"],
    },
    "bork": {
        "name": "Трактирщик Борк", "location": "tavern",
        "greeting": "Эль есть, мясо есть, а вот с разбойниками на тракте — беда. Поможешь — налью бесплатно.",
        "quests": ["q_bandits"],
    },
    "ranger": {
        "name": "Лесник Айвен", "location": "forest",
        "greeting": "Гоблины расплодились. Убей десяток — получишь мою благодарность и кое-что из схрона.",
        "quests": ["q_goblins"],
    },
    "hermit": {
        "name": "Отшельник Син", "location": "glade",
        "greeting": "Ищешь мудрости или просто забрёл? В любом случае — помоги с волками, а я подскажу путь.",
        "quests": ["q_wolf_leader"],
    },
    "captain": {
        "name": "Капитан Кайл", "location": "port",
        "greeting": "Пираты распоясались. Нужны крепкие руки. Ты выглядишь подходяще.",
        "quests": ["q_pirates"],
    },
}

# ================= СЮЖЕТНЫЕ КВЕСТЫ NPC =================
NPC_QUESTS = {
    "q_iron": {
        "npc": "blacksmith",
        "title": "Железо для кузнеца",
        "desc": "Убей 3 гоблинов в Тёмном лесу и принеси железо.",
        "type": "kill", "target": "Гоблин", "location": "forest", "count": 3,
        "reward_gold": 150, "reward_xp": 80,
        "reward_item": "Железный меч",
        "req_level": 1,
    },
    "q_wolves": {
        "npc": "elder",
        "title": "Волки у деревни",
        "desc": "Стая волков терроризирует деревню. Убей 2 волков в Тёмном лесу.",
        "type": "kill", "target": "Лесной волк", "location": "forest", "count": 2,
        "reward_gold": 200, "reward_xp": 100,
        "reward_item": "Кожаная броня",
        "req_level": 1,
    },
    "q_bandits": {
        "npc": "bork",
        "title": "Разбойники на тракте",
        "desc": "Убей 4 разбойников на Большом тракте.",
        "type": "kill", "target": "Разбойник", "location": "road", "count": 4,
        "reward_gold": 300, "reward_xp": 150,
        "reward_item": "Кольцо силы",
        "req_level": 2,
    },
    "q_goblins": {
        "npc": "ranger",
        "title": "Нашествие гоблинов",
        "desc": "Убей 10 гоблинов в Тёмном лесу.",
        "type": "kill", "target": "Гоблин", "location": "forest", "count": 10,
        "reward_gold": 500, "reward_xp": 250,
        "reward_item": "Стальной меч",
        "req_level": 3,
    },
    "q_wolf_leader": {
        "npc": "hermit",
        "title": "Волчий вожак",
        "desc": "Убей волка-вожака на Волчьей поляне.",
        "type": "kill", "target": "Волк-вожак", "location": "glade", "count": 1,
        "reward_gold": 400, "reward_xp": 200,
        "reward_item": "Кольцо ловкости",
        "req_level": 3,
    },
    "q_pirates": {
        "npc": "captain",
        "title": "Пиратская угроза",
        "desc": "Убей 5 пиратов в Морском порту.",
        "type": "kill", "target": "Пират", "location": "sea", "count": 5,
        "reward_gold": 800, "reward_xp": 400,
        "reward_item": "Амулет мудреца",
        "req_level": 8,
    },
}

# ================= ГИЛЬДИИ =================
GUILD_CREATE_COST = 1000
GUILD_TAG_MAX = 5
GUILD_NAME_MAX = 20

# Бонусы за владение локацией
LOCATION_OWNER_BONUS = {
    "gold_mult": 1.15,     # +15% золота в этой локации для членов гильдии
    "xp_mult": 1.10,       # +10% XP
}

# ================= ДИНАМИЧЕСКИЕ СОБЫТИЯ =================
# Шаблоны событий. Раз в час выбирается одно.
EVENT_TEMPLATES = [
    {"code": "invasion", "name": "🔴 Нашествие", "desc": "+30% XP, враги сильнее",
     "duration_min": 30, "xp_mult": 1.30, "gold_mult": 1.0, "spawn_mult": 1.5},
    {"code": "treasure", "name": "💰 Клад", "desc": "+100% золота из врагов",
     "duration_min": 30, "xp_mult": 1.0, "gold_mult": 2.0, "spawn_mult": 1.0},
    {"code": "calm", "name": "🕊 Затишье", "desc": "Меньше врагов, безопаснее",
     "duration_min": 45, "xp_mult": 0.8, "gold_mult": 0.8, "spawn_mult": 0.5},
    {"code": "plague", "name": "☠️ Мор", "desc": "Враги наносят +20% урона",
     "duration_min": 30, "xp_mult": 1.2, "gold_mult": 1.2, "spawn_mult": 1.0,
     "enemy_dmg_mult": 1.2},
    {"code": "blessing", "name": "✨ Благословение", "desc": "+50% XP, +20% золота",
     "duration_min": 30, "xp_mult": 1.5, "gold_mult": 1.2, "spawn_mult": 1.0},
]


def get_location(code):
    return LOCATIONS.get(code)


def get_neighbors(code):
    loc = LOCATIONS.get(code)
    if not loc:
        return []
    return [(c, LOCATIONS[c]) for c in loc["exits"] if c in LOCATIONS]


def get_npc(npc_code):
    return NPCS.get(npc_code)


def get_npcs_in_location(loc_code):
    loc = LOCATIONS.get(loc_code)
    if not loc:
        return []
    return [(c, NPCS[c]) for c in loc.get("npcs", []) if c in NPCS]


def get_quest(qcode):
    return NPC_QUESTS.get(qcode)


def get_boss(loc_code):
    loc = LOCATIONS.get(loc_code)
    return loc.get("boss") if loc else None


def get_boss_level(loc_code):
    b = get_boss(loc_code)
    return b["level"] if b else 0


def get_random_enemy(loc_code):
    import random
    loc = LOCATIONS.get(loc_code)
    if not loc or not loc.get("enemies"):
        return None
    return random.choice(loc["enemies"])


def can_enter(loc_code, player_level):
    loc = LOCATIONS.get(loc_code)
    if not loc:
        return False, "Локация не существует"
    if player_level < loc["level_req"]:
        return False, f"Нужен уровень {loc['level_req']}+"
    return True, ""


def find_location_by_name(name):
    """Нечёткий поиск локации по названию (для текстового ввода)."""
    if not name:
        return None
    low = name.lower().strip()
    for code, loc in LOCATIONS.items():
        if low in loc["name"].lower() or loc["name"].lower() in low:
            return code
    # Ключевые слова
    keywords = {
        "forest": ["лес", "чаща", "роща"],
        "village": ["деревня", "начальная", "деревн"],
        "tavern": ["таверна", "трактир", "кабак"],
        "road": ["тракт", "дорога", "путь"],
        "glade": ["поляна", "луг"],
        "swamp": ["болото", "топь"],
        "ruins": ["руины", "развалины"],
        "mountains": ["горы", "горная", "ледян"],
        "cave": ["пещера", "дракон"],
        "port": ["порт", "город"],
        "sea": ["море", "порт", "берег"],
        "island": ["остров", "дух"],
    }
    for code, words in keywords.items():
        for w in words:
            if w in low:
                return code
    return None
