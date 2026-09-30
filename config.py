"""Конфиг: токены, админы, энергия, премиум."""
import os

# ================= ТОКЕНЫ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")

# ================= АДМИНЫ =================
ADMIN_IDS = [
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip()
]

# ================= ЭНЕРГИЯ =================
ENERGY_BASE = 20              # базовый максимум
ENERGY_PER_LEVEL = 2          # +2 за уровень
ENERGY_PER_REFERRAL = 10      # +10 за каждого приглашённого
ENERGY_REGEN_MINUTES = 30     # +1 каждые 30 минут
ENERGY_PREMIUM_MAX_MULT = 1.5 # максимум ×1.5 для премиума
ENERGY_PREMIUM_REGEN = 2      # регенерация ×2 для премиума

# Старое поле (не используется, но нужно для совместимости)
FREE_DAILY_LIMIT = 10

# ================= ПРЕМИУМ =================
PREMIUM_PRICE_STARS = 150

# ================= МАРКЕР ИИ =================
AI_MARKER = "🤖 Сгенерировано ИИ"
