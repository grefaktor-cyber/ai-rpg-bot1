"""Книги скиллов — выпадают с боссов."""

# Скрытые скиллы (source: book) — по 2 на класс
# skill_code — должен совпадать с кодом в core/skills.py
SKILL_BOOKS = {
    # Воин
    "war_7": {"name": "📖 Кровавый удар", "class": "warrior",
              "drop_boss": ["Древень", "Лич-хранитель"], "chance": 0.05},
    "war_8": {"name": "📖 Ярость берсерка", "class": "warrior",
              "drop_boss": ["Ледяной Великан"], "chance": 0.04},
    # Рыцарь
    "kni_7": {"name": "📖 Несокрушимость", "class": "knight",
              "drop_boss": ["Лич-хранитель", "Ледяной Великан"], "chance": 0.05},
    "kni_8": {"name": "📖 Возмездие", "class": "knight",
              "drop_boss": ["Король Духов"], "chance": 0.04},
    # Маг
    "mag_7": {"name": "📖 Метеор", "class": "mage",
              "drop_boss": ["Ледяной Великан"], "chance": 0.05},
    "mag_8": {"name": "📖 Проклятие бездны", "class": "mage",
              "drop_boss": ["Древний дракон"], "chance": 0.03},
    # Лучник
    "arc_7": {"name": "📖 Град стрел", "class": "archer",
              "drop_boss": ["Древень", "Король Духов"], "chance": 0.05},
    "arc_8": {"name": "📖 Снайперский выстрел", "class": "archer",
              "drop_boss": ["Дракон Ксарг"], "chance": 0.04},
    # Страж
    "grd_7": {"name": "📖 Несокрушимая защита", "class": "guardian",
              "drop_boss": ["Лич-хранитель"], "chance": 0.05},
    "grd_8": {"name": "📖 Гнев природы", "class": "guardian",
              "drop_boss": ["Древень"], "chance": 0.04},
    # Певчий
    "brd_7": {"name": "📖 Гимн победы", "class": "bard",
              "drop_boss": ["Ледяной Великан"], "chance": 0.05},
    "brd_8": {"name": "📖 Песнь вечности", "class": "bard",
              "drop_boss": ["Король Духов"], "chance": 0.04},
    # Убийца
    "asn_7": {"name": "📖 Казнь", "class": "assassin",
              "drop_boss": ["Лич-хранитель", "Древний дракон"], "chance": 0.05},
    "asn_8": {"name": "📖 Танец теней", "class": "assassin",
              "drop_boss": ["Король Духов"], "chance": 0.04},
    # Некромант
    "nec_7": {"name": "📖 Смертельный холод", "class": "necro",
              "drop_boss": ["Ледяной Великан"], "chance": 0.05},
    "nec_8": {"name": "📖 Армия мёртвых", "class": "necro",
              "drop_boss": ["Древний дракон"], "chance": 0.03},
    # Танцор
    "dnc_7": {"name": "📖 Смертельное вращение", "class": "dancer",
              "drop_boss": ["Лич-хранитель"], "chance": 0.05},
    "dnc_8": {"name": "📖 Вихрь клинков", "class": "dancer",
              "drop_boss": ["Король Духов"], "chance": 0.04},
    # Разрушитель
    "dst_7": {"name": "📖 Армагеддон", "class": "destroyer",
              "drop_boss": ["Древень", "Ледяной Великан"], "chance": 0.05},
    "dst_8": {"name": "📖 Разрушение миров", "class": "destroyer",
              "drop_boss": ["Древний дракон"], "chance": 0.03},
    # Тиранин
    "tyr_7": {"name": "📖 Серия смерти", "class": "tyrant",
              "drop_boss": ["Ледяной Великан"], "chance": 0.05},
    "tyr_8": {"name": "📖 Кулак дракона", "class": "tyrant",
              "drop_boss": ["Дракон Ксарг"], "chance": 0.04},
    # Владыка
    "ovl_7": {"name": "📖 Печать смерти", "class": "overlord",
              "drop_boss": ["Лич-хранитель"], "chance": 0.05},
    "ovl_8": {"name": "📖 Апокалипсис", "class": "overlord",
              "drop_boss": ["Древний дракон"], "chance": 0.03},
    # Хранитель
    "kp_7": {"name": "📖 Божественный щит", "class": "keeper",
             "drop_boss": ["Король Духов"], "chance": 0.05},
    "kp_8": {"name": "📖 Массовое воскрешение", "class": "keeper",
             "drop_boss": ["Древний дракон"], "chance": 0.03},
}


def get_book_for_skill(skill_code):
    return SKILL_BOOKS.get(skill_code)


def get_book_name(skill_code):
    b = SKILL_BOOKS.get(skill_code)
    return b["name"] if b else None
