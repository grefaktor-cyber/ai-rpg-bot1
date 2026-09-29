"""Система энергии — заменяет дневные лимиты действий."""
from datetime import datetime, timedelta


# ================= КОНСТАНТЫ =================
ENERGY_BASE = 20            # базовый максимум
ENERGY_PER_LEVEL = 2        # +2 к максимуму за уровень
ENERGY_PER_REFERRAL = 10    # +10 за друга
REGEN_MINUTES = 30          # +1 каждые 30 минут
REGEN_MINUTES_PREMIUM = 15  # премиум: +1 каждые 15 минут


def get_max_energy(user):
    """Максимум энергии с учётом уровня, рефералов и премиума."""
    base = ENERGY_BASE + user.get("level", 1) * ENERGY_PER_LEVEL
    base += user.get("referral_count", 0) * ENERGY_PER_REFERRAL
    if user.get("is_premium"):
        base = int(base * 1.5)
    return base


def calculate_current_energy(user):
    """Текущая энергия с учётом времени, прошедшего с последнего действия.
    
    Возвращает (current, seconds_to_next).
    """
    max_e = get_max_energy(user)
    current = user.get("energy", max_e)
    last_update = user.get("energy_updated_at")

    # Если даты нет или энергия уже полная
    if not last_update or current >= max_e:
        return max_e if current >= max_e else current, 0

    # Парсим дату последнего обновления
    try:
        if isinstance(last_update, str):
            last_dt = datetime.fromisoformat(last_update)
        else:
            last_dt = last_update
    except (ValueError, TypeError):
        return current, 0

    now = datetime.utcnow()
    elapsed = now - last_dt
    elapsed_minutes = int(elapsed.total_seconds() // 60)

    regen_interval = REGEN_MINUTES_PREMIUM if user.get("is_premium") else REGEN_MINUTES
    regen = elapsed_minutes // regen_interval

    if regen <= 0:
        # Сколько осталось до следующей единицы
        seconds_to_next = regen_interval * 60 - (elapsed.total_seconds() % (regen_interval * 60))
        return current, int(seconds_to_next)

    new_energy = min(max_e, current + regen)
    return new_energy, 0


def format_time_to_next(seconds):
    """Красивое отображение 'до следующей энергии'."""
    if seconds <= 0:
        return "сейчас"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}ч {mins}м"


def can_act(user, cost=1):
    """Хватает ли энергии на действие."""
    current, _ = calculate_current_energy(user)
    return current >= cost, current


def spend_energy(user, cost=1):
    """Списать энергию (для сохранения в БД).
    Возвращает (успех, новая_энергия).
    """
    current, _ = calculate_current_energy(user)
    if current < cost:
        return False, current
    return True, current - cost


def is_full(user):
    """Полная ли энергия."""
    current, _ = calculate_current_energy(user)
    return current >= get_max_energy(user)
