"""Формулы: статы, HP, урон, полоски, эмодзи опасности."""
import re

from core.game_data import SHOP, PETS, FACTIONS, RACES, CLASSES


def parse_item(s):
    """Разбирает строку предмета: 'Клинок тьмы+3' → ('Клинок тьмы', 3)."""
    if not s:
        return "", 0
    m = re.match(r"^(.+?)\+(\d+)$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, 0


def calc_stats(race_code, class_code):
    """Базовые статы = раса + бонус класса."""
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


def calc_max_hp(user):
    """Максимальное HP с учётом фракции."""
    eff = effective_stats(user)
    hp = eff["con"] * 20 + user["level"] * 15
    f = FACTIONS.get(user.get("faction", ""), None)
    if f:
        hp = int(hp * f["hp_mult"])
    return hp


def hp_bar(current, maximum, length=10):
    """Полоска HP: ██████░░░░."""
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def danger_emoji(player_level, enemy_level, is_boss):
    """Эмодзи опасности врага относительно игрока."""
    if is_boss:
        return "🐉"
    diff = enemy_level - player_level
    if diff <= -3: return "🟢"
    if diff <= -1: return "🟡"
    if diff <= 1:  return "🟠"
    if diff <= 3:  return "🔴"
    return "💀"


def faction_mult(user, key):
    """Множитель фракции: hp_mult, shop_mult, gold_mult, dmg_mult."""
    f = FACTIONS.get(user.get("faction", ""))
    if not f:
        return 1.0
    return f.get(key, 1.0)
