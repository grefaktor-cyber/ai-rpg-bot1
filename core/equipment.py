"""Экипировка 2.0: типы, привязки к классам, грейды, сеты, магазин."""

# ================= ПРИВЯЗКА К КЛАССАМ =================
# Тип брони по классу
CLASS_ARMOR_TYPE = {
    "warrior":    "heavy",
    "knight":     "heavy",
    "destroyer":  "heavy",
    "tyrant":     "heavy",
    "archer":     "light",
    "guardian":   "light",
    "assassin":   "light",
    "dancer":     "light",
    "mage":       "robe",
    "necro":      "robe",
    "bard":       "robe",
    "overlord":   "robe",
}

# Разрешённые типы оружия по классу
CLASS_WEAPON_TYPES = {
    "warrior":    ["sword_1h"],
    "knight":     ["sword_1h"],
    "mage":       ["staff"],
    "archer":     ["bow", "dagger"],
    "guardian":   ["spear"],
    "bard":       ["staff"],
    "assassin":   ["dagger"],
    "necro":      ["staff"],
    "dancer":     ["dual"],
    "destroyer":  ["sword_2h"],
    "tyrant":     ["sword_2h", "cestus"],
    "overlord":   ["staff"],
}

# Кто может носить щит (одноручное оружие)
SHIELD_CLASSES = ["warrior", "knight"]

# Слоты
SLOTS = ["weapon", "helmet", "armor", "boots", "shield", "accessory", "ring"]
SLOT_NAMES = {
    "weapon": "🗡 Оружие",
    "helmet": "👑 Шлем",
    "armor": "🛡 Броня",
    "boots": "👢 Сапоги",
    "shield": "🛡 Щит",
    "accessory": "💍 Амулет",
    "ring": "💎 Кольцо",
}

# ================= СЕТОВЫЕ БОНУСЫ =================
# Активируются, если надеть 3 части брони одного типа И одного грейда
# (helmet + armor + boots одного armor_type и grade)
SET_BONUSES = {
    "heavy": {
        "hp_mult": 1.15,       # +15% max HP
        "pdef_mult": 1.10,     # +10% P.Def
        "desc": "+15% HP, +10% P.Def",
    },
    "light": {
        "dex_bonus": 3,
        "crit_bonus": 5,       # +5% шанс крита
        "desc": "+3 DEX, +5% крит",
    },
    "robe": {
        "mp_mult": 1.20,       # +20% max MP
        "mdef_mult": 1.15,     # +15% M.Def
        "desc": "+20% MP, +15% M.Def",
    },
}

# Грейды
GRADES = {
    "common": {"name": "Обычный", "level_req": 1,  "desc": "Базовый"},
    "D":      {"name": "D",       "level_req": 20, "desc": "Закалённый"},
    "C":      {"name": "C",       "level_req": 40, "desc": "Мастерский"},
}


# ================= МАГАЗИН =================
SHOP = {}


def _weapon(name, subtype, grade, price, bonus, classes=None, level_req=None):
    SHOP[name] = {
        "type": "weapon", "slot": "weapon", "subtype": subtype,
        "grade": grade,
        "level_req": level_req or GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": classes or [],
    }


def _armor(name, armor_type, part, grade, price, bonus, level_req=None):
    SHOP[name] = {
        "type": "armor", "slot": part, "armor_type": armor_type,
        "grade": grade,
        "level_req": level_req or GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": [],
    }


def _shield(name, grade, price, bonus, level_req=None):
    SHOP[name] = {
        "type": "shield", "slot": "shield", "grade": grade,
        "level_req": level_req or GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": SHIELD_CLASSES,
    }


def _accessory(name, slot, grade, price, bonus, level_req=None):
    SHOP[name] = {
        "type": "accessory", "slot": slot, "grade": grade,
        "level_req": level_req or GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": [],
    }


def _potion(name, price, heal_hp=0, heal_mp=0):
    SHOP[name] = {
        "type": "potion", "slot": "", "grade": "common",
        "level_req": 1, "price": price, "bonus": {},
        "classes": [], "heal_hp": heal_hp, "heal_mp": heal_mp,
    }


# ---------- Старые предметы (совместимость) ----------
_weapon("Железный меч", "sword_1h", "common", 50, {"str": 2})
_weapon("Стальной меч", "sword_1h", "D", 250, {"str": 5})
_weapon("Клинок тьмы", "sword_1h", "C", 1200, {"str": 10, "dex": 2})
_weapon("Посох мага", "staff", "common", 200, {"int": 4})
_weapon("Лук охотника", "bow", "common", 200, {"dex": 4})

_armor("Кожаная броня", "heavy", "armor", "common", 50, {"con": 2})
_armor("Кольчуга", "heavy", "armor", "D", 300, {"con": 5})
_armor("Мантия мага", "robe", "armor", "common", 250, {"int": 3, "wit": 2})
_armor("Латы рыцаря", "heavy", "armor", "C", 1200, {"con": 10})

_accessory("Амулет удачи", "accessory", "common", 150, {"men": 3})
_accessory("Кольцо силы", "ring", "common", 200, {"str": 3})
_accessory("Перстень мудрости", "ring", "common", 200, {"int": 3})
_accessory("Кольцо ловкости", "ring", "common", 200, {"dex": 3})
_accessory("Амулет мудреца", "accessory", "C", 800, {"int": 5, "wit": 3})

# ---------- Оружие: Common ----------
_weapon("Короткий меч",    "sword_1h", "common", 50,  {"str": 2}, ["warrior", "knight"])
_weapon("Тяжёлый топор",   "sword_2h", "common", 80,  {"str": 3}, ["destroyer", "tyrant"])
_weapon("Ржавый кинжал",   "dagger",   "common", 50,  {"dex": 2}, ["assassin", "archer"])
_weapon("Короткий лук",    "bow",      "common", 50,  {"dex": 2}, ["archer"])
_weapon("Деревянный посох","staff",    "common", 50,  {"int": 2}, ["mage", "necro", "bard", "overlord"])
_weapon("Простое копьё",   "spear",    "common", 60,  {"str": 2}, ["guardian"])
_weapon("Парные кинжалы",  "dual",     "common", 60,  {"dex": 2}, ["dancer"])
_weapon("Кожаные кастеты", "cestus",   "common", 60,  {"str": 2}, ["tyrant"])

# ---------- Оружие: D ----------
_weapon("Длинный меч",     "sword_1h", "D", 400, {"str": 5}, ["warrior", "knight"])
_weapon("Боевой топор",    "sword_2h", "D", 600, {"str": 7}, ["destroyer", "tyrant"])
_weapon("Кинжал убийцы",   "dagger",   "D", 400, {"dex": 5}, ["assassin", "archer"])
_weapon("Длинный лук",     "bow",      "D", 400, {"dex": 5}, ["archer"])
_weapon("Крепкий посох",   "staff",    "D", 400, {"int": 5}, ["mage", "necro", "bard", "overlord"])
_weapon("Длинное копьё",   "spear",    "D", 450, {"str": 5}, ["guardian"])
_weapon("Парные клинки",   "dual",     "D", 450, {"dex": 5}, ["dancer"])
_weapon("Стальные кастеты","cestus",   "D", 450, {"str": 5}, ["tyrant"])

# ---------- Оружие: C ----------
_weapon("Клинок рыцаря",   "sword_1h", "C", 3000, {"str": 10}, ["warrior", "knight"])
_weapon("Клинок берсерка", "sword_2h", "C", 4500, {"str": 14}, ["destroyer", "tyrant"])
_weapon("Клинок тени",     "dagger",   "C", 3000, {"dex": 10}, ["assassin", "archer"])
_weapon("Лук снайпера",    "bow",      "C", 3000, {"dex": 10}, ["archer"])
_weapon("Посох архимага",  "staff",    "C", 3000, {"int": 10}, ["mage", "necro", "bard", "overlord"])
_weapon("Копьё гнева",     "spear",    "C", 3500, {"str": 10}, ["guardian"])
_weapon("Клинки танца",    "dual",     "C", 3500, {"dex": 10}, ["dancer"])
_weapon("Кастеты ярости",  "cestus",   "C", 3500, {"str": 10}, ["tyrant"])

# ---------- Броня: Heavy ----------
_armor("Кожаный шлем",     "heavy", "helmet", "common", 30,  {"con": 1})
_armor("Тяжёлая куртка",   "heavy", "armor",  "common", 50,  {"con": 3})
_armor("Кожаные сапоги",   "heavy", "boots",  "common", 30,  {"con": 1})
_armor("Железный шлем",    "heavy", "helmet", "D", 250, {"con": 3})
_armor("Железная броня",   "heavy", "armor",  "D", 500, {"con": 7})
_armor("Железные сапоги",  "heavy", "boots",  "D", 300, {"con": 4})
_armor("Стальной шлем",    "heavy", "helmet", "C", 1500, {"con": 5})
_armor("Стальная броня",   "heavy", "armor",  "C", 3000, {"con": 12})
_armor("Стальные сапоги",  "heavy", "boots",  "C", 2000, {"con": 6})

# ---------- Броня: Light ----------
_armor("Тканевый капюшон", "light", "helmet", "common", 30,  {"dex": 1})
_armor("Тканевая куртка",  "light", "armor",  "common", 50,  {"dex": 3})
_armor("Тканевые туфли",   "light", "boots",  "common", 30,  {"dex": 1})
_armor("Кожаный капюшон",  "light", "helmet", "D", 250, {"dex": 3})
_armor("Лёгкая кожа",      "light", "armor",  "D", 500, {"dex": 7})
_armor("Лёгкие сапоги",    "light", "boots",  "D", 300, {"dex": 4})
_armor("Капюшон тени",     "light", "helmet", "C", 1500, {"dex": 5})
_armor("Куртка тени",      "light", "armor",  "C", 3000, {"dex": 12})
_armor("Сапоги тени",      "light", "boots",  "C", 2000, {"dex": 6})

# ---------- Броня: Robe ----------
_armor("Простой капюшон",  "robe", "helmet", "common", 30,  {"int": 1})
_armor("Простая мантия",   "robe", "armor",  "common", 50,  {"int": 3})
_armor("Простые туфли",    "robe", "boots",  "common", 30,  {"int": 1})
_armor("Капюшон ученика",  "robe", "helmet", "D", 250, {"int": 3})
_armor("Мантия ученика",   "robe", "armor",  "D", 500, {"int": 7})
_armor("Туфли ученика",    "robe", "boots",  "D", 300, {"int": 4})
_armor("Капюшон магистра", "robe", "helmet", "C", 1500, {"int": 5})
_armor("Мантия магистра",  "robe", "armor",  "C", 3000, {"int": 12})
_armor("Туфли магистра",   "robe", "boots",  "C", 2000, {"int": 6})

# ---------- Щиты ----------
_shield("Деревянный щит", "common", 50, {"con": 2})
_shield("Стальной щит",   "D", 400, {"con": 5})
_shield("Башенный щит",   "C", 3000, {"con": 10})

# ---------- Аксессуары (кольца) ----------
_accessory("Кольцо защиты",  "ring", "common", 100, {"men": 1})
_accessory("Кольцо магии",   "ring", "D", 500, {"men": 3})
_accessory("Кольцо мудрости", "ring", "C", 2000, {"men": 6})

# ---------- Зелья ----------
_potion("Зелье HP",  25, heal_hp=30)
_potion("Эликсир HP", 60, heal_hp=60)
_potion("Зелье MP",  25, heal_mp=40)
_potion("Эликсир MP", 60, heal_mp=70)


# ================= ХЕЛПЕРЫ =================
def get_armor_type(user_class):
    return CLASS_ARMOR_TYPE.get(user_class, "light")


def can_use_item(user_class, item_name):
    """Может ли класс использовать предмет. Сначала по типу, потом по classes."""
    data = SHOP.get(item_name)
    if not data:
        return False

    item_type = data.get("type")

    # Зелья — всем
    if item_type == "potion":
        return True
    # Аксессуары (кольца, амулеты) — всем
    if item_type == "accessory":
        return True
    # Оружие — по подтипу
    if item_type == "weapon":
        wtypes = CLASS_WEAPON_TYPES.get(user_class, [])
        return data.get("subtype") in wtypes
    # Броня — по типу
    if item_type == "armor":
        return data.get("armor_type") == get_armor_type(user_class)
    # Щит — только warrior / knight
    if item_type == "shield":
        return user_class in SHIELD_CLASSES

    # Прочее (не должно случиться) — по classes
    allowed = data.get("classes") or []
    if not allowed:
        return True
    return user_class in allowed


def get_available_shop(user_class, shop_mult=1.0, player_level=1, show_locked=False):
    """Список предметов, доступных классу. show_locked — показывать недоступные."""
    result = []
    for name, data in SHOP.items():
        if data["type"] == "potion":
            result.append((name, data, True))
            continue
        can_use = can_use_item(user_class, name)
        level_ok = player_level >= data.get("level_req", 1)
        if can_use or show_locked:
            result.append((name, data, can_use and level_ok))
    return result


def get_set_bonus(user):
    """Проверить сетовый бонус. Возвращает dict с бонусами или None."""
    eq = {
        "helmet": user.get("equipped_helmet", ""),
        "armor": user.get("equipped_armor", ""),
        "boots": user.get("equipped_boots", ""),
    }
    # Все три части должны быть
    if not all(eq.values()):
        return None
    # Получаем типы и грейды
    types = []
    grades = []
    for part in ("helmet", "armor", "boots"):
        raw = eq[part]
        # Убираем +N
        base = raw.split("+")[0] if "+" in raw else raw
        data = SHOP.get(base)
        if not data or data["type"] != "armor":
            return None
        types.append(data.get("armor_type"))
        grades.append(data.get("grade"))
    # Все три одного типа И одного грейда?
    if len(set(types)) != 1:
        return None
    if len(set(grades)) != 1:
        return None
    # Только common не даёт сет (нужен D или C)
    if grades[0] == "common":
        return None
    return SET_BONUSES.get(types[0])


def is_set_active(user):
    return get_set_bonus(user) is not None
