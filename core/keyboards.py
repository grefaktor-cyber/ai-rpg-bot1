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
            [KeyboardButton(text="💎 Премиум"),   KeyboardButton(text="🐉 Боссы")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что делает герой?"
    )


def combat_kb(active_skills=None, mp=0, pending=None,
              prefix="combat", max_actions=4, is_pvp=False,
              can_spoil=False, spoil_used=False):
    """Боевая клавиатура с очередью действий."""
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
                "damage":   "🔥", "heal":     "💚",
                "buff_atk": "⚡", "buff_def": "🛡",
                "debuff":   "🌀", "stun":     "💫",
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

    # Спул — отдельная кнопка если доступно
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
    if not pending:
        return f"<i>Очередь пуста. Добавь 1-{max_actions} действий.</i>"
    lines = [f"<b>📋 Твоя очередь ({len(pending)}/{max_actions}):</b>"]
    icons = {
        "attack": "⚔️ Атака", "defend": "🛡 Защита",
        "potion_hp": "💚 Зелье HP", "potion_mp": "🔮 Зелье MP",
        "spoil": "🌿 Спойл",
    }
    for i, a in enumerate(pending):
        if a.startswith("skill_"):
            code = a.replace("skill_", "")
            from core.skills import get_skill
            s = get_skill(code)
            name = s["name"] if s else code
            lines.append(f"{i+1}. ✨ {name}")
        else:
            lines.append(f"{i+1}. {icons.get(a, a)}")
    return "\n".join(lines)


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
