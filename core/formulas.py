"""Формулы: статы, HP, MP, P.Def, M.Def, урон, полоски, эмодзи."""
import re

from core.game_data import (
    SHOP, PETS, FACTIONS, RACES, CLASSES, ROLE_HP_BONUS,
)


def parse_item(s):
    if not s:
        return "", 0
    m = re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def calc_stats(race_code, class_code):
    """Базовые статы = раса + бонус класса."""
    if race_code not in RACES or class_code not in CLASSES:
        return {"str": 5, "dex": 5, "con": 5, "int": 5, "wit": 5, "men": 5}
    race = RACES[race_code]["stats"].copy()
    for k, v in CLASSES[class_code]["bonus"].items():
        race[k] = race.get(k, 0) + v
    return race


def effective_stats(user):
    """Статы с учётом экипировки и питомца."""
    base = {
        "str": user.get("stat_str", 5), "dex": user.get("stat_dex", 5),
        "con": user.get("stat_con", 5), "int": user.get("stat_int", 5),
        "wit": user.get("stat_wit", 5), "men": user.get("stat_men", 5),
    }
    for slot in ["equipped_weapon", "equipped_armor", "equipped_accessory"]:
        raw = user.get(slot, "")
        if raw:
            name, lvl = parse_item(raw)
            if name in SHOP:
                for k, v in SHOP[name]["bonus"].items():
                    bonus = int(v * (1 + lvl * 0.10))
                    base[k] = base.get(k, 0) + bonus
    if user.get("pet_type"):
        pet = PETS.get(user["pet_type"])
        if pet:
            for k, v in pet["bonus"].items():
                base[k] = base.get(k, 0) + v
    return base


def get_role(user):
    """Роль класса: tank / fighter / agile / mage / universal."""
    cls = CLASSES.get(user.get("class", ""), {})
    return cls.get("role", "fighter")


def get_dmg_type(user):
    """Тип урона: phys / agile / magic."""
    cls = CLASSES.get(user.get("class", ""), {})
    return cls.get("dmg_type", "phys")


def calc_p_def(user):
    """Физическая защита."""
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    return int(eff["con"] * 1.5 + lvl * 2)


def calc_m_def(user):
    """Магическая защита."""
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    return int(eff["men"] * 1.5 + eff["int"] * 0.5 + lvl * 2)


def calc_max_hp(user):
    """Максимальное HP с учётом роли и фракции."""
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    role_bonus = ROLE_HP_BONUS.get(get_role(user), 10)
    hp = eff["con"] * 12 + lvl * 10 + 40 + role_bonus
    f = FACTIONS.get(user.get("faction", ""), None)
    if f:
        hp = int(hp * f["hp_mult"])
    return hp


def calc_max_mp(user):
    """Максимальное MP (для скилов)."""
    eff = effective_stats(user)
    lvl = user.get("level", 1)
    return 50 + eff["int"] * 5 + lvl * 3


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
    """Базовый урон по типу класса."""
    eff = effective_stats(user)
    dmg_type = get_dmg_type(user)
    if dmg_type == "phys":
        return int(eff["str"] * 2 + eff["con"] / 2)
    if dmg_type == "agile":
        return int(eff["dex"] * 2 + eff["str"] / 2)
    if dmg_type == "magic":
        return int(eff["int"] * 1.5 + eff["wit"])
    return int(eff["str"] * 2 + eff["dex"])
