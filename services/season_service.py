"""Логика сезонов: проверка конца, награды, старт нового."""
import logging
from datetime import datetime, timezone, timedelta

from aiogram.enums import ParseMode

from core import globals as g
from core.seasons import (
    SEASON_DURATION_DAYS, SEASON_REWARDS, TOP10_GOLD, TOP10_TITLE,
    JOURNAL_ENTRY,
)


async def ensure_season():
    """Проверить: есть ли активный сезон? Если нет — создать 1-й."""
    current = await g.db.get_current_season()
    if current:
        return current
    new = await g.db.create_season(1)
    logging.info(f"✅ Создан сезон #{new['id']}")
    return await g.db.get_current_season()


def _days_left(started_at):
    """Сколько дней до конца сезона."""
    now = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    end = started_at + timedelta(days=SEASON_DURATION_DAYS)
    delta = end - now
    return max(0, delta.days)


async def check_season_end():
    """Проверить окончание. Вызывается в cron раз в час."""
    current = await g.db.get_current_season()
    if not current:
        await ensure_season()
        return None

    started = current["started_at"]
    if started is None:
        return None

    now = datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)

    days_passed = (now - started).days
    if days_passed < SEASON_DURATION_DAYS:
        return None

    # Сезон окончен
    season_number = current["number"]
    await _award_rewards(current["id"], season_number)
    await g.db.close_season(current["id"])

    new_number = season_number + 1
    await g.db.reset_all_season_xp(new_number)
    await g.db.create_season(new_number)

    # Broadcast всем
    async with g.db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE char_name!=''")
    for r in rows:
        try:
            await g.bot.send_message(
                r["user_id"],
                f"🏁 <b>Сезон #{season_number} завершён!</b>\n\n"
                f"Награды выданы. Стартует <b>сезон #{new_number}</b>!\n"
                f"<i>Прогресс сезона обнулён. Удачи!</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    logging.info(f"✅ Сезон #{season_number} → #{new_number}")
    return new_number


async def _award_rewards(season_id, season_number):
    """Выдать награды топ-10."""
    top = await g.db.get_season_top(limit=10)
    if not top:
        return

    for i, entry in enumerate(top, start=1):
        uid = entry["user_id"]
        name = entry["char_name"]

        if i in SEASON_REWARDS:
            reward = SEASON_REWARDS[i]
            await g.db.add_gold(uid, reward["gold"])
            if reward.get("item"):
                await g.db.add_item(uid, reward["item"])
            title_code = reward["title"]
            await g.db.add_season_title(uid, title_code)

            entry_text = JOURNAL_ENTRY.get(i, "🏆 Топ сезона #{number}")
            await g.db.add_journal_entry(
                uid, entry_text.format(number=season_number), "season"
            )

            text = (
                f"🏆 <b>Сезон #{season_number} завершён!</b>\n\n"
                f"Ты занял <b>{i} место</b>!\n\n"
                f"💰 +{reward['gold']} золота\n"
                f"🎖 Титул: <b>{title_code}</b>"
            )
            if reward.get("item"):
                text += f"\n🎁 Предмет: {reward['item']}"
        else:
            await g.db.add_gold(uid, TOP10_GOLD)
            await g.db.add_season_title(uid, TOP10_TITLE)
            await g.db.add_journal_entry(
                uid, f"⭐ Топ-10 сезона #{season_number}", "season"
            )
            text = (
                f"⭐ <b>Сезон #{season_number} завершён!</b>\n\n"
                f"Ты в <b>топ-10</b> ({i} место)!\n\n"
                f"💰 +{TOP10_GOLD} золота\n"
                f"🎖 Титул: <b>{TOP10_TITLE}</b>"
            )

        try:
            await g.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def get_season_info():
    """Информация о текущем сезоне для /season."""
    current = await g.db.get_current_season()
    if not current:
        current = await ensure_season()
    return {
        "number": current["number"],
        "days_left": _days_left(current["started_at"]),
    }
