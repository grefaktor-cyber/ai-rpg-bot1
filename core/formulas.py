"""Формулы: статы, HP, MP, P.Def, M.Def, урон, сеты."""
import re
from core.game_data import (
    SHOP, PETS, FACTIONS, RACES, CLASSES, ROLE_HP_BONUS,
)
from core.equipment import (
    SLOTS, get_set_bonus,
)


def parse_item(s):
    if not s:
        return "", 0
    m = re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def calc_stats(race_code, class_code):
    if race_code not in RACES or class_code not in CLASSES:
        return {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5}
    race = RACES[race_code]["stats"].copy()
    for k, v in CLASSES[class_code]["bonus"].items():
        race[k] = race.get(k, 0) + v
    return race


def effective_stats(user):
    """Статы с учётом 7 слотов, питомца и сетов."""
    base = {
        "str": user.get("stat_str", 5), "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5), "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5), "men": user.get("stat_men", 5),
    }
    # Все 7 слотов
    for slot in SLOTS:
        raw = user.get(f"equipped_{slot}", "")
        if not raw:
            continue
        name, lvl = parse_item(raw)
        if name in SHOP:
            for k, v in SHOP[name]["bonus"].items():
                bonus = int(v * (1 + lvl * 0.10))
                base[k] = base.get(k, 0) + bonus
    # Питомец
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"])
        if pet:
            for k, v in pet["bonus"].items():
                base[k] = base.get(k, 0) + v
    # Сетовый бонус (только DEX для light)
    set_b = get_set_bonus(user)
    if set_b and "dex_bonus" in set_b:
        base["dex"] = base.get("dex", 0) + set_b["dex_bonus"]
    return base


def get_role(user):
    return CLASSES.get(user.get("class", ""), {}).get("role", "fighter")


def get_dmg_type(user):
    return CLASSES.get(user.get("class", ""), {}).get("dmg_type", "phys")


def calc_p_def(user):
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    val = eff["con"] * 1.5 + lvl * 2
    set_b = get_set_bonus(user)
    if set_b and "pdef_mult" in set_b:
        val *= set_b["pdef_mult"]
    return int(val)


def calc_m_def(user):
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    val = eff["men"] * 1.5 + eff["int"] * 0.5 + lvl * 2
    set_b = get_set_bonus(user)
    if set_b and "mdef_mult" in set_b:
        val *= set_b["mdef_mult"]
    return int(val)


def calc_max_hp(user):
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    role_bonus = ROLE_HP_BONUS.get(get_role(user), 10)
    hp = eff["con"] * 12 + lvl * 10 + 40 + role_bonus
    hp = int(hp * racial_hp_mult(user))
    set_b = get_set_bonus(user)
    if set_b and "hp_mult" in set_b:
        hp *= set_b["hp_mult"]
    f = FACTIONS.get(user.get("faction", ""), None)
    if f:
        hp *= f["hp_mult"]
    return int(hp)


def calc_max_mp(user):
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    mp = 50 + eff["int"] * 5 + lvl * 3
    set_b = get_set_bonus(user)
    if set_b and "mp_mult" in set_b:
        mp *= set_b["mp_mult"]
    return int(mp)


def hp_bar(current, maximum, length=10):
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def danger_emoji(player_level, enemy_level, is_boss):
    if is_boss:
        return "🐉"
    diff = enemy_level - player_level
    if diff <= -3: return "🟢"
    if diff <= -1: return "🟡"
    if diff <= 1:  return "🟠"
    if diff <= 3:  return "🔴"
    return "💀"


def faction_mult(user, key):
    f = FACTIONS.get(user.get("faction", ""))
    if not f:
        return 1.0
    return f.get(key, 1.0)


def calc_damage(user):
    eff = effective_stats(user)
    dmg_type = get_dmg_type(user)
    if dmg_type == "phys":
        return int(eff["str"] * 2 + eff["con"] / 2)
    if dmg_type == "agile":
        return int(eff["dex"] * 2 + eff["str"] / 2)
    if dmg_type == "magic":
        return int(eff["int"] * 1.5 + eff["wit"])
    return int(eff["str"] * 2 + eff["dex"])


def get_crit_chance(user):
    """Шанс крита с учётом сета и питомца."""
    eff = effective_stats(user)
    base = eff["dex"]
    if user.get("pet_type") == "owl":
        base += 15
    set_b = get_set_bonus(user)
    if set_b and "crit_bonus" in set_b:
        base += set_b["crit_bonus"]
    return base


def enemy_p_def(level):
    return int(level * 2 + 3)


def enemy_m_def(level):
    return int(level * 1.5 + 2)


def apply_defense(damage, defense):
    if defense <= 0:
        return max(1, int(damage))
    reduction = defense / (defense + 50)
    final = int(damage * (1 - reduction))
    return max(1, final)


# ================= БОЕВОЙ БАЛАНС 2.0 =================
import random as _rnd


# ============ XP С УЧЁТОМ РАЗНИЦЫ УРОВНЕЙ ============
def calc_xp_reward(enemy_level, player_level, base_exp):
    """Умный XP. Слабые мобы дают копейки, сильные — жирно.
    Как в L2: за мобов на 5+ уровней ниже — почти 0."""
    diff = enemy_level - player_level
    if diff >= 0:
        mult = min(2.5, 1.0 + diff * 0.15)
    else:
        mult = max(0.05, 1.0 + diff * 0.15)
    return max(1, int(base_exp * mult))


# ============ HP МОБА ============
def calc_enemy_hp(enemy_level, player_level, is_boss=False):
    """HP моба. Растёт с уровнем и уровнем игрока, чтобы бои были длиннее."""
    if is_boss:
        return int(enemy_level * 45 + player_level * 12)
    return int(enemy_level * 28 + player_level * 6)


# ============ УРОН МОБА (БАЗА) ============
def calc_enemy_base_dmg(enemy_level, player_level, is_boss=False):
    """Базовый урон моба. Растёт с уровнем игрока, чтобы не было скучно."""
    base = enemy_level * 6 + (player_level // 2) + _rnd.randint(0, 5)
    if is_boss:
        base = int(base * 1.5)
    return base


# ============ ТИП УРОНА МОБА ============
MAGIC_MOB_KEYWORDS = [
    "маг", "колдун", "некромант", "жрец", "шаман", "лич",
    "призрак", "дух", "ведьма", "демон", "элементаль",
    "хранитель", "король духов", "ксарг",
]


def get_enemy_dmg_type(enemy_name):
    """Определить тип урона моба по имени.
    По умолчанию — phys. Магические — по ключевым словам."""
    low = (enemy_name or "").lower()
    for kw in MAGIC_MOB_KEYWORDS:
        if kw in low:
            return "magic"
    return "phys"


# ============ ЗАЩИТА ИГРОКА ПРОТИВ ТИПА МОБА ============
def get_player_def_for_enemy(user, enemy_dmg_type):
    """Какую защиту игрока применить против этого типа урона."""
    if enemy_dmg_type == "magic":
        return calc_m_def(user)
    return calc_p_def(user)


def apply_player_defense(enemy_dmg, player_def):
    """Снизить урон врага через защиту игрока.
    Формула как в L2: reduction = def / (def + 50)."""
    if player_def <= 0:
        return max(1, int(enemy_dmg))
    reduction = player_def / (player_def + 50)
    final = int(enemy_dmg * (1 - reduction))
    return max(1, final)


# ============ ФАЗЫ БОССА ============
def get_boss_phase(combat):
    """Фаза босса по HP. Возвращает dict или None."""
    if not combat or not combat.get("is_boss"):
        return None
    max_hp = combat.get("enemy_max_hp", 1)
    if max_hp <= 0:
        return None
    hp_pct = combat["enemy_hp"] / max_hp
    if hp_pct > 0.6:
        return None  # обычная фаза
    if hp_pct > 0.3:
        return {
            "name": "⚡ Ярость",
            "dmg_mult": 1.30,
            "attacks": 1,
            "desc": "Босс в ярости! +30% урона",
        }
    return {
        "name": "🔥 Финал",
        "dmg_mult": 1.50,
        "attacks": 2,
        "desc": "Босс атакует вдвое чаще!",
    }


# ============ РЕГЕНЕРАЦИЯ МЕЖДУ КОМНАТАМИ ПОДЗЕМЕЛЬЯ ============
def regen_between_rooms(user, hp_pct=0.20, mp_pct=0.30):
    """Сколько HP/MP восстановить между комнатами.
    Возвращает (new_hp, new_mp)."""
    max_hp = user.get("max_hp", 1)
    max_mp = user.get("max_mp", 0)
    hp = user.get("hp", 0)
    mp = user.get("mp", 0)
    new_hp = min(max_hp, hp + int(max_hp * hp_pct))
    new_mp = min(max_mp, mp + int(max_mp * mp_pct)) if max_mp > 0 else 0
    return new_hp, new_mp

# ================= УРОН БОССА С УЧЁТОМ ЗАЩИТЫ =================
def calc_boss_damage_to_player(user, boss_data, phase_mult=1.0):
    """Рассчитать урон босса по игроку с учётом P.Def/M.Def.
    Работает как в L2: dmg_type босса определяет, через какую защиту режется.
    """
    import random
    base = boss_data.get("attack_dmg", 100)
    dmg_type = boss_data.get("dmg_type", "phys")
    
    # Разброс ±10%
    raw = int(base * random.uniform(0.9, 1.1))
    
    # Защита игрока
    if dmg_type == "magic":
        player_def = calc_m_def(user)
    else:
        player_def = calc_p_def(user)
    
    # Применяем формулу apply_defense
    mitigated = apply_player_defense(raw, player_def)
    
    # Множитель фазы
    final = int(mitigated * phase_mult)
    return max(1, final)

# ================= ЭФФЕКТЫ ЭКСКЛЮЗИВНОЙ ЭКИПИРОВКИ =================
def _iter_equipped(user):
    """Генератор: (name, level) по всем надётым предметам."""
    for slot in SLOTS:
        raw = user.get(f"equipped_{slot}", "")
        if not raw:
            continue
        name, lvl = parse_item(raw)
        yield name, lvl


def get_block_chance(user):
    """Суммарный шанс блока от экипировки."""
    total = 0
    for name, _ in _iter_equipped(user):
        if name in SHOP:
            total += SHOP[name].get("block_chance", 0)
    return min(total, 75)  # макс 75%


def get_crit_bonus(user):
    """Бонус к криту от экипировки."""
    total = 0
    for name, _ in _iter_equipped(user):
        if name in SHOP:
            total += SHOP[name].get("crit_bonus", 0)
    return total


def get_gold_mult(user):
    """Множитель золота от экипировки."""
    mult = 1.0
    for name, _ in _iter_equipped(user):
        if name in SHOP:
            mult *= SHOP[name].get("gold_mult", 1.0)
    return mult

# ================= РАСОВЫЕ ЭФФЕКТЫ (пассив) =================
def racial_crit_bonus(user):
    """Бонус к криту от расы. Возвращает +% к шансу."""
    race = user.get("race", "")
    if race == "elf":
        return 15
    if race == "prit":
        return 15
    return 0


def racial_magic_mult(user):
    """Множитель магического урона."""
    race = user.get("race", "")
    if race == "dark_elf":
        return 1.10
    if race == "demon":
        return 1.15
    return 1.0


def racial_heal_mult(user):
    """Множитель силы лечения."""
    if user.get("race") == "angel":
        return 1.20
    return 1.0


def racial_gold_mult(user):
    """Множитель золота."""
    if user.get("race") == "prit":
        return 1.10
    return 1.0


def racial_hp_mult(user):
    """Множитель max HP."""
    if user.get("race") == "orc":
        return 1.15
    return 1.0


def racial_low_hp_mult(user):
    """Для 'Воля' (human): +20% урона при HP < 30%."""
    if user.get("race") == "human":
        max_hp = user.get("max_hp", 100)
        if max_hp > 0 and user.get("hp", 0) < max_hp * 0.30:
            return 1.20
    return 1.0
