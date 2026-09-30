"""Скилы: классовые + расовые. Прокачка через skill_points."""

# ================= КЛАССОВЫЕ СКИЛЫ =================
# Формат: код, название, req_level (с какого уровня доступен), mp_cost,
#         effect (damage / heal / buff_atk / buff_def / debuff / stun),
#         mult (множитель урона/лечения или процент для бафа),
#         desc (краткое описание)
CLASS_SKILLS = {
    # ---------- ЧЕЛОВЕК ----------
    "warrior": [
        {"code": "war_1", "name": "Мощный удар",   "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "war_2", "name": "Боевой клич",   "req_level": 3,  "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "war_3", "name": "Стойка",        "req_level": 5,  "mp_cost": 10, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона в раунде"},
        {"code": "war_4", "name": "Провокация",    "req_level": 7,  "mp_cost": 15, "effect": "debuff",   "mult": 0.70, "desc": "−30% атаки врага"},
        {"code": "war_5", "name": "Кровавый удар", "req_level": 10, "mp_cost": 30, "effect": "damage",   "mult": 3.0, "desc": "×3 урона + кровотечение"},
        {"code": "war_6", "name": "Ярость",        "req_level": 15, "mp_cost": 40, "effect": "damage",   "mult": 3.5, "desc": "×3.5 урона"},
    ],
    "knight": [
        {"code": "kni_1", "name": "Удар щитом",    "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 урона + оглушение"},
        {"code": "kni_2", "name": "Защита",        "req_level": 3,  "mp_cost": 20, "effect": "buff_def", "mult": 0.40, "desc": "−60% урона на 2 раунда"},
        {"code": "kni_3", "name": "Благословение", "req_level": 5,  "mp_cost": 25, "effect": "heal",     "mult": 0.25, "desc": "+25% HP"},
        {"code": "kni_4", "name": "Стойкость",     "req_level": 7,  "mp_cost": 30, "effect": "buff_def", "mult": 0.30, "desc": "−70% урона на 2 раунда"},
        {"code": "kni_5", "name": "Возмездие",     "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "kni_6", "name": "Оберег",        "req_level": 15, "mp_cost": 40, "effect": "buff_def", "mult": 0.10, "desc": "−90% урона на 1 раунд"},
    ],
    "mage": [
        {"code": "mag_1", "name": "Огненный шар",  "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "mag_2", "name": "Ледяная стрела","req_level": 3,  "mp_cost": 20, "effect": "debuff",   "mult": 0.80, "desc": "−20% атаки врага"},
        {"code": "mag_3", "name": "Магический щит","req_level": 5,  "mp_cost": 15, "effect": "buff_def", "mult": 0.60, "desc": "−40% урона на 3 раунда"},
        {"code": "mag_4", "name": "Цепь молний",   "req_level": 7,  "mp_cost": 25, "effect": "damage",   "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "mag_5", "name": "Меткий огонь",  "req_level": 10, "mp_cost": 30, "effect": "damage",   "mult": 3.0, "desc": "×3 маг. урона"},
        {"code": "mag_6", "name": "Адское пламя",  "req_level": 15, "mp_cost": 45, "effect": "damage",   "mult": 4.0, "desc": "×4 маг. урона + поджог"},
    ],
    # ---------- ЭЛЬФ ----------
    "archer": [
        {"code": "arc_1", "name": "Точный выстрел","req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "arc_2", "name": "Отравленная",   "req_level": 3,  "mp_cost": 20, "effect": "damage",   "mult": 1.8, "desc": "×1.8 + яд"},
        {"code": "arc_3", "name": "Двойной",       "req_level": 5,  "mp_cost": 25, "effect": "damage",   "mult": 2.0, "desc": "2 атаки по ×2"},
        {"code": "arc_4", "name": "Снайпер",       "req_level": 7,  "mp_cost": 30, "effect": "damage",   "mult": 3.0, "desc": "×3 урона"},
        {"code": "arc_5", "name": "Взрывная",      "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "arc_6", "name": "Ливень стрел",  "req_level": 15, "mp_cost": 45, "effect": "damage",   "mult": 3.5, "desc": "×3.5 урона"},
    ],
    "guardian": [
        {"code": "grd_1", "name": "Удар копьём",   "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 урона"},
        {"code": "grd_2", "name": "Стойка стража", "req_level": 3,  "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "grd_3", "name": "Лечение",       "req_level": 5,  "mp_cost": 25, "effect": "heal",     "mult": 0.30, "desc": "+30% HP"},
        {"code": "grd_4", "name": "Зеркало",       "req_level": 7,  "mp_cost": 30, "effect": "buff_def", "mult": 0.40, "desc": "−60% урона"},
        {"code": "grd_5", "name": "Оковы",         "req_level": 10, "mp_cost": 25, "effect": "debuff",   "mult": 0.60, "desc": "−40% атаки врага"},
        {"code": "grd_6", "name": "Гнев леса",     "req_level": 15, "mp_cost": 40, "effect": "damage",   "mult": 3.0, "desc": "×3 урона + лечение"},
    ],
    "bard": [
        {"code": "brd_1", "name": "Вдохновение",   "req_level": 1,  "mp_cost": 15, "effect": "buff_atk", "mult": 1.20, "desc": "+20% урона на 3 раунда"},
        {"code": "brd_2", "name": "Песня жизни",   "req_level": 3,  "mp_cost": 20, "effect": "heal",     "mult": 0.25, "desc": "+25% HP"},
        {"code": "brd_3", "name": "Гимн защиты",   "req_level": 5,  "mp_cost": 25, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 3 раунда"},
        {"code": "brd_4", "name": "Колыбельная",   "req_level": 7,  "mp_cost": 25, "effect": "stun",     "mult": 1.0, "desc": "Оглушение на 1 раунд"},
        {"code": "brd_5", "name": "Боевой марш",   "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "brd_6", "name": "Гимн жизни",    "req_level": 15, "mp_cost": 45, "effect": "heal",     "mult": 0.60, "desc": "+60% HP + очищение"},
    ],
    # ---------- ТЁМНЫЙ ЭЛЬФ ----------
    "assassin": [
        {"code": "asn_1", "name": "Внезапный удар","req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "asn_2", "name": "Удар в спину",  "req_level": 3,  "mp_cost": 20, "effect": "damage",   "mult": 2.8, "desc": "×2.8 урона"},
        {"code": "asn_3", "name": "Тень",          "req_level": 5,  "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "asn_4", "name": "Кровавый клинок","req_level": 7, "mp_cost": 25, "effect": "damage",   "mult": 2.5, "desc": "×2.5 + кровотечение"},
        {"code": "asn_5", "name": "Двойной клинок","req_level": 10, "mp_cost": 30, "effect": "damage",   "mult": 3.0, "desc": "×3 урона"},
        {"code": "asn_6", "name": "Смертельный",   "req_level": 15, "mp_cost": 45, "effect": "damage",   "mult": 4.0, "desc": "×4 урона"},
    ],
    "necro": [
        {"code": "nec_1", "name": "Тёмная стрела", "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "nec_2", "name": "Проклятие",     "req_level": 3,  "mp_cost": 20, "effect": "debuff",   "mult": 0.75, "desc": "−25% урона врага"},
        {"code": "nec_3", "name": "Похищение",     "req_level": 5,  "mp_cost": 25, "effect": "damage",   "mult": 1.5, "desc": "×1.5 урона + лечение 50%"},
        {"code": "nec_4", "name": "Ужас",          "req_level": 7,  "mp_cost": 25, "effect": "stun",     "mult": 1.0, "desc": "Оглушение на 1 раунд"},
        {"code": "nec_5", "name": "Чумной взрыв",  "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 2.5, "desc": "×2.5 + яд"},
        {"code": "nec_6", "name": "Армия тьмы",    "req_level": 15, "mp_cost": 50, "effect": "damage",   "mult": 3.5, "desc": "×3.5 маг. урона"},
    ],
    "dancer": [
        {"code": "dnc_1", "name": "Вихрь",         "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 урона"},
        {"code": "dnc_2", "name": "Двойное вращение","req_level": 3,"mp_cost": 20, "effect": "damage",   "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "dnc_3", "name": "Танец тени",    "req_level": 5,  "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "dnc_4", "name": "Режущий ветер", "req_level": 7,  "mp_cost": 25, "effect": "damage",   "mult": 2.5, "desc": "×2.5 + рана"},
        {"code": "dnc_5", "name": "Парный удар",   "req_level": 10, "mp_cost": 30, "effect": "damage",   "mult": 3.0, "desc": "×3 урона"},
        {"code": "dnc_6", "name": "Смертельный танец","req_level": 15,"mp_cost": 45, "effect": "damage","mult": 3.8, "desc": "×3.8 урона"},
    ],
    # ---------- ОРК ----------
    "destroyer": [
        {"code": "dst_1", "name": "Сокрушающий",   "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "dst_2", "name": "Ярость",        "req_level": 3,  "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "dst_3", "name": "Разрушение",    "req_level": 5,  "mp_cost": 25, "effect": "damage",   "mult": 3.0, "desc": "×3 урона"},
        {"code": "dst_4", "name": "Кровавая ярость","req_level": 7, "mp_cost": 25, "effect": "buff_atk", "mult": 1.50, "desc": "+50% урона на 2 раунда"},
        {"code": "dst_5", "name": "Землетрясение", "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 3.2, "desc": "×3.2 + оглушение"},
        {"code": "dst_6", "name": "Армагеддон",    "req_level": 15, "mp_cost": 50, "effect": "damage",   "mult": 4.5, "desc": "×4.5 урона"},
    ],
    "tyrant": [
        {"code": "tyr_1", "name": "Быстрый удар",  "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 урона"},
        {"code": "tyr_2", "name": "Серия ударов",  "req_level": 3,  "mp_cost": 20, "effect": "damage",   "mult": 2.3, "desc": "×2.3 урона"},
        {"code": "tyr_3", "name": "Кулак бури",    "req_level": 5,  "mp_cost": 25, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "tyr_4", "name": "Ускорение",     "req_level": 7,  "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "tyr_5", "name": "Смертельный",   "req_level": 10, "mp_cost": 35, "effect": "damage",   "mult": 3.5, "desc": "×3.5 урона"},
        {"code": "tyr_6", "name": "Ярость тигра",  "req_level": 15, "mp_cost": 45, "effect": "damage",   "mult": 4.0, "desc": "×4 урона"},
    ],
    "overlord": [
        {"code": "ovl_1", "name": "Тёмный удар",   "req_level": 1,  "mp_cost": 15, "effect": "damage",   "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "ovl_2", "name": "Печать",        "req_level": 3,  "mp_cost": 20, "effect": "debuff",   "mult": 0.70, "desc": "−30% урона врага"},
        {"code": "ovl_3", "name": "Забрать жизнь", "req_level": 5,  "mp_cost": 25, "effect": "damage",   "mult": 2.0, "desc": "×2 урона + лечение 50%"},
        {"code": "ovl_4", "name": "Война душ",     "req_level": 7,  "mp_cost": 30, "effect": "damage",   "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "ovl_5", "name": "Разлом",        "req_level": 10, "mp_cost": 40, "effect": "damage",   "mult": 3.0, "desc": "×3 маг. урона"},
        {"code": "ovl_6", "name": "Апокалипсис",   "req_level": 15, "mp_cost": 50, "effect": "damage",   "mult": 4.0, "desc": "×4 маг. урона"},
    ],
}

# ================= РАСОВЫЕ СКИЛЫ (1 на расу) =================
RACIAL_SKILLS = {
    # ---- Обычные расы ----
    "human": {
        "code": "rac_human", "name": "Воля", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.20,
        "desc": "Пассивно: +20% урона, когда HP < 30%",
    },
    "elf": {
        "code": "rac_elf", "name": "Глаз ястреба", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.15,
        "desc": "Пассивно: +15% шанс крита",
    },
    "dark_elf": {
        "code": "rac_dark", "name": "Тень", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.10,
        "desc": "Пассивно: +10% магического урона",
    },
    "orc": {
        "code": "rac_orc", "name": "Берсерк", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.15,
        "desc": "Пассивно: +15% max HP",
    },
    # ---- Премиум-расы ----
    "demon": {
        "code": "rac_demon", "name": "Адское пламя", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.15,
        "desc": "Пассивно: +15% магического урона",
    },
    "angel": {
        "code": "rac_angel", "name": "Небесный щит", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.20,
        "desc": "Пассивно: +20% силы лечения",
    },
    "prit": {
        "code": "rac_prit", "name": "Из тени", "req_level": 5, "mp_cost": 0,
        "effect": "passive", "mult": 0.15,
        "desc": "Пассивно: +15% крита, +10% золота",
    },
}


# ================= ХЕЛПЕРЫ =================
def available_skills(user):
    cls = user.get("class", "")
    race = user.get("race", "")
    lvl = user.get("level", 1)
    result = []
    for s in CLASS_SKILLS.get(cls, []):
        if s["req_level"] <= lvl:
            result.append({**s, "source": "class"})
    if race in RACIAL_SKILLS:
        s = RACIAL_SKILLS[race]
        if s["req_level"] <= lvl:
            result.append({**s, "source": "race"})
    return result


def get_skill(code):
    """Найти скил по коду."""
    for skills_list in CLASS_SKILLS.values():
        for s in skills_list:
            if s["code"] == code:
                return {**s, "source": "class"}
    for s in RACIAL_SKILLS.values():
        if s["code"] == code:
            return {**s, "source": "race"}
    return None


def skill_level(user, code):
    """Уровень скила у игрока (1-3). 1 — базовый."""
    import json
    try:
        learned = json.loads(user.get("learned_skills") or "{}")
    except Exception:
        learned = {}
    return int(learned.get(code, 1))


def skill_multiplier(user, code):
    """Множитель скила с учётом прокачки (+15% за уровень)."""
    s = get_skill(code)
    if not s:
        return 1.0
    lvl = skill_level(user, code)
    base = s.get("mult", 1.0)
    if s["effect"] == "damage":
        return base * (1 + (lvl - 1) * 0.15)
    return base
