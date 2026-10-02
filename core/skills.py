"""Скилы: классовые + расовые + скрытые (из книг). Улучшение до 5 уровня."""

# Максимальный уровень скилла
MAX_SKILL_LEVEL = 5
# Сколько очков умений стоит 1 улучшение
UPGRADE_COST = 1
# Прирост урона/хила за уровень (+15% за каждый уровень)
UPGRADE_DMG_BONUS = 0.15
# Прирост снижения урона за уровень для buff_def
UPGRADE_DEF_BONUS = 0.10


CLASS_SKILLS = {
    "warrior": [
        {"code": "war_1", "name": "Мощный удар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "war_2", "name": "Боевой клич", "req_level": 3, "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "war_3", "name": "Стойка", "req_level": 5, "mp_cost": 10, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона в раунде"},
        {"code": "war_4", "name": "Провокация", "req_level": 7, "mp_cost": 15, "effect": "debuff", "mult": 0.70, "desc": "−30% атаки врага"},
        {"code": "war_5", "name": "Кровавый удар", "req_level": 10, "mp_cost": 30, "effect": "damage", "mult": 3.0, "desc": "×3 урона + кровотечение"},
        {"code": "war_6", "name": "Ярость", "req_level": 15, "mp_cost": 40, "effect": "damage", "mult": 3.5, "desc": "×3.5 урона"},
        {"code": "war_7", "name": "Кровавый удар II", "req_level": 20, "mp_cost": 35, "effect": "damage", "mult": 4.5, "desc": "×4.5 урона", "source": "book"},
        {"code": "war_8", "name": "Ярость берсерка", "req_level": 25, "mp_cost": 50, "effect": "buff_atk", "mult": 1.80, "desc": "+80% урона на 2 раунда", "source": "book"},
    ],
    "knight": [
        {"code": "kni_1", "name": "Удар щитом", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 урона + оглушение"},
        {"code": "kni_2", "name": "Защита", "req_level": 3, "mp_cost": 20, "effect": "buff_def", "mult": 0.40, "desc": "−60% урона на 2 раунда"},
        {"code": "kni_3", "name": "Благословение", "req_level": 5, "mp_cost": 25, "effect": "heal", "mult": 0.25, "desc": "+25% HP"},
        {"code": "kni_4", "name": "Стойкость", "req_level": 7, "mp_cost": 30, "effect": "buff_def", "mult": 0.30, "desc": "−70% урона на 2 раунда"},
        {"code": "kni_5", "name": "Возмездие", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "kni_6", "name": "Оберег", "req_level": 15, "mp_cost": 40, "effect": "buff_def", "mult": 0.10, "desc": "−90% урона на 1 раунд"},
        {"code": "kni_7", "name": "Несокрушимость", "req_level": 20, "mp_cost": 45, "effect": "buff_def", "mult": 0.05, "desc": "−95% урона на 1 раунд", "source": "book"},
        {"code": "kni_8", "name": "Возмездие II", "req_level": 25, "mp_cost": 50, "effect": "damage", "mult": 4.0, "desc": "×4 урона", "source": "book"},
    ],
    "mage": [
        {"code": "mag_1", "name": "Огненный шар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "mag_2", "name": "Ледяная стрела", "req_level": 3, "mp_cost": 20, "effect": "debuff", "mult": 0.80, "desc": "−20% атаки врага"},
        {"code": "mag_3", "name": "Магический щит", "req_level": 5, "mp_cost": 15, "effect": "buff_def", "mult": 0.60, "desc": "−40% урона на 3 раунда"},
        {"code": "mag_4", "name": "Цепь молний", "req_level": 7, "mp_cost": 25, "effect": "damage", "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "mag_5", "name": "Меткий огонь", "req_level": 10, "mp_cost": 30, "effect": "damage", "mult": 3.0, "desc": "×3 маг. урона"},
        {"code": "mag_6", "name": "Адское пламя", "req_level": 15, "mp_cost": 45, "effect": "damage", "mult": 4.0, "desc": "×4 маг. урона"},
        {"code": "mag_7", "name": "Метеор", "req_level": 20, "mp_cost": 55, "effect": "damage", "mult": 5.0, "desc": "×5 маг. урона", "source": "book"},
        {"code": "mag_8", "name": "Проклятие бездны", "req_level": 25, "mp_cost": 60, "effect": "damage", "mult": 6.0, "desc": "×6 маг. урона", "source": "book"},
    ],
    "archer": [
        {"code": "arc_1", "name": "Точный выстрел", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "arc_2", "name": "Отравленная стрела", "req_level": 3, "mp_cost": 20, "effect": "damage", "mult": 1.8, "desc": "×1.8 + яд"},
        {"code": "arc_3", "name": "Двойной выстрел", "req_level": 5, "mp_cost": 25, "effect": "damage", "mult": 1.6, "double": True, "desc": "2 выстрела по ×1.6"},
        {"code": "arc_4", "name": "Снайпер", "req_level": 7, "mp_cost": 30, "effect": "damage", "mult": 2.0, "pierce": True, "desc": "×2, игнорирует броню"},
        {"code": "arc_5", "name": "Взрывная стрела", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "arc_6", "name": "Ливень стрел", "req_level": 15, "mp_cost": 45, "effect": "damage", "mult": 3.5, "desc": "×3.5 урона"},
        {"code": "arc_7", "name": "Град стрел", "req_level": 20, "mp_cost": 50, "effect": "damage", "mult": 4.5, "desc": "×4.5 урона", "source": "book"},
        {"code": "arc_8", "name": "Снайперский выстрел", "req_level": 25, "mp_cost": 60, "effect": "damage", "mult": 3.5, "pierce": True, "desc": "×3.5, игнор брони", "source": "book"},
    ],
    "guardian": [
        {"code": "grd_1", "name": "Удар копьём", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 урона"},
        {"code": "grd_2", "name": "Стойка стража", "req_level": 3, "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "grd_3", "name": "Лечение", "req_level": 5, "mp_cost": 25, "effect": "heal", "mult": 0.30, "desc": "+30% HP"},
        {"code": "grd_4", "name": "Зеркало", "req_level": 7, "mp_cost": 30, "effect": "buff_def", "mult": 0.40, "desc": "−60% урона"},
        {"code": "grd_5", "name": "Оковы", "req_level": 10, "mp_cost": 25, "effect": "debuff", "mult": 0.60, "desc": "−40% атаки врага"},
        {"code": "grd_6", "name": "Гнев леса", "req_level": 15, "mp_cost": 40, "effect": "damage", "mult": 3.0, "desc": "×3 урона + лечение"},
        {"code": "grd_7", "name": "Несокрушимая защита", "req_level": 20, "mp_cost": 45, "effect": "buff_def", "mult": 0.10, "desc": "−90% урона на 1 раунд", "source": "book"},
        {"code": "grd_8", "name": "Гнев природы", "req_level": 25, "mp_cost": 50, "effect": "damage", "mult": 4.0, "desc": "×4 урона + лечение", "source": "book"},
    ],
    "bard": [
        {"code": "brd_1", "name": "Вдохновение", "req_level": 1, "mp_cost": 15, "effect": "buff_atk", "mult": 1.20, "desc": "+20% урона на 3 раунда"},
        {"code": "brd_2", "name": "Песня жизни", "req_level": 3, "mp_cost": 20, "effect": "heal", "mult": 0.25, "desc": "+25% HP"},
        {"code": "brd_3", "name": "Гимн защиты", "req_level": 5, "mp_cost": 25, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 3 раунда"},
        {"code": "brd_4", "name": "Колыбельная", "req_level": 7, "mp_cost": 25, "effect": "stun", "mult": 1.0, "desc": "Оглушение на 1 раунд"},
        {"code": "brd_5", "name": "Боевой марш", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "brd_6", "name": "Гимн жизни", "req_level": 15, "mp_cost": 45, "effect": "heal", "mult": 0.60, "desc": "+60% HP + очищение"},
        {"code": "brd_7", "name": "Гимн победы", "req_level": 20, "mp_cost": 50, "effect": "buff_atk", "mult": 1.50, "desc": "+50% урона на 3 раунда", "source": "book"},
        {"code": "brd_8", "name": "Песнь вечности", "req_level": 25, "mp_cost": 60, "effect": "heal", "mult": 0.90, "desc": "+90% HP", "source": "book"},
    ],
    "assassin": [
        {"code": "asn_1", "name": "Внезапный удар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.2, "desc": "×2.2 урона"},
        {"code": "asn_2", "name": "Удар в спину", "req_level": 3, "mp_cost": 20, "effect": "damage", "mult": 2.8, "desc": "×2.8 урона"},
        {"code": "asn_3", "name": "Тень", "req_level": 5, "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "asn_4", "name": "Кровавый клинок", "req_level": 7, "mp_cost": 25, "effect": "damage", "mult": 2.5, "desc": "×2.5 + кровотечение"},
        {"code": "asn_5", "name": "Двойной клинок", "req_level": 10, "mp_cost": 30, "effect": "damage", "mult": 3.0, "desc": "×3 урона"},
        {"code": "asn_6", "name": "Смертельный удар", "req_level": 15, "mp_cost": 45, "effect": "damage", "mult": 4.0, "desc": "×4 урона"},
        {"code": "asn_7", "name": "Казнь", "req_level": 20, "mp_cost": 50, "effect": "damage", "mult": 3.5, "execute": 2.0, "desc": "×3.5 (×7 при HP врага < 20%)", "source": "book"},
        {"code": "asn_8", "name": "Танец теней", "req_level": 25, "mp_cost": 55, "effect": "damage", "mult": 6.0, "desc": "×6 урона", "source": "book"},
    ],
    "necro": [
        {"code": "nec_1", "name": "Тёмная стрела", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "nec_2", "name": "Проклятие", "req_level": 3, "mp_cost": 20, "effect": "debuff", "mult": 0.75, "desc": "−25% урона врага"},
        {"code": "nec_3", "name": "Похищение", "req_level": 5, "mp_cost": 25, "effect": "damage", "mult": 1.5, "lifesteal": 0.5, "desc": "×1.5 + лечение 50%"},
        {"code": "nec_4", "name": "Ужас", "req_level": 7, "mp_cost": 25, "effect": "stun", "mult": 1.0, "desc": "Оглушение на 1 раунд"},
        {"code": "nec_5", "name": "Чумной взрыв", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 2.5, "desc": "×2.5 + яд"},
        {"code": "nec_6", "name": "Армия тьмы", "req_level": 15, "mp_cost": 50, "effect": "damage", "mult": 3.5, "lifesteal": 0.3, "desc": "×3.5 маг. урона + вампиризм 30%"},
        {"code": "nec_7", "name": "Смертельный холод", "req_level": 20, "mp_cost": 55, "effect": "damage", "mult": 4.5, "desc": "×4.5 маг. урона", "source": "book"},
        {"code": "nec_8", "name": "Армия мёртвых", "req_level": 25, "mp_cost": 65, "effect": "damage", "mult": 4.5, "lifesteal": 0.4, "desc": "×4.5 + вампиризм 40%", "source": "book"},
    ],
    "dancer": [
        {"code": "dnc_1", "name": "Вихрь", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 урона"},
        {"code": "dnc_2", "name": "Двойное вращение", "req_level": 3, "mp_cost": 20, "effect": "damage", "mult": 1.4, "double": True, "desc": "2 удара по ×1.4"},
        {"code": "dnc_3", "name": "Танец тени", "req_level": 5, "mp_cost": 20, "effect": "buff_def", "mult": 0.50, "desc": "−50% урона на 2 раунда"},
        {"code": "dnc_4", "name": "Режущий ветер", "req_level": 7, "mp_cost": 25, "effect": "damage", "mult": 2.5, "desc": "×2.5 + рана"},
        {"code": "dnc_5", "name": "Парный удар", "req_level": 10, "mp_cost": 30, "effect": "damage", "mult": 3.0, "desc": "×3 урона"},
        {"code": "dnc_6", "name": "Смертельный танец", "req_level": 15, "mp_cost": 45, "effect": "damage", "mult": 3.8, "desc": "×3.8 урона"},
        {"code": "dnc_7", "name": "Смертельное вращение", "req_level": 20, "mp_cost": 50, "effect": "damage", "mult": 4.8, "desc": "×4.8 урона", "source": "book"},
        {"code": "dnc_8", "name": "Вихрь клинков", "req_level": 25, "mp_cost": 60, "effect": "damage", "mult": 5.8, "desc": "×5.8 урона", "source": "book"},
    ],
    "destroyer": [
        {"code": "dst_1", "name": "Сокрушающий удар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "dst_2", "name": "Ярость", "req_level": 3, "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "dst_3", "name": "Разрушение", "req_level": 5, "mp_cost": 25, "effect": "damage", "mult": 3.0, "desc": "×3 урона"},
        {"code": "dst_4", "name": "Кровавая ярость", "req_level": 7, "mp_cost": 25, "effect": "buff_atk", "mult": 1.50, "desc": "+50% урона на 2 раунда"},
        {"code": "dst_5", "name": "Землетрясение", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 3.2, "desc": "×3.2 + оглушение"},
        {"code": "dst_6", "name": "Армагеддон", "req_level": 15, "mp_cost": 50, "effect": "damage", "mult": 4.5, "desc": "×4.5 урона"},
        {"code": "dst_7", "name": "Армагеддон II", "req_level": 20, "mp_cost": 55, "effect": "damage", "mult": 5.5, "desc": "×5.5 урона", "source": "book"},
        {"code": "dst_8", "name": "Разрушение миров", "req_level": 25, "mp_cost": 70, "effect": "damage", "mult": 5.0, "execute": 2.0, "desc": "×5 (×10 при HP врага < 20%)", "source": "book"},
    ],
    "tyrant": [
        {"code": "tyr_1", "name": "Быстрый удар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 урона"},
        {"code": "tyr_2", "name": "Серия ударов", "req_level": 3, "mp_cost": 20, "effect": "damage", "mult": 1.4, "double": True, "desc": "2 удара по ×1.4"},
        {"code": "tyr_3", "name": "Кулак бури", "req_level": 5, "mp_cost": 25, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "tyr_4", "name": "Ускорение", "req_level": 7, "mp_cost": 20, "effect": "buff_atk", "mult": 1.30, "desc": "+30% урона на 3 раунда"},
        {"code": "tyr_5", "name": "Смертельный удар", "req_level": 10, "mp_cost": 35, "effect": "damage", "mult": 3.5, "desc": "×3.5 урона"},
        {"code": "tyr_6", "name": "Ярость тигра", "req_level": 15, "mp_cost": 45, "effect": "damage", "mult": 4.0, "desc": "×4 урона"},
        {"code": "tyr_7", "name": "Серия смерти", "req_level": 20, "mp_cost": 50, "effect": "damage", "mult": 3.0, "double": True, "desc": "2 удара по ×3", "source": "book"},
        {"code": "tyr_8", "name": "Кулак дракона", "req_level": 25, "mp_cost": 60, "effect": "damage", "mult": 6.0, "desc": "×6 урона", "source": "book"},
    ],
    "overlord": [
        {"code": "ovl_1", "name": "Тёмный удар", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 маг. урона"},
        {"code": "ovl_2", "name": "Печать", "req_level": 3, "mp_cost": 20, "effect": "debuff", "mult": 0.70, "desc": "−30% урона врага"},
        {"code": "ovl_3", "name": "Забрать жизнь", "req_level": 5, "mp_cost": 25, "effect": "damage", "mult": 2.0, "lifesteal": 0.5, "desc": "×2 + лечение 50%"},
        {"code": "ovl_4", "name": "Война душ", "req_level": 7, "mp_cost": 30, "effect": "damage", "mult": 2.5, "desc": "×2.5 урона"},
        {"code": "ovl_5", "name": "Разлом", "req_level": 10, "mp_cost": 40, "effect": "damage", "mult": 3.0, "desc": "×3 маг. урона"},
        {"code": "ovl_6", "name": "Апокалипсис", "req_level": 15, "mp_cost": 50, "effect": "damage", "mult": 4.0, "desc": "×4 маг. урона"},
        {"code": "ovl_7", "name": "Печать смерти", "req_level": 20, "mp_cost": 55, "effect": "damage", "mult": 5.0, "desc": "×5 маг. урона", "source": "book"},
        {"code": "ovl_8", "name": "Апокалипсис II", "req_level": 25, "mp_cost": 65, "effect": "damage", "mult": 6.5, "desc": "×6.5 маг. урона", "source": "book"},
    ],
    "keeper": [
        {"code": "kp_1", "name": "Удар щитом", "req_level": 1, "mp_cost": 15, "effect": "damage", "mult": 2.0, "desc": "×2 урона + оглушение 50%"},
        {"code": "kp_2", "name": "Лечение", "req_level": 3, "mp_cost": 20, "effect": "heal", "mult": 0.30, "desc": "+30% HP"},
        {"code": "kp_3", "name": "Благословение", "req_level": 5, "mp_cost": 25, "effect": "heal", "mult": 0.45, "desc": "+45% HP"},
        {"code": "kp_4", "name": "Оберег", "req_level": 7, "mp_cost": 20, "effect": "buff_def", "mult": 0.40, "desc": "−60% урона на 2 раунда"},
        {"code": "kp_5", "name": "Святая кара", "req_level": 10, "mp_cost": 30, "effect": "damage", "mult": 2.8, "desc": "×2.8 урона"},
        {"code": "kp_6", "name": "Воскрешение", "req_level": 15, "mp_cost": 50, "effect": "heal", "mult": 0.75, "desc": "+75% HP"},
        {"code": "kp_7", "name": "Божественный щит", "req_level": 20, "mp_cost": 55, "effect": "buff_def", "mult": 0.05, "desc": "−95% урона на 2 раунда", "source": "book"},
        {"code": "kp_8", "name": "Массовое воскрешение", "req_level": 25, "mp_cost": 70, "effect": "heal", "mult": 1.00, "desc": "Полное восстановление HP", "source": "book"},
    ],
}


RACIAL_SKILLS = {
    "human": {"code": "rac_human", "name": "Воля", "req_level": 5, "mp_cost": 0,
              "effect": "passive", "mult": 0.20, "desc": "Пассив: +20% урона при HP < 30%"},
    "elf": {"code": "rac_elf", "name": "Глаз ястреба", "req_level": 5, "mp_cost": 0,
            "effect": "passive", "mult": 0.15, "desc": "Пассив: +15% маг. урона"},
    "dark_elf": {"code": "rac_dark", "name": "Тень", "req_level": 5, "mp_cost": 0,
                 "effect": "passive", "mult": 0.10, "desc": "Пассив: +10% маг. урона, +8% крита"},
    "orc": {"code": "rac_orc", "name": "Берсерк", "req_level": 5, "mp_cost": 0,
            "effect": "passive", "mult": 0.15, "desc": "Пассив: +10% урона"},
    "demon": {"code": "rac_demon", "name": "Адское пламя", "req_level": 5, "mp_cost": 0,
              "effect": "passive", "mult": 0.15, "desc": "Пассив: ярость, вампиризм 15%"},
    "angel": {"code": "rac_angel", "name": "Небесный щит", "req_level": 5, "mp_cost": 0,
              "effect": "passive", "mult": 0.20, "desc": "Пассив: +30% лечения"},
    "prit": {"code": "rac_prit", "name": "Из тени", "req_level": 5, "mp_cost": 0,
             "effect": "passive", "mult": 0.15, "desc": "Пассив: +12% крита, +15% уклонения"},
}


def available_skills(user, extra_learned=None):
    cls = user.get("class", "")
    race = user.get("race", "")
    lvl = user.get("level", 1)
    learned_books = set(extra_learned or [])
    result = []
    for s in CLASS_SKILLS.get(cls, []):
        if s.get("source") == "book":
            if s["code"] not in learned_books:
                continue
        if s["req_level"] <= lvl:
            result.append({**s, "source_type": s.get("source", "class")})
    if race in RACIAL_SKILLS:
        s = RACIAL_SKILLS[race]
        if s["req_level"] <= lvl:
            result.append({**s, "source_type": "race"})
    return result


def get_skill(code):
    for lst in CLASS_SKILLS.values():
        for s in lst:
            if s["code"] == code:
                return {**s, "source_type": s.get("source", "class")}
    for s in RACIAL_SKILLS.values():
        if s["code"] == code:
            return {**s, "source_type": "race"}
    return None


def skill_level(user, code):
    import json
    try:
        learned = json.loads(user.get("learned_skills") or "{}")
    except Exception:
        learned = {}
    return int(learned.get(code, 1))


def set_skill_level_json(user, code, level):
    """Возвращает обновлённый JSON для поля learned_skills.
    Использование:
        new_json = set_skill_level_json(user, code, lvl + 1)
        await g.db.set_learned_skills(user["user_id"], new_json)
    """
    import json
    try:
        learned = json.loads(user.get("learned_skills") or "{}")
    except Exception:
        learned = {}
    learned[code] = level
    return json.dumps(learned)


def skill_multiplier(user, code):
    """Множитель скилла с учётом его уровня (1-5).

    - damage / heal:    base × (1 + 0.15 × (lvl-1))
    - buff_atk:         1 + (base-1) × (1 + 0.15 × (lvl-1))
    - buff_def:         base − 0.10 × (lvl-1)  (чем ниже, тем лучше)
    - остальные:        base без изменений
    """
    s = get_skill(code)
    if not s:
        return 1.0
    lvl = skill_level(user, code)
    base = s.get("mult", 1.0)
    bonus = UPGRADE_DMG_BONUS * (lvl - 1)

    if s["effect"] in ("damage", "heal"):
        return base * (1 + bonus)
    if s["effect"] == "buff_atk":
        return 1 + (base - 1) * (1 + bonus)
    if s["effect"] == "buff_def":
        return max(0.05, base - UPGRADE_DEF_BONUS * (lvl - 1))
    return base


def get_skill_info(user, code):
    """Словарь с информацией о скилле для показа игроку."""
    s = get_skill(code)
    if not s:
        return None
    lvl = skill_level(user, code)
    base = s.get("mult", 1.0)
    current = skill_multiplier(user, code)

    next_mult = None
    if lvl < MAX_SKILL_LEVEL and s["effect"] != "passive":
        # Симулируем уровень +1
        class FakeUser:
            pass
        fake = FakeUser()
        try:
            import json
            learned = json.loads(user.get("learned_skills") or "{}")
        except Exception:
            learned = {}
        learned[code] = lvl + 1
        fake.learned_skills = json.dumps(learned)
        next_mult = skill_multiplier(fake, code)

    return {
        "skill": s,
        "level": lvl,
        "max_level": MAX_SKILL_LEVEL,
        "cost": UPGRADE_COST,
        "current_mult": current,
        "next_mult": next_mult,
        "can_upgrade": (lvl < MAX_SKILL_LEVEL
                        and s["effect"] != "passive"),
        "is_max": lvl >= MAX_SKILL_LEVEL,
        "is_passive": s["effect"] == "passive",
    }
