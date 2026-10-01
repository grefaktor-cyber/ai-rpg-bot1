"""Все клавиатуры бота. UI-1: категории в главном меню."""
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton)

from core.game_data import POTION_PRICE


# ================= ГЛАВНОЕ МЕНЮ (ReplyKeyboard) =================
def main_kb():
    """Главное меню — 6 кнопок в 3 ряда."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Игра"),      KeyboardButton(text="👥 Социум")],
            [KeyboardButton(text="📊 Прогресс"),  KeyboardButton(text="🌍 Мир")],
            [KeyboardButton(text="🐉 Боссы"),     KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что делает герой?"
    )


# ================= INLINE КАТЕГОРИИ ГЛАВНОГО МЕНЮ =================
def menu_game_kb():
    """Категория «🎮 Игра»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv"),
         InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton(text="✨ Скилы", callback_data="menu_skills"),
         InlineKeyboardButton(text="⚒️ Кузница", callback_data="menu_craft")],
        [InlineKeyboardButton(text="📋 Квесты", callback_data="menu_quests"),
         InlineKeyboardButton(text="🏰 Подземелья", callback_data="menu_dungeon")],
        [InlineKeyboardButton(text="🗺 Карта", callback_data="menu_map"),
         InlineKeyboardButton(text="🚶 Идти", callback_data="menu_travel")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"),
         InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")],
    ])


def menu_social_kb():
    """Категория «👥 Социум»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Кто здесь", callback_data="menu_who"),
         InlineKeyboardButton(text="🏛 Гильдия", callback_data="menu_guild")],
        [InlineKeyboardButton(text="💬 Чат", callback_data="menu_chat"),
         InlineKeyboardButton(text="🤝 Обмен", callback_data="menu_trade")],
        [InlineKeyboardButton(text="⚔️ Дуэль", callback_data="menu_duel_info")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"),
         InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")],
    ])


def menu_progress_kb():
    """Категория «📊 Прогресс»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Профиль", callback_data="menu_profile"),
         InlineKeyboardButton(text="🏆 Достижения", callback_data="menu_ach")],
        [InlineKeyboardButton(text="🏅 Рейтинг", callback_data="menu_top"),
         InlineKeyboardButton(text="🎁 Награда", callback_data="menu_daily")],
        [InlineKeyboardButton(text="🏆 Сезон", callback_data="menu_season"),
         InlineKeyboardButton(text="📜 Дневник", callback_data="menu_journal")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="menu_premium"),
         InlineKeyboardButton(text="🐾 Питомец", callback_data="menu_pet")],
        [InlineKeyboardButton(text="🏆 Титулы", callback_data="menu_titles")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"),
         InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")],
    ])


# ================= КОРНЕВОЕ МЕНЮ (Назад) =================
def menu_root_kb():
    """Экран «Категории» — куда возвращает ⬅️ Назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Игра", callback_data="menu_game"),
         InlineKeyboardButton(text="👥 Социум", callback_data="menu_social")],
        [InlineKeyboardButton(text="📊 Прогресс", callback_data="menu_progress")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")],
    ])


# ================= ПРОФИЛЬ (вкладки) =================
def profile_tabs_kb(active_tab="stats"):
    """Вкладки профиля."""
    def btn(text, tab):
        mark = "•" if active_tab == tab else " "
        return InlineKeyboardButton(
            text=f"{mark} {text}", callback_data=f"prof_tab_{tab}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("📊 Статы", "stats"), btn("👑 Экип.", "equip")],
        [btn("🏆 Достижения", "ach"), btn("📦 Материалы", "mats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="prof_close")],
    ])


# ================= ПОИСК В ИНВЕНТАРЕ =================
def inv_search_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="inv_search_cancel")],
    ])


# ================= ФИЛЬТР КВЕСТОВ =================
def quests_filter_kb(active="all"):
    """Кнопки фильтра в /quests."""
    def btn(text, code):
        mark = "•" if active == code else " "
        return InlineKeyboardButton(
            text=f"{mark} {text}", callback_data=f"qfilter_{code}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("📋 Все", "all"), btn("📜 Сюжет", "story")],
        [btn("⚔️ Ежедневные", "daily"), btn("🏆 Еженедельные", "weekly")],
        [InlineKeyboardButton(text="⭐ Очки заданий",
                              callback_data="quest_points")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="quest_close")],
    ])


# ================= БОЕВАЯ =================
def combat_kb(active_skills=None, mp=0, pending=None,
              prefix="combat", max_actions=4, is_pvp=False,
              can_spoil=False, spoil_used=False):
    from core.skills import get_skill
    from core.game_data import POTION_PRICE, MP_POTION_PRICE

    pending = pending or []
    rows = []

    rows.append([
        InlineKeyboardButton(text="⚔️ Атака", callback_data=f"{prefix}_add_attack"),
        InlineKeyboardButton(text="🛡 Защита", callback_data=f"{prefix}_add_defend"),
    ])

    if active_skills:
        skill_buttons = []
        for code in active_skills[:3]:
            if not code:
                continue
            s = get_skill(code)
            if not s:
                continue
            icon = {
                "damage": "🔥", "heal": "💚",
                "buff_atk": "⚡", "buff_def": "🛡",
                "debuff": "🌀", "stun": "💫",
            }.get(s["effect"], "✨")
            short = s["name"][:10]
            text = f"{icon} {short} ({s['mp_cost']}mp)"
            if mp < s["mp_cost"]:
                text = f"{icon} {short} ❌"
            skill_buttons.append(InlineKeyboardButton(
                text=text, callback_data=f"{prefix}_add_skill_{code}"
            ))
        if len(skill_buttons) <= 2:
            rows.append(skill_buttons)
        else:
            rows.append(skill_buttons[:2])
            rows.append(skill_buttons[2:])

    rows.append([
        InlineKeyboardButton(text=f"💚 HP ({POTION_PRICE}💰)",
                             callback_data=f"{prefix}_add_potion_hp"),
        InlineKeyboardButton(text=f"🔮 MP ({MP_POTION_PRICE}💰)",
                             callback_data=f"{prefix}_add_potion_mp"),
    ])

    if can_spoil and not is_pvp:
        if spoil_used:
            rows.append([InlineKeyboardButton(
                text="🌿 Спойл уже использован",
                callback_data="combat_spoil_noop")])
        else:
            rows.append([InlineKeyboardButton(
                text="🌿 Спойл (обчистить моба)",
                callback_data="combat_add_spoil")])

    count = len(pending)
    row_actions = []
    if count > 0:
        row_actions.append(InlineKeyboardButton(
            text="↩️ Убрать", callback_data=f"{prefix}_undo"))
    row_actions.append(InlineKeyboardButton(
        text=f"⚡ Выполнить ({count}/{max_actions})",
        callback_data=f"{prefix}_execute"))
    rows.append(row_actions)

    if is_pvp:
        rows.append([InlineKeyboardButton(
            text="🏳️ Сдаться", callback_data="pvp_surrender")])
    else:
        rows.append([InlineKeyboardButton(
            text="🏃 Бежать", callback_data="combat_flee")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def combat_pending_text(pending, max_actions=4):
    """Визуальные слоты очереди."""
    from core.skills import get_skill

    action_icons = {
        "attack":    "⚔️",
        "defend":    "🛡",
        "potion_hp": "💚",
        "potion_mp": "🔮",
        "spoil":     "🌿",
    }
    slot_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    lines = []
    for i, a in enumerate(pending):
        num = slot_emoji[i] if i < len(slot_emoji) else f"{i+1}."
        if a.startswith("skill_"):
            code = a.replace("skill_", "")
            s = get_skill(code)
            name = s["name"] if s else code
            cost = s["mp_cost"] if s else 0
            lines.append(f"{num} ✨ <b>{name}</b> ({cost} MP)")
        else:
            label = {
                "attack": "Атака", "defend": "Защита",
                "potion_hp": "Зелье HP", "potion_mp": "Зелье MP",
                "spoil": "Спойл",
            }.get(a, a)
            lines.append(f"{num} {action_icons.get(a, '❔')} {label}")

    for i in range(len(pending), max_actions):
        num = slot_emoji[i] if i < len(slot_emoji) else f"{i+1}."
        lines.append(f"{num} ▫️ <i>пусто</i>")

    header = f"<b>📋 Очередь ({len(pending)}/{max_actions})</b>"
    return header + "\n" + "\n".join(lines)


# ================= ПОДЗЕМЕЛЬЯ / ПИТОМЦЫ / МАГАЗИН =================
def dungeon_continue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="dungeon_next")],
        [InlineKeyboardButton(text="🏃 Выйти с добычей", callback_data="dungeon_leave")],
    ])


def dungeons_kb(dungeons_dict, player_level, player_gold):
    rows = []
    for code, d in dungeons_dict.items():
        can = player_level >= d["level_req"] and player_gold >= d["entry"]
        if can:
            rows.append([InlineKeyboardButton(
                text=f"{d['name']} — {d['entry']}💰",
                callback_data=f"dungeon_enter_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pets_kb(pets_dict):
    rows = []
    for code, p in pets_dict.items():
        rows.append([InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}💰",
            callback_data=f"pet_buy_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_kb(shop_dict, shop_mult):
    rows = []
    for name, data in shop_dict.items():
        if data.get("type") == "potion":
            continue
        price = int(data["price"] * shop_mult)
        rows.append([InlineKeyboardButton(
            text=f"{name} — {price}💰",
            callback_data=f"shop_buy_{name}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def craft_kb(recipes):
    rows = []
    for result in recipes.keys():
        rows.append([InlineKeyboardButton(
            text=f"Создать {result}",
            callback_data=f"craft_{result}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ================= ПУТЕШЕСТВИЯ / NPC / ГИЛЬДИИ =================
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


# ================= PVP / ДУЭЛИ =================
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


# ================= ПРОЧЕЕ =================
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


# ================= СКИЛЫ =================
def skills_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Все скилы", callback_data="skills_list")],
        [InlineKeyboardButton(text="📖 Изучить книгу", callback_data="skills_learn_menu")],
        [InlineKeyboardButton(text="🎯 Настроить слоты", callback_data="skills_slots")],
        [InlineKeyboardButton(text="⬆️ Прокачать скилы", callback_data="skills_upgrade")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="skills_close")],
    ])


def skills_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")],
    ])


def skills_slot_choice_kb(available, slot_num):
    rows = []
    for s in available:
        src = " 📖" if s.get("source") == "book" else ""
        rows.append([InlineKeyboardButton(
            text=f"{s['name']}{src} · {s['mp_cost']} MP",
            callback_data=f"skills_set_{slot_num}_{s['code']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="skills_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skills_upgrade_kb(available, learned):
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


# ================= МИР =================
def world_menu_kb(has_events=False):
    """Клавиатура для /world."""
    rows = []
    if has_events:
        rows.append([InlineKeyboardButton(text="🔄 Обновить",
                                           callback_data="world_refresh")])
    rows.append([InlineKeyboardButton(text="🗺 Карта",
                                       callback_data="menu_map")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть",
                                       callback_data="world_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
