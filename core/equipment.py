"""Экипировка 3.0: 4 грейда, 8 слотов, большой выбор."""

# ================= ПРИВЯЗКА К КЛАССАМ =================
CLASS_ARMOR_TYPE = {
    "warrior": "heavy", "knight": "heavy", "destroyer": "heavy",
    "tyrant": "heavy", "guardian": "light", "archer": "light",
    "assassin": "light", "dancer": "light",
    "mage": "robe", "necro": "robe", "bard": "robe", "overlord": "robe",
    "keeper": "heavy",
}

CLASS_WEAPON_TYPES = {
    "warrior": ["sword_1h"], "knight": ["sword_1h"], "mage": ["staff"],
    "archer": ["bow", "dagger"], "guardian": ["spear"],
    "bard": ["staff"], "assassin": ["dagger"], "necro": ["staff"],
    "dancer": ["dual"], "destroyer": ["sword_2h"],
    "tyrant": ["sword_2h", "cestus"], "overlord": ["staff"],
    "keeper": ["sword_1h"],
}

SHIELD_CLASSES = ["warrior", "knight", "keeper"]

# ================= СЛОТЫ (8) =================
SLOTS = ["weapon", "helmet", "armor", "boots", "shield",
         "accessory", "ring", "earring"]
SLOT_NAMES = {
    "weapon": "🗡 Оружие", "helmet": "👑 Шлем", "armor": "🛡 Броня",
    "boots": "👢 Сапоги", "shield": "🛡 Щит", "accessory": "💍 Амулет",
    "ring": "💎 Кольцо", "earring": "💠 Серьга",
}

# ================= СЕТЫ =================
SET_BONUSES = {
    "heavy": {"hp_mult": 1.15, "pdef_mult": 1.10, "desc": "+15% HP, +10% P.Def"},
    "light": {"dex_bonus": 3, "crit_bonus": 5, "desc": "+3 DEX, +5% крит"},
    "robe":  {"mp_mult": 1.20, "mdef_mult": 1.15, "desc": "+20% MP, +15% M.Def"},
}

# ================= ГРЕЙДЫ (4) =================
GRADES = {
    "common": {"name": "Обычный", "level_req": 1, "mult": 1.0},
    "D":      {"name": "D", "level_req": 15, "mult": 1.5},
    "C":      {"name": "C", "level_req": 30, "mult": 2.2},
    "B":      {"name": "B", "level_req": 45, "mult": 3.2},
}


# ================= МАГАЗИН =================
SHOP = {}


def _w(name, subtype, grade, price, bonus, classes=None):
    SHOP[name] = {
        "type": "weapon", "slot": "weapon", "subtype": subtype,
        "grade": grade, "level_req": GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": classes or [],
    }


def _a(name, armor_type, part, grade, price, bonus):
    SHOP[name] = {
        "type": "armor", "slot": part, "armor_type": armor_type,
        "grade": grade, "level_req": GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": [],
    }


def _s(name, grade, price, bonus):
    SHOP[name] = {
        "type": "shield", "slot": "shield", "grade": grade,
        "level_req": GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": SHIELD_CLASSES,
    }


def _acc(name, slot, grade, price, bonus):
    SHOP[name] = {
        "type": "accessory", "slot": slot, "grade": grade,
        "level_req": GRADES[grade]["level_req"],
        "price": price, "bonus": bonus, "classes": [],
    }


def _p(name, price, heal_hp=0, heal_mp=0, level_req=1):
    SHOP[name] = {
        "type": "potion", "slot": "", "grade": "common",
        "level_req": level_req, "price": price, "bonus": {},
        "classes": [], "heal_hp": heal_hp, "heal_mp": heal_mp,
    }


# ---------- СТАРЫЕ ПРЕДМЕТЫ (совместимость) ----------
_w("Железный меч", "sword_1h", "common", 50, {"str": 2})
_w("Стальной меч", "sword_1h", "D", 250, {"str": 5})
_w("Клинок тьмы", "sword_1h", "C", 1200, {"str": 10, "dex": 2})
_w("Посох мага", "staff", "common", 200, {"int": 4})
_w("Лук охотника", "bow", "common", 200, {"dex": 4})

_a("Кожаная броня", "heavy", "armor", "common", 50, {"con": 2})
_a("Кольчуга", "heavy", "armor", "D", 300, {"con": 5})
_a("Мантия мага", "robe", "armor", "common", 250, {"int": 3, "wit": 2})
_a("Латы рыцаря", "heavy", "armor", "C", 1200, {"con": 10})

_acc("Амулет удачи", "accessory", "common", 150, {"men": 3})
_acc("Кольцо силы", "ring", "common", 200, {"str": 3})
_acc("Перстень мудрости", "ring", "common", 200, {"int": 3})
_acc("Кольцо ловкости", "ring", "common", 200, {"dex": 3})
_acc("Амулет мудреца", "accessory", "C", 800, {"int": 5, "wit": 3})


# ================= ОРУЖИЕ (4 грейда × 8 типов) =================
# sword_1h
_w("Короткий меч", "sword_1h", "common", 50, {"str": 2}, ["warrior","knight","keeper"])
_w("Длинный меч", "sword_1h", "D", 400, {"str": 5}, ["warrior","knight","keeper"])
_w("Клинок рыцаря", "sword_1h", "C", 3000, {"str": 10}, ["warrior","knight","keeper"])
_w("Клинок Судьбы легиона", "sword_1h", "B", 9000, {"str": 18}, ["warrior","knight","keeper"])

# sword_2h
_w("Тяжёлый топор", "sword_2h", "common", 80, {"str": 3}, ["destroyer","tyrant"])
_w("Боевой топор", "sword_2h", "D", 600, {"str": 7}, ["destroyer","tyrant"])
_w("Клинок берсерка", "sword_2h", "C", 4500, {"str": 14}, ["destroyer","tyrant"])
_w("Секира ярости", "sword_2h", "B", 12000, {"str": 22}, ["destroyer","tyrant"])

# dagger
_w("Ржавый кинжал", "dagger", "common", 50, {"dex": 2}, ["assassin","archer"])
_w("Кинжал убийцы", "dagger", "D", 400, {"dex": 5}, ["assassin","archer"])
_w("Клинок тени", "dagger", "C", 3000, {"dex": 10}, ["assassin","archer"])
_w("Кинжал пустоты", "dagger", "B", 9000, {"dex": 18}, ["assassin","archer"])

# bow
_w("Короткий лук", "bow", "common", 50, {"dex": 2}, ["archer"])
_w("Длинный лук", "bow", "D", 400, {"dex": 5}, ["archer"])
_w("Лук снайпера", "bow", "C", 3000, {"dex": 10}, ["archer"])
_w("Лук дракона", "bow", "B", 9000, {"dex": 18, "str": 5}, ["archer"])

# staff
_w("Деревянный посох", "staff", "common", 50, {"int": 2}, ["mage","necro","bard","overlord"])
_w("Крепкий посох", "staff", "D", 400, {"int": 5}, ["mage","necro","bard","overlord"])
_w("Посох архимага", "staff", "C", 3000, {"int": 10}, ["mage","necro","bard","overlord"])
_w("Посох бездны", "staff", "B", 9000, {"int": 18, "wit": 5}, ["mage","necro","bard","overlord"])

# spear
_w("Простое копьё", "spear", "common", 60, {"str": 2}, ["guardian"])
_w("Длинное копьё", "spear", "D", 450, {"str": 5}, ["guardian"])
_w("Копьё гнева", "spear", "C", 3500, {"str": 10}, ["guardian"])
_w("Копьё богов", "spear", "B", 10000, {"str": 18, "con": 5}, ["guardian"])

# dual
_w("Парные кинжалы", "dual", "common", 60, {"dex": 2}, ["dancer"])
_w("Парные клинки", "dual", "D", 450, {"dex": 5}, ["dancer"])
_w("Клинки танца", "dual", "C", 3500, {"dex": 10}, ["dancer"])
_w("Клинки вихря", "dual", "B", 10000, {"dex": 18, "str": 5}, ["dancer"])

# cestus
_w("Кожаные кастеты", "cestus", "common", 60, {"str": 2}, ["tyrant"])
_w("Стальные кастеты", "cestus", "D", 450, {"str": 5}, ["tyrant"])
_w("Кастеты ярости", "cestus", "C", 3500, {"str": 10}, ["tyrant"])
_w("Кастеты титана", "cestus", "B", 10000, {"str": 18}, ["tyrant"])


# ================= БРОНЯ =================
# Heavy
for grade, price_h, price_a, price_b, b in [
    ("common", 30, 50, 30, {"con": 1, "armor": 3, "boots": 1}),
    ("D", 250, 500, 300, {"con": 3, "armor": 7, "boots": 4}),
    ("C", 1500, 3000, 2000, {"con": 5, "armor": 12, "boots": 6}),
    ("B", 5000, 9000, 6000, {"con": 8, "armor": 18, "boots": 10}),
]:
    pass  # сделаем явно ниже

_a("Кожаный шлем", "heavy", "helmet", "common", 30, {"con": 1})
_a("Тяжёлая куртка", "heavy", "armor", "common", 50, {"con": 3})
_a("Кожаные сапоги", "heavy", "boots", "common", 30, {"con": 1})
_a("Железный шлем", "heavy", "helmet", "D", 250, {"con": 3})
_a("Железная броня", "heavy", "armor", "D", 500, {"con": 7})
_a("Железные сапоги", "heavy", "boots", "D", 300, {"con": 4})
_a("Стальной шлем", "heavy", "helmet", "C", 1500, {"con": 5})
_a("Стальная броня", "heavy", "armor", "C", 3000, {"con": 12})
_a("Стальные сапоги", "heavy", "boots", "C", 2000, {"con": 6})
_a("Латы дракона", "heavy", "helmet", "B", 5000, {"con": 8})
_a("Броня титана", "heavy", "armor", "B", 9000, {"con": 18})
_a("Сапоги титана", "heavy", "boots", "B", 6000, {"con": 10})

# Light
_a("Тканевый капюшон", "light", "helmet", "common", 30, {"dex": 1})
_a("Тканевая куртка", "light", "armor", "common", 50, {"dex": 3})
_a("Тканевые туфли", "light", "boots", "common", 30, {"dex": 1})
_a("Кожаный капюшон", "light", "helmet", "D", 250, {"dex": 3})
_a("Лёгкая кожа", "light", "armor", "D", 500, {"dex": 7})
_a("Лёгкие сапоги", "light", "boots", "D", 300, {"dex": 4})
_a("Капюшон тени", "light", "helmet", "C", 1500, {"dex": 5})
_a("Куртка тени", "light", "armor", "C", 3000, {"dex": 12})
_a("Сапоги тени", "light", "boots", "C", 2000, {"dex": 6})
_a("Капюшон ветра", "light", "helmet", "B", 5000, {"dex": 8})
_a("Куртка ветра", "light", "armor", "B", 9000, {"dex": 18})
_a("Сапоги ветра", "light", "boots", "B", 6000, {"dex": 10})

# Robe
_a("Простой капюшон", "robe", "helmet", "common", 30, {"int": 1})
_a("Простая мантия", "robe", "armor", "common", 50, {"int": 3})
_a("Простые туфли", "robe", "boots", "common", 30, {"int": 1})
_a("Капюшон ученика", "robe", "helmet", "D", 250, {"int": 3})
_a("Мантия ученика", "robe", "armor", "D", 500, {"int": 7})
_a("Туфли ученика", "robe", "boots", "D", 300, {"int": 4})
_a("Капюшон магистра", "robe", "helmet", "C", 1500, {"int": 5})
_a("Мантия магистра", "robe", "armor", "C", 3000, {"int": 12})
_a("Туфли магистра", "robe", "boots", "C", 2000, {"int": 6})
_a("Капюшон бездны", "robe", "helmet", "B", 5000, {"int": 8})
_a("Мантия бездны", "robe", "armor", "B", 9000, {"int": 18})
_a("Туфли бездны", "robe", "boots", "B", 6000, {"int": 10})


# ================= ЩИТЫ =================
_s("Деревянный щит", "common", 50, {"con": 2})
_s("Стальной щит", "D", 400, {"con": 5})
_s("Башенный щит", "C", 3000, {"con": 10})
_s("Щит дракона", "B", 9000, {"con": 18})


# ================= АКСЕССУАРЫ (8 слотов) =================
# Амулеты
_acc("Амулет удачи", "accessory", "common", 150, {"men": 3})
_acc("Амулет ученика", "accessory", "D", 600, {"men": 5})
_acc("Амулет мудреца", "accessory", "C", 800, {"int": 5, "wit": 3})
_acc("Амулет бездны", "accessory", "B", 4000, {"men": 10, "int": 8})

# Кольца
_acc("Кольцо силы", "ring", "common", 200, {"str": 3})
_acc("Кольцо ловкости", "ring", "common", 200, {"dex": 3})
_acc("Перстень мудрости", "ring", "common", 200, {"int": 3})
_acc("Кольцо защиты", "ring", "common", 100, {"men": 1})
_acc("Кольцо магии", "ring", "D", 500, {"men": 3})
_acc("Кольцо убийцы", "ring", "D", 500, {"str": 3, "dex": 3})
_acc("Кольцо мудрости", "ring", "C", 2000, {"men": 6})
_acc("Кольцо власти", "ring", "B", 7000, {"int": 10, "men": 10})

# Серьги
_acc("Серьга удачи", "earring", "common", 200, {"men": 3})
_acc("Серьга защиты", "earring", "D", 500, {"con": 3})
_acc("Серьга мага", "earring", "D", 500, {"int": 3})
_acc("Серьга мудрости", "earring", "C", 2000, {"men": 6})
_acc("Серьга вечности", "earring", "B", 7000, {"con": 12, "men": 8})


# ================= ЗЕЛЬЯ =================
_p("Зелье HP", 25, heal_hp=30)
_p("Эликсир HP", 60, heal_hp=60)
_p("Большой эликсир HP", 150, heal_hp=120, level_req=20)
_p("Зелье MP", 25, heal_mp=40)
_p("Эликсир MP", 60, heal_mp=70)
_p("Большой эликсир MP", 150, heal_mp=140, level_req=20)


# ================= ЭКСКЛЮЗИВНЫЕ ПРЕДМЕТЫ (только за Stars) =================
_w("Клинок Судьбы", "sword_1h", "C", 99999, {"str": 15}, ["warrior","knight"])
SHOP["Клинок Судьбы"]["premium"] = True
SHOP["Клинок Судьбы"]["extra"] = "крит +5%"
SHOP["Клинок Судьбы"]["crit_bonus"] = 5

_w("Лук Апокалипсиса", "bow", "C", 99999, {"dex": 15}, ["archer"])
SHOP["Лук Апокалипсиса"]["premium"] = True
SHOP["Лук Апокалипсиса"]["extra"] = "крит +8%"
SHOP["Лук Апокалипсиса"]["crit_bonus"] = 8

_a("Венец Владыки", "robe", "helmet", "C", 99999, {"int": 15})
SHOP["Венец Владыки"]["premium"] = True
SHOP["Венец Владыки"]["extra"] = "+30% золота"
SHOP["Венец Владыки"]["gold_mult"] = 1.30

_s("Эгида Богов", "C", 99999, {"con": 15})
SHOP["Эгида Богов"]["premium"] = True
SHOP["Эгида Богов"]["extra"] = "блок 15%"
SHOP["Эгида Богов"]["block_chance"] = 15


# ================= ХЕЛПЕРЫ =================
def get_armor_type(user_class):
    return CLASS_ARMOR_TYPE.get(user_class, "light")


def can_use_item(user_class, item_name):
    data = SHOP.get(item_name)
    if not data:
        return False
    it = data.get("type")
    if it == "potion": return True
    if it == "accessory": return True
    if it == "weapon":
        return data.get("subtype") in CLASS_WEAPON_TYPES.get(user_class, [])
    if it == "armor":
        return data.get("armor_type") == get_armor_type(user_class)
    if it == "shield":
        return user_class in SHIELD_CLASSES
    allowed = data.get("classes") or []
    if not allowed: return True
    return user_class in allowed


def get_set_bonus(user):
    eq = {}
    for part in ("helmet", "armor", "boots"):
        raw = user.get(f"equipped_{part}", "")
        if not raw: return None
        base = raw.split("+")[0] if "+" in raw else raw
        data = SHOP.get(base)
        if not data or data.get("type") != "armor": return None
        eq[part] = data
    types = [d.get("armor_type") for d in eq.values()]
    grades = [d.get("grade") for d in eq.values()]
    if len(set(types)) != 1 or len(set(grades)) != 1: return None
    if grades[0] == "common": return None
    return SET_BONUSES.get(types[0])
