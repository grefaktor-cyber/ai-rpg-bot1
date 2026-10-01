"""Контекстные подсказки для игроков."""
import logging

from core import globals as g


# Отслеживаем действия игроков в памяти: uid -> {"lost_count": N, "last_hint": ts}
_state = {}


def reset_hint_state(uid):
    """Сбросить счётчик "затупа"."""
    _state[uid] = {"lost_count": 0}
    _state[uid]["lost_count"] = 0


def register_lost_action(uid):
    """Игрок совершил действие без видимого результата. Возвращает True если 3+ раз."""
    s = _state.setdefault(uid, {"lost_count": 0})
    s["lost_count"] = s.get("lost_count", 0) + 1
    if s["lost_count"] >= 3:
        s["lost_count"] = 0
        return True
    return False


def clear_lost(uid):
    """Игрок успешно что-то сделал — сбрасываем счётчик."""
    if uid in _state:
        _state[uid]["lost_count"] = 0


async def check_hp_hint(uid, chat_id, user):
    """Если HP < 50% вне боя — подсказать."""
    hp_pct = user["hp"] / max(1, user["max_hp"])
    if hp_pct >= 0.5:
        return
    if user["hp"] <= 0:
        return
    if user["gold"] < 25:
        return

    # Проверяем есть ли зелье в инвентаре
    inv = await g.db.get_inventory(uid)
    has_potion = any("Зелье HP" in it["item_name"] or "Эликсир HP" in it["item_name"]
                     for it in inv)

    try:
        if has_potion:
            await g.bot.send_message(
                chat_id,
                "💡 <b>Подсказка:</b> HP низкое. Используй зелье:\n"
                "<code>/use Зелье HP</code>",
                parse_mode="HTML")
        else:
            await g.bot.send_message(
                chat_id,
                "💡 <b>Подсказка:</b> HP низкое. Купи и используй зелье:\n"
                "🛒 Магазин → 🧪 Зелья → /use Зелье HP",
                parse_mode="HTML")
    except Exception as e:
        logging.debug(f"hp hint error: {e}")


async def check_energy_hint(uid, chat_id, user):
    """Если энергия 0 — подсказать /daily."""
    if user.get("is_premium"):
        return
    if user.get("energy", 0) > 0:
        return
    try:
        await g.bot.send_message(
            chat_id,
            "⚡ <b>Энергия исчерпана</b>\n\n"
            "Подожди восстановления или забери награду:\n"
            "🎁 /daily — полное восстановление энергии",
            parse_mode="HTML")
    except Exception as e:
        logging.debug(f"energy hint error: {e}")


async def check_new_player_hint(uid, chat_id, user):
    """Первые 3 действия новичка — даём наводящие подсказки."""
    action_count = user.get("action_count", 0)
    if action_count > 3:
        return
    if action_count == 1:
        hint = ("💡 <b>Совет:</b> Попробуй написать что-то вроде:\n"
                "• <i>осматриваюсь по сторонам</i>\n"
                "• <i>иду в лес</i>\n"
                "• <i>атакую гоблина</i>")
    elif action_count == 2:
        hint = ("💡 <b>Совет:</b> Открой меню кнопкой <b>🎮 Игра</b>\n"
                "Там инвентарь, магазин, скилы и квесты.")
    elif action_count == 3:
        hint = ("💡 <b>Совет:</b> Не забудь про <b>📊 Прогресс</b> — там\n"
                "профиль, достижения и награды.")
    else:
        return
    try:
        await g.bot.send_message(chat_id, hint, parse_mode="HTML")
    except Exception as e:
        logging.debug(f"new player hint error: {e}")


async def check_lost_hint(uid, chat_id):
    """Игрок 3 раза подряд нажал непонятное — предложить помощь."""
    try:
        await g.bot.send_message(
            chat_id,
            "🤔 <b>Похоже, что-то идёт не так?</b>\n\n"
            "Открой ❓ <b>Помощь</b> — там подсказки по всем разделам.\n"
            "Или напиши /help.",
            parse_mode="HTML")
    except Exception as e:
        logging.debug(f"lost hint error: {e}")
