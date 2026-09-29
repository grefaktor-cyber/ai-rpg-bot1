"""Предметы, экипировка, типы брони и грейды."""


# ================= ТИПЫ БРОНИ =================
ARMOR_TYPES = {
    "heavy": "Тяжёлая",
    "light": "Лёгкая",
    "robe":  "Мантия",
}


# ================= ГРЕЙДЫ =================
GRADES = {
    "common": {"name": "Обычный", "multiplier": 1.00, "level_req": 1},
    "d":      {"name": "D",       "multiplier": 1.30, "level_req": 20},
    "c":      {"name": "C",       "multiplier": 1.70, "level_req": 40},
}


# ================= СЛОТЫ ЭКИПИРОВКИ =================
SLOTS = ["weapon", "helmet", "armor", "boots", "shield", "amulet", "ring"]


# ================= КЛАССЫ → ТИП БРОНИ =================
CLASS_ARMOR = {
    "warrior": "heavy", "knight": "heavy", "destroyer": "heavy",
    "tyrant": "heavy", "defender": "heavy", "keeper": "heavy",
    "archer": "light", "assassin": "light", "dancer": "light",
    "hunter": "light", "guardian": "light", "prit": "light",
    "mage": "robe", "necro": "robe", "priest": "robe",
    "bard": "robe", "overlord": "robe",
}


# ================= КЛАССЫ → ТИП ОРУЖИЯ =================
CLASS_WEAPON = {
    "warrior": "sword_1h", "knight": "sword_1h", "defender": "sword_1h",
    "keeper": "sword_1h",
    "destroyer": "sword_2h", "tyrant": "fist",
    "archer": "bow", "hunter": "bow",
    "assassin": "dagger", "prit": "dagger",
    "dancer": "dual_blades",
    "mage": "staff", "necro": "staff", "priest": "staff",
    "bard": "staff", "overlord": "staff",
    "guardian": "spear",
}


# ================= КЛАССЫ, КОТОРЫЕ МОГУТ НОСИТЬ ЩИТ =================
CAN_USE_SHIELD = {"warrior", "knight", "defender", "keeper", "guardian"}


# ================= МАГАЗИН (No Grade) =================
SHOP_ITEMS = {
    # Оружие
    "Железный меч":     {"type": "weapon", "slot": "sword_1h", "price": 50,   "bonus": {"str": 3}},
    "Стальной меч":     {"type": "weapon", "slot": "sword_1h", "price": 250,  "bonus": {"str": 5}},
    "Двуручный меч":    {"type": "weapon", "slot": "sword_2h", "price": 300,  "bonus": {"str": 7}},
    "Кинжал":           {"type": "weapon", "slot": "dagger",   "price": 150,  "bonus": {"dex": 4}},
    "Короткий лук":     {"type": "weapon", "slot": "bow",      "price": 200,  "bonus": {"dex": 4}},
    "Посох ученика":    {"type": "weapon", "slot": "staff",    "price": 200,  "bonus": {"int": 4}},
    "Копьё":            {"type": "weapon", "slot": "spear",    "price": 280,  "bonus": {"str": 5, "con": 1}},
    "Парные клинки":    {"type": "weapon", "slot": "dual_blades", "price": 250, "bonus": {"str": 2, "dex": 3}},
    "Кастеты":          {"type": "weapon", "slot": "fist",     "price": 220,  "bonus": {"str": 3, "dex": 2}},

    # Броня Heavy
    "Кожаная броня":    {"type": "armor", "slot": "heavy", "price": 50,   "bonus": {"con": 2, "pdef": 3}},
    "Кольчуга":         {"type": "armor", "slot": "heavy", "price": 300,  "bonus": {"con": 5, "pdef": 6}},
    "Латы рыцаря":      {"type": "armor", "slot": "heavy", "price": 1200, "bonus": {"con": 10, "pdef": 10}},

    # Броня Light
    "Кожаный доспех":   {"type": "armor", "slot": "light", "price": 50,   "bonus": {"dex": 2, "pdef": 2}},
    "Броня следопыта":  {"type": "armor", "slot": "light", "price": 300,  "bonus": {"dex": 4, "pdef": 4}},

    # Броня Robe
    "Мантия ученика":   {"type": "armor", "slot": "robe",  "price": 50,   "bonus": {"int": 2, "mdef": 3}},
    "Мантия мага":      {"type": "armor", "slot": "robe",  "price": 250,  "bonus": {"int": 3, "wit": 2, "mdef": 5}},
    "Мантия архимага":  {"type": "armor", "slot": "robe",  "price": 1000, "bonus": {"int": 8, "wit": 4, "mdef": 10}},

    # Шлемы
    "Кожаный шлем":     {"type": "helmet", "slot": "helmet", "price": 40, "bonus": {"con": 1, "pdef": 1}},
    "Стальной шлем":    {"type": "helmet", "slot": "helmet", "price": 200, "bonus": {"con": 2, "pdef": 3}},

    # Сапоги
    "Кожаные сапоги":   {"type": "boots", "slot": "boots", "price": 40, "bonus": {"dex": 1}},
    "Стальные сапоги":  {"type": "boots", "slot": "boots", "price": 200, "bonus": {"con": 2, "pdef": 2}},

    # Щит
    "Деревянный щит":   {"type": "shield", "slot": "shield", "price": 60,  "bonus": {"pdef": 3, "block": 5}},
    "Стальной щит":     {"type": "shield", "slot": "shield", "price": 400, "bonus": {"pdef": 8, "block": 12}},

    # Аксессуары
    "Амулет удачи":     {"type": "amulet", "slot": "amulet", "price": 150, "bonus": {"men": 3, "mdef": 3}},
    "Кольцо силы":      {"type": "ring",   "slot": "ring",   "price": 200, "bonus": {"str": 3, "mdef": 2}},
    "Перстень мудрости":{"type": "ring",   "slot": "ring",   "price": 200, "bonus": {"int": 3, "mdef": 4}},
    "Кольцо ловкости":  {"type": "ring",   "slot": "ring",   "price": 200, "bonus": {"dex": 3, "mdef": 2}},
    "Амулет мудреца":   {"type": "amulet", "slot": "amulet", "price": 800, "bonus": {"int": 5, "wit": 3, "mdef": 6}},
}


# ================= РЕЦЕПТЫ КРАФТА (обычные → D) =================
CRAFT_RECIPES = {
    "Стальной меч":     {"base": "Железный меч",   "count": 3, "mat": "iron",    "mat_count": 5},
    "Кольчуга":         {"base": "Кожаная броня",  "count": 3, "mat": "leather", "mat_count": 5},
    "Латы рыцаря":      {"base": "Кольчуга",       "count": 2, "mat": "iron",    "mat_count": 15},
    "Мантия мага":      {"base": "Мантия ученика", "count": 3, "mat": "dust",    "mat_count": 5},
    "Мантия архимага":  {"base": "Мантия мага",    "count": 2, "mat": "crystal", "mat_count": 10},
    "Амулет мудреца":   {"base": "Амулет удачи",   "count": 2, "mat": "crystal", "mat_count": 5},
}


# ================= МАТЕРИАЛЫ =================
MATERIAL_NAMES = {
    "iron": "железо",
    "leather": "кожа",
    "dust": "магическая пыль",
    "crystal": "кристалл",
}


# ================= ПРОВЕРКИ =================
def can_equip(class_code, item_name):
    """Может ли класс носить этот предмет."""
    item = SHOP_ITEMS.get(item_name)
    if not item:
        return False, "Предмет не найден"

    item_type = item["type"]
    item_slot = item["slot"]

    # Оружие
    if item_type == "weapon":
        if CLASS_WEAPON.get(class_code) != item_slot:
            return False, f"Твой класс не может использовать {item_name}"
        return True, ""

    # Броня и шлемы
    if item_type in ("armor", "helmet"):
        armor_type = CLASS_ARMOR.get(class_code, "heavy")
        if item_slot != armor_type:
            return False, f"Твой класс носит {ARMOR_TYPES.get(armor_type, '?')}"
        return True, ""

    # Щит
    if item_type == "shield":
        if class_code not in CAN_USE_SHIELD:
            return False, "Твой класс не может носить щит"
        return True, ""

    # Аксессуары и сапоги — доступны всем
    return True, ""


def get_full_set_bonus(equipped):
    """Бонус за полный сет брони (helmet + armor + boots одного типа)."""
    if not equipped:
        return None
    helmet = equipped.get("helmet")
    armor = equipped.get("armor")
    boots = equipped.get("boots")
    if not (helmet and armor and boots):
        return None

    h = SHOP_ITEMS.get(helmet, {})
    a = SHOP_ITEMS.get(armor, {})
    b = SHOP_ITEMS.get(boots, {})

    if h.get("slot") == a.get("slot") == b.get("slot") == "heavy":
        return {"hp_pct": 0.15, "pdef_pct": 0.10, "name": "Heavy Set"}
    if h.get("slot") == a.get("slot") == b.get("slot") == "light":
        return {"dex_pct": 0.10, "evasion_pct": 0.10, "name": "Light Set"}
    if h.get("slot") == a.get("slot") == b.get("slot") == "robe":
        return {"mp_pct": 0.20, "mdef_pct": 0.15, "name": "Robe Set"}
    return None
