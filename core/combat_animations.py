"""Анимации боя: удары, криты, HP, лут, смерть.

Все функции обёрнуты в try/except — если что-то падает, бой продолжается.
Длительность анимаций: 0.6-1.5 сек, чтобы не раздражать игрока.
"""
import asyncio
import logging
import re

from aiogram.enums import ParseMode

from core import globals as g


def _hp_bar(hp, max_hp, length=15):
    if max_hp <= 0:
        return "░" * length
    pct = max(0.0, min(1.0, hp / max_hp))
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def extract_dmg(log_line):
    """Извлекает число урона из строки лога: '⚔️ 47 урона' → 47."""
    m = re.search(r'(\d+)\s+урона', log_line)
    return int(m.group(1)) if m else 0


async def animate_attack(edit_message, dmg, enemy_name, is_crit=False):
    """Анимация атаки игрока по врагу."""
    if not edit_message or dmg <= 0:
        return
    try:
        if is_crit:
            frames = [
                ("⚔️ <i>Замах...</i>", 0.25),
                ("⚡ ⚡ ⚡ <b>КРИТ!</b>", 0.35),
                (f"💥 <b>{dmg}</b> урона по <b>{enemy_name}</b>!", 0.4),
            ]
        else:
            frames = [
                ("⚔️ <i>Удар...</i>", 0.22),
                (f"💥 <b>{dmg}</b> урона по <b>{enemy_name}</b>", 0.3),
            ]
        for text, delay in frames:
            try:
                await edit_message.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            await asyncio.sleep(delay)
    except Exception as e:
        logging.debug(f"[ANIM ATTACK] {e}")


async def animate_hp_drop(edit_message, player_name, hp_from, hp_to, max_hp):
    """Плавное падение HP игрока (4 кадра)."""
    if not edit_message or hp_to >= hp_from:
        return
    try:
        steps = 4
        header = f"💔 <b>{player_name}</b> получает урон!\n\n"
        for i in range(steps + 1):
            pct = i / steps
            cur = int(hp_from + (hp_to - hp_from) * pct)
            bar = _hp_bar(cur, max_hp, length=15)
            text = header + f"❤️ [{bar}] {cur}/{max_hp}"
            try:
                await edit_message.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            await asyncio.sleep(0.18)
    except Exception as e:
        logging.debug(f"[ANIM HP] {e}")


async def animate_victory_kill(edit_message, enemy_name):
    """Короткая анимация добивания врага."""
    if not edit_message:
        return
    frames = [
        ("⚔️ <i>Финальный удар...</i>", 0.35),
        (f"🏆 <b>{enemy_name}</b> повержен!", 0.5),
    ]
    try:
        for text, delay in frames:
            try:
                await edit_message.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            await asyncio.sleep(delay)
    except Exception as e:
        logging.debug(f"[ANIM KILL] {e}")


async def animate_loot(chat_id, drops, header="🎁 <b>Добыча:</b>"):
    """Анимация открытия добычи. Сообщение удаляется через 0.7 сек."""
    if not drops:
        return
    sent = None
    try:
        sent = await g.bot.send_message(
            chat_id,
            "🎁 <i>Открываю добычу...</i>",
            parse_mode=ParseMode.HTML,
        )
        await asyncio.sleep(0.4)

        loot_text = header + "\n"
        for icon, name in drops:
            loot_text += f"  {icon} <b>{name}</b>\n"
        try:
            await sent.edit_text(loot_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await asyncio.sleep(0.7)
    except Exception as e:
        logging.debug(f"[ANIM LOOT] {e}")
    finally:
        if sent:
            try:
                await sent.delete()
            except Exception:
                pass


async def animate_death(chat_id):
    """Анимация смерти. Создаёт сообщение, редактирует и удаляет."""
    try:
        msg = await g.bot.send_message(
            chat_id,
            "💀 <i>Ты падаешь...</i>",
            parse_mode=ParseMode.HTML,
        )
        await asyncio.sleep(0.45)
        try:
            await msg.edit_text("💀 💀 <i>Последний вздох...</i>",
                                 parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await asyncio.sleep(0.45)
        try:
            await msg.edit_text("💀 💀 💀 <i>Тьма.</i>",
                                 parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await asyncio.sleep(0.5)
        try:
            await msg.delete()
        except Exception:
            pass
    except Exception as e:
        logging.debug(f"[ANIM DEATH] {e}")
