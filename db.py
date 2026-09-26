import asyncpg
import os
from datetime import date

DATABASE_URL = os.environ.get("DATABASE_URL", "")

class DB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    is_premium INTEGER DEFAULT 0,
                    requests_today INTEGER DEFAULT 0,
                    last_reset TEXT,
                    story TEXT DEFAULT '',
                    consent_given INTEGER DEFAULT 0,
                    consent_date TEXT,
                    referred_by BIGINT DEFAULT 0,
                    referral_count INTEGER DEFAULT 0
                )
            """)

    async def get_user(self, user_id, username=""):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, is_premium, requests_today, last_reset, story,
                       consent_given, referred_by, referral_count
                FROM users WHERE user_id=$1
            """, user_id)
            if not row:
                await conn.execute("""
                    INSERT INTO users (user_id, username, last_reset)
                    VALUES ($1, $2, $3)
                """, user_id, username, today)
                return {"user_id": user_id, "is_premium": 0, "requests_today": 0,
                        "story": "", "consent_given": 0, "referred_by": 0, "referral_count": 0}
            if row["last_reset"] != today:
                await conn.execute("""
                    UPDATE users SET requests_today=0, last_reset=$1 WHERE user_id=$2
                """, today, user_id)
                return {"user_id": row["user_id"], "is_premium": row["is_premium"],
                        "requests_today": 0, "story": row["story"],
                        "consent_given": row["consent_given"],
                        "referred_by": row["referred_by"], "referral_count": row["referral_count"]}
            return {"user_id": row["user_id"], "is_premium": row["is_premium"],
                    "requests_today": row["requests_today"], "story": row["story"],
                    "consent_given": row["consent_given"],
                    "referred_by": row["referred_by"], "referral_count": row["referral_count"]}

    async def give_consent(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET consent_given=1, consent_date=$1 WHERE user_id=$2
            """, str(date.today()), user_id)

    async def revoke_consent(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET consent_given=0, story='' WHERE user_id=$1
            """, user_id)

    async def set_referrer(self, user_id, referrer_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT referred_by FROM users WHERE user_id=$1", user_id)
            if row and row["referred_by"] == 0 and referrer_id != user_id:
                await conn.execute("UPDATE users SET referred_by=$1 WHERE user_id=$2",
                                   referrer_id, user_id)
                await conn.execute("""
                    UPDATE users SET referral_count=referral_count+1,
                    requests_today=GREATEST(0, requests_today-10)
                    WHERE user_id=$1
                """, referrer_id)
                return True
            return False

    async def increment(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET requests_today=requests_today+1 WHERE user_id=$1",
                               user_id)

    async def update_story(self, user_id, story):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET story=$1 WHERE user_id=$2", story, user_id)

    async def set_premium(self, user_id, value=1):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_premium=$1 WHERE user_id=$2",
                               value, user_id)
