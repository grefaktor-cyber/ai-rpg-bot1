"""Ежедневные испытания — новый челлендж каждый день.

Логика:
- Каждый день выбирается 1 испытание
- Прогресс копится в БД (daily_quests, type='challenge')
- При выполнении — награда
"""
import random
from datetime import date

# Пул испытаний
CHALLENGES = [
    {
        "code": "kill_10",
        "title": "Охотник",
        "desc": "Убей 10 врагов в бою",
        "target": 10,
        "reward_gold": 300,
        "reward_xp": 250,
        "reward_qp": 5,
    },
    {
        "code": "kill_25",
        "title": "Массовый убийца",
        "desc": "Убей 25 врагов в бою",
        "target": 25,
        "reward_gold": 700,
        "reward_xp": 600,
        "reward_qp": 10,
    },
    {
        "code": "kill_boss_1",
        "title": "Гроза боссов",
        "desc": "Победи 1 босса",
        "target": 1,
        "reward_gold": 500,
        "reward_xp": 400,
        "reward_qp": 8,
    },
    {
        "code": "visit_3",
        "title": "Путешественник",
        "desc": "Посети 3 локации",
        "target": 3,
        "reward_gold": 200,
        "reward_xp": 150,
        "reward_qp": 3,
    },
    {
        "code": "win_duel_2",
        "title": "Дуэлянт",
        "desc": "Выиграй 2 дуэли",
        "target": 2,
        "reward_gold": 600,
        "reward_xp": 500,
        "reward_qp": 8,
    },
    {
        "code": "use_spoil_3",
        "title": "Обчистка",
        "desc": "Используй спойл 3 раза (только Убийца/Плут/Охотник)",
        "target": 3,
        "reward_gold": 400,
        "reward_xp": 300,
        "reward_qp": 5,
    },
    {
        "code": "win_pvp_arena",
        "title": "Хозяин арены",
        "desc": "Выиграй 1 PvP дуэль без зелий",
        "target": 1,
        "reward_gold": 800,
        "reward_xp": 700,
        "reward_qp": 12,
        # флаг для проверки что зелий не использовали
        "no_potions": True,
    },
    {
        "code": "damage_5000",
        "title": "Тяжёлая рука",
        "desc": "Нанеси 5000 урона",
        "target": 5000,
        "reward_gold": 500,
        "reward_xp": 400,
        "reward_qp": 6,
    },
    {
        "code": "crit_5",
        "title": "Крит-машина",
        "desc": "Нанеси 5 критических ударов",
        "target": 5,
        "reward_gold": 400,
        "reward_xp": 300,
        "reward_qp": 5,
    },
    {
        "code": "survive_5",
        "title": "Живучий",
        "desc": "Победи 5 врагов подряд без смертей",
        "target": 5,
        "reward_gold": 500,
        "reward_xp": 450,
        "reward_qp": 7,
    },
]


def get_daily_challenge():
    """Возвращает испытание дня. Детерминированно от даты."""
    today = date.today()
    # Стабильный "random" — используем день года как seed
    seed = today.year * 1000 + today.timetuple().tm_yday
    rng = random.Random(seed)
    return rng.choice(CHALLENGES)


def get_challenge_by_code(code):
    for c in CHALLENGES:
        if c["code"] == code:
            return c
    return None
