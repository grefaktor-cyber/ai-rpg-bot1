"""Все inline- и reply-клавиатуры бота."""
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton)

from core.game_data import POTION_PRICE


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="⭐ Профиль"),   KeyboardButton(text="🏆 Достижения")],
            [KeyboardButton(text="📋 Квесты"),    KeyboardButton(text="🗺 Карта")],
            [KeyboardButton(text="🚶 Идти"),      KeyboardButton(text="🌍 Мир")],
            [KeyboardButton(text="👥 Кто здесь"), KeyboardButton(text="🐾 Питомец")],
            [KeyboardButton(text="🏰 Подземелья"),KeyboardButton(text="⚒️ Кузница")],
            [KeyboardButton(text="🏛 Гильдия"),   KeyboardButton(text="✨ Скилы")],
            [KeyboardButton(text="🎁 Награда"),   KeyboardButton(text="🏅 Рейтинг")],
            [KeyboardButton(text="💎 Премиум"),   KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что делает герой?"
    )


def combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="combat_attack"),
         InlineKeyboardButton(text="🛡 Защита", callback_data="combat_defend")],
        [InlineKeyboardButton(text=f"💚 Зелье ({POTION_PRICE}💰)", callback_data="combat_potion"),
         InlineKeyboardButton(text="🏃 Бежать", callback_data="combat_flee")],
    ])


def dungeon_continue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="dungeon_next")],
        [InlineKeyboardButton(text="🏃 Выйти с добычей", callback_data="dungeon_leave")],
    ])


def pvp_kb(my_turn):
    if my_turn:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атака", callback_data="pvp_attack")],
            [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="pvp_surrender")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="pvp_surrender")],
    ])


def duel_offer_kb(offer_id, is_caller=False):
    if is_caller:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"duel_cancel_{offer_id}")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept_{offer_id}"),
         InlineKeyboardButton(text="💰 Своя ставка", callback_data=f"duel_counter_{offer_id}")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"duel_decline_{offer_id}")],
    ])


def travel_kb(location_code, player_level, world_module):
    rows = []
    for code, info in world_module.get_neighbors(location_code):
        can, reason = world_module.can_enter(code, player_level)
        if can:
            rows.append([InlineKeyboardButton(text=f"→ {info['name']}",
                                              callback_data=f"travel_to_{code}")])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🔒 {info['name']} (ур.{info['level_req']}+)",
                callback_data="travel_locked")])
    rows.append([InlineKeyboardButton(text="❌ Остаться", callback_data="travel_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def npc_list_kb(location_code, world_module):
    rows = []
    for code, info in world_module.get_npcs_in_location(location_code):
        rows.append([InlineKeyboardButton(text=f"👤 {info['name']}",
                                          callback_data=f"npc_{code}")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="npc_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def npc_menu_kb(npc_code, world_module):
    npc = world_module.get_npc(npc_code)
    if not npc:
        return None
    rows = []
    for qcode in npc.get("quests", []):
        q = world_module.get_quest(qcode)
        if not q:
            continue
        rows.append([InlineKeyboardButton(text=f"📜 {q['title']}",
                                          callback_data=f"npcquest_{qcode}")])
    rows.append([InlineKeyboardButton(text="💬 Поговорить",
                                      callback_data=f"npctalk_{npc_code}")])
    rows.append([InlineKeyboardButton(text="❌ Уйти", callback_data="npc_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def guild_menu_kb(has_guild):
    if has_guild:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Инфо", callback_data="guild_info")],
            [InlineKeyboardButton(text="👥 Участники", callback_data="guild_members")],
            [InlineKeyboardButton(text="⚔️ Захватить локацию", callback_data="guild_capture")],
            [InlineKeyboardButton(text="🚪 Выйти из гильдии", callback_data="guild_leave")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛 Создать гильдию (1000💰)",
                              callback_data="guild_create_start")],
        [InlineKeyboardButton(text="🏆 Топ гильдий", callback_data="guild_top")],
    ])


def shop_kb(shop_dict, shop_mult):
    rows = []
    for name, data in shop_dict.items():
        if data["type"] == "potion":
            continue  # зелья будут в отдельной категории (2.3)
        price = int(data["price"] * shop_mult)
        rows.append([InlineKeyboardButton(text=f"{name} — {price}💰",
                                          callback_data=f"shop_buy_{name}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def craft_kb(recipes):
    rows = []
    for result in recipes.keys():
        rows.append([InlineKeyboardButton(text=f"Создать {result}",
                                          callback_data=f"craft_{result}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pets_kb(pets_dict):
    rows = []
    for code, p in pets_dict.items():
        rows.append([InlineKeyboardButton(text=f"{p['name']} — {p['price']}💰",
                                          callback_data=f"pet_buy_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dungeons_kb(dungeons_dict, player_level, player_gold):
    rows = []
    for code, d in dungeons_dict.items():
        can = player_level >= d["level_req"] and player_gold >= d["entry"]
        if can:
            rows.append([InlineKeyboardButton(
                text=f"{d['name']} — {d['entry']}💰",
                callback_data=f"dungeon_enter_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yes_no_kb(yes_cb, no_cb, yes_text="✅ Да", no_text="❌ Нет"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=yes_text, callback_data=yes_cb),
        InlineKeyboardButton(text=no_text, callback_data=no_cb),
    ]])


def race_selection_kb(races_dict):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{r['name']} — {r['desc']}",
                              callback_data=f"race_{code}")]
        for code, r in races_dict.items()
    ])


def class_selection_kb(classes_dict):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['name']} — {c['desc']}",
                              callback_data=f"class_{code}")]
        for code, c in classes_dict.items()
    ])


def faction_selection_kb(factions_dict):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{f['name']} — {f['desc']}",
                              callback_data=f"faction_{code}")]
        for code, f in factions_dict.items()
    ])


# ================= МЕНЮ СКИЛОВ =================
def skills_main_kb():
    """Главное меню скилов."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Все скилы", callback_data="skills_list")],
        [InlineKeyboardButton(text="🎯 Настроить слоты", callback_data="skills_slots")],
        [InlineKeyboardButton(text="⬆️ Прокачать скилы", callback_data="skills_upgrade")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="skills_close")],
    ])


def skills_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")],
    ])


def skills_slot_choice_kb(available, slot_num):
    """Выбор скила в слот. available — список скилов."""
    rows = []
    for s in available:
        rows.append([InlineKeyboardButton(
            text=f"{s['name']} · {s['mp_cost']} MP · {s['desc']}",
            callback_data=f"skills_set_{slot_num}_{s['code']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skills_upgrade_kb(available, learned):
    """Кнопки прокачки. learned — dict code: level."""
    rows = []
    for s in available:
        if s["effect"] == "passive":
            continue
        lvl = learned.get(s["code"], 1)
        if lvl >= 3:
            mark = "✅ МАКС"
            cb = "skills_noop"
        else:
            mark = f"ур.{lvl} → {lvl+1} (1 очко)"
            cb = f"skills_up_{s['code']}"
        rows.append([InlineKeyboardButton(
            text=f"{s['name']} · {mark}",
            callback_data=cb
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
