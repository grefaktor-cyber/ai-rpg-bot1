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
# (заменим FREE_DAILY_LIMIT после Этапа 1)
FREE_DAILY_LIMIT = 10

# ================= ПРЕМИУМ =================
PREMIUM_PRICE_STARS = 150

# ================= МАРКЕР ИИ =================
AI_MARKER = "🤖 Сгенерировано ИИ"
