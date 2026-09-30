"""Титулы: по уровню + за заслуги. Награды за достижения."""

# ================= ТИТУЛЫ =================
# Формат: code: {name, icon, unlock (условие), desc}
TITLES = {
    # ---- По уровню ----
    "novice":    {"name": "Новичок",   "icon": "🌟", "req_level": 3,
                  "desc": "Достигни 3 уровня"},
    "seeker":    {"name": "Искатель",  "icon": "🗺", "req_level": 5,
                  "desc": "Достигни 5 уровня"},
    "warrior":   {"name": "Воин",      "icon": "⚔️", "req_level": 10,
                  "desc": "Достигни 10 уровня"},
    "veteran":   {"name": "Ветеран",   "icon": "👑", "req_level": 15,
                  "desc": "Достигни 15 уровня"},
    "master":    {"name": "Мастер",    "icon": "🔥", "req_level": 20,
                  "desc": "Достигни 20 уровня"},
    "legend":    {"name": "Легенда",   "icon": "💎", "req_level": 30,
                  "desc": "Достигни 30 уровня"},

    # ---- За заслуги ----
    "student":   {"name": "Ученик",    "icon": "🎓", "achievement": "tutorial_done",
                  "desc": "Пройди обучение"},
    "duelist":   {"name": "Дуэлянт",   "icon": "🗡", "achievement": "arena_king",
                  "desc": "Выиграй 5 дуэлей"},
    "boss_hunter":{"name": "Убийца боссов","icon": "🐉","achievement": "boss_5",
                  "desc": "Победи 5 боссов"},
    "founder":   {"name": "Основатель", "icon": "🏛", "achievement": "guild_founder",
                  "desc": "Создай гильдию"},
    "conqueror": {"name": "Захватчик",  "icon": "🏴", "achievement": "conqueror",
                  "desc": "Захвати локацию"},
}

# Цвета для отображения (просто визуально)
TITLE_COLORS = {
    "novice": "🟢", "seeker": "🟢", "warrior": "🟡", "veteran": "🟡",
    "master": "🟠", "legend": "🔴", "student": "🟢", "duelist": "🟡",
    "boss_hunter": "🔴", "founder": "🟠", "conqueror": "🟠",
}


# ================= НАГРАДЫ ЗА ДОСТИЖЕНИЯ =================
# code: (gold, xp)
ACHIEVEMENT_REWARDS = {
    "first_step":  (50,   20),
    "explorer_5":  (100,  50),
    "explorer_10": (200, 100),
    "explorer_all":(500, 300),
    "collector_5": (80,   40),
    "level_5":     (100,  50),
    "level_10":    (300, 150),
    "level_20":    (800, 400),
    "first_boss":  (200, 100),
    "boss_5":      (500, 250),
    "referral_3":  (200, 100),
    "daily_7":     (150,  80),
    "rich":        (100,  50),
    "equipped":    (50,   20),
    "survivor":    (30,   10),
    "first_blood": (50,   20),
    "duelist":     (100,  50),
    "arena_king":  (300, 150),
    "coward":      (0,     0),
    "graffiti":    (30,   15),
    "social":      (50,   20),
    "pet_owner":   (50,   20),
    "pet_10":      (200, 100),
    "dungeon_1":   (100,  50),
    "dungeon_5":   (500, 300),
    "crafter":     (100,  50),
    "upgrader":    (100,  50),
    "guild_founder":(200, 100),
    "guild_member":(50,   20),
    "conqueror":   (300, 150),
    "event_hunter":(100,  50),
    "quest_master":(300, 200),
    "tutorial_done":(0,    0),  # Награда выдаётся отдельно в tut_finish
}


# ================= ХЕЛПЕРЫ =================
def get_available_titles(user, achievements_codes):
    """Какие титулы открыты у игрока."""
    unlocked = []
    for code, data in TITLES.items():
        if "req_level" in data and user.get("level", 1) >= data["req_level"]:
            unlocked.append(code)
        elif "achievement" in data and data["achievement"] in achievements_codes:
            unlocked.append(code)
    return unlocked


def get_title_data(code):
    return TITLES.get(code)


def format_active_title(user):
    """Форматировать активный титул для отображения. Возвращает строку."""
    code = user.get("active_title", "")
    if not code:
        return ""
    data = TITLES.get(code)
    if not data:
        return ""
    return f"{data['icon']} {data['name']}"
