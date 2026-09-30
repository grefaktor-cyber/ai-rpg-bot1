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
