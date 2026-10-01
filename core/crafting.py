"""Крафт: рецепты, шансы, редкие материалы."""

# Формат: результат → {base_item, materials, rare_materials, chance, grade, source}
RECIPES = {
    # ===== D-грейд (средние) =====
    "Длинный меч": {
        "base": "Короткий меч", "count_base": 2,
        "materials": {"iron": 10}, "rare": {}, "chance": 1.0,
        "grade": "D",
    },
    "Кинжал убийцы": {
        "base": "Ржавый кинжал", "count_base": 2,
        "materials": {"iron": 8, "leather": 5}, "rare": {}, "chance": 1.0,
        "grade": "D",
    },
    "Длинный лук": {
        "base": "Короткий лук", "count_base": 2,
        "materials": {"leather": 8, "dust": 5}, "rare": {}, "chance": 1.0,
        "grade": "D",
    },
    "Крепкий посох": {
        "base": "Деревянный посох", "count_base": 2,
        "materials": {"dust": 10}, "rare": {}, "chance": 1.0,
        "grade": "D",
    },
    # ===== C-грейд (топ-предметы) =====
    "Клинок тьмы+5": {
        "base": "Стальной меч", "count_base": 2,
        "materials": {"crystal": 15, "iron": 10}, "rare": {"ancient_crystal": 2},
        "chance": 0.75, "grade": "C",
    },
    "Клинок рыцаря+3": {
        "base": "Длинный меч", "count_base": 2,
        "materials": {"crystal": 12, "iron": 15}, "rare": {"ancient_crystal": 1},
        "chance": 0.75, "grade": "C",
    },
    "Мантия магистра+3": {
        "base": "Мантия ученика", "count_base": 2,
        "materials": {"crystal": 12, "dust": 15}, "rare": {"ancient_crystal": 1},
        "chance": 0.75, "grade": "C",
    },
    "Латы рыцаря+3": {
        "base": "Железная броня", "count_base": 2,
        "materials": {"iron": 20, "crystal": 8}, "rare": {"ancient_crystal": 2},
        "chance": 0.75, "grade": "C",
    },
    # ===== B-грейд (легендарные) =====
    "Броня титана+3": {
        "base": "Стальная броня", "count_base": 2,
        "materials": {"crystal": 30, "iron": 30}, "rare": {"titan_heart": 3},
        "chance": 0.60, "grade": "B",
    },
    "Латы дракона+3": {
        "base": "Стальной шлем", "count_base": 2,
        "materials": {"crystal": 25, "iron": 20}, "rare": {"dragon_scale": 3},
        "chance": 0.60, "grade": "B",
    },
    "Кинжал пустоты+5": {
        "base": "Клинок тени", "count_base": 2,
        "materials": {"crystal": 30, "dust": 20}, "rare": {"void_essence": 2},
        "chance": 0.55, "grade": "B",
    },
    "Посох бездны+3": {
        "base": "Посох архимага", "count_base": 2,
        "materials": {"crystal": 30, "dust": 25}, "rare": {"void_essence": 3},
        "chance": 0.55, "grade": "B",
    },
    "Щит дракона+3": {
        "base": "Башенный щит", "count_base": 1,
        "materials": {"crystal": 20, "iron": 25}, "rare": {"dragon_scale": 2},
        "chance": 0.60, "grade": "B",
    },
    "Копьё богов+5": {
        "base": "Копьё гнева", "count_base": 2,
        "materials": {"crystal": 30, "iron": 30}, "rare": {"dragon_scale": 2, "titan_heart": 2},
        "chance": 0.50, "grade": "B",
    },
    "Кастеты титана+5": {
        "base": "Кастеты ярости", "count_base": 2,
        "materials": {"crystal": 25, "iron": 25}, "rare": {"titan_heart": 3},
        "chance": 0.50, "grade": "B",
    },
    "Клинки вихря+5": {
        "base": "Клинки танца", "count_base": 2,
        "materials": {"crystal": 25, "dust": 20}, "rare": {"void_essence": 2},
        "chance": 0.50, "grade": "B",
    },
    "Лук дракона+5": {
        "base": "Лук снайпера", "count_base": 2,
        "materials": {"crystal": 25, "leather": 20}, "rare": {"dragon_scale": 3},
        "chance": 0.55, "grade": "B",
    },
}


def get_recipe(result_name):
    return RECIPES.get(result_name)
