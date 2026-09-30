"""Нечёткий поиск предметов для команд бота."""
import difflib
import re


def _norm(s):
    """Нормализовать строку: lowercase + убрать лишние пробелы."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _base_name(name):
    """Убрать +N из названия."""
    if "+" in name:
        return name.rsplit("+", 1)[0].strip()
    return name


def find_inventory_item(query, inventory_names, cutoff=0.55):
    """Найти предмет в инвентаре (с учётом +N).
    Возвращает (exact_name | None, [suggestions])."""
    if not query or not inventory_names:
        return None, []
    q = _norm(query)

    # 1. Точное совпадение
    for it in inventory_names:
        if _norm(it) == q:
            return it, []

    # 2. Начинается с query
    starts = [it for it in inventory_names if _norm(it).startswith(q)]
    if len(starts) == 1:
        return starts[0], []
    if len(starts) > 1:
        return None, starts

    # 3. Содержит query
    contains = [it for it in inventory_names if q in _norm(it)]
    if len(contains) == 1:
        return contains[0], []
    if len(contains) > 1:
        return None, contains

    # 4. Fuzzy по базовым именам
    base_to_full = {}
    for it in inventory_names:
        base = _base_name(it)
        base_to_full.setdefault(_norm(base), []).append(it)

    matches_norm = difflib.get_close_matches(
        q, list(base_to_full.keys()), n=5, cutoff=cutoff
    )
    if len(matches_norm) == 1:
        fulls = base_to_full[matches_norm[0]]
        if len(fulls) == 1:
            return fulls[0], []
        return None, fulls
    if matches_norm:
        result = []
        for bn in matches_norm:
            result.extend(base_to_full[bn])
        return None, result

    return None, []


def find_shop_item(query, shop_keys, cutoff=0.55):
    """Найти базовое имя в SHOP.
    Возвращает (base_name | None, [suggestions])."""
    if not query or not shop_keys:
        return None, []
    q = _norm(query)

    # 1. Точное
    for k in shop_keys:
        if _norm(k) == q:
            return k, []

    # 2. Начинается
    starts = [k for k in shop_keys if _norm(k).startswith(q)]
    if len(starts) == 1:
        return starts[0], []
    if len(starts) > 1:
        return None, starts

    # 3. Содержит
    contains = [k for k in shop_keys if q in _norm(k)]
    if len(contains) == 1:
        return contains[0], []
    if len(contains) > 1:
        return None, contains

    # 4. Fuzzy
    norm_to_orig = {_norm(k): k for k in shop_keys}
    matches = difflib.get_close_matches(
        q, list(norm_to_orig.keys()), n=5, cutoff=cutoff
    )
    result = [norm_to_orig[m] for m in matches]
    if len(result) == 1:
        return result[0], []
    if result:
        return None, result
    return None, []
