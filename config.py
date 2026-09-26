import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")

# ID админов через запятую (пример: "123456,789012")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

FREE_DAILY_LIMIT = 10
PREMIUM_PRICE_STARS = 100
AI_MARKER = "🤖 Сгенерировано ИИ"
