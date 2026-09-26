import asyncpg
import os
from datetime import date, datetime

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
                    referral_count INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_daily TEXT,
                    daily_streak INTEGER DEFAULT 0,
                    arc INTEGER DEFAULT 1,
                    action_count INTEGER DEFAULT 0,
                    location TEXT DEFAULT 'Начальная деревня'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    item_name TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    location_name TEXT,
                    visited_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, location_name)
                )
            """)

    async def get_user(self, user_id, username=""):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
            if not row:
                await conn.execute("""
                    INSERT INTO users (user_id, username, last_reset) VALUES ($1,$2,$3)
                """, user_id, username, today)
                return await self._empty_user(user_id)
            if row["last_reset"] != today:
                await conn.execute("""
                    UPDATE users SET requests_today=0, last_reset=$1 WHERE user_id=$2
                """, today, user_id)
                d = dict(row); d["requests_today"] = 0
                return d
            return dict(row)

    def _empty_user(self, user_id):
        return {"user_id": user_id, "is_premium": 0, "requests_today": 0,
                "story": "", "consent_given": 0, "referred_by": 0,
                "referral_count": 0, "xp": 0, "level": 1, "last_daily": None,
                "daily_streak": 0, "arc": 1, "action_count": 0,
                "location": "Начальная деревня"}

    async def give_consent(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET consent_given=1, consent_date=$1 WHERE user_id=$2",
                               str(date.today()), user_id)

    async def revoke_consent(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET consent_given=0, story='' WHERE user_id=$1", user_id)

    async def set_referrer(self, user_id, referrer_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT referred_by FROM users WHERE user_id=$1", user_id)
            if row and row["referred_by"] == 0 and referrer_id != user_id:
                await conn.execute("UPDATE users SET referred_by=$1 WHERE user_id=$2",
                                   referrer_id, user_id)
                await conn.execute("""
                    UPDATE users SET referral_count=referral_count+1,
                    requests_today=GREATEST(0, requests_today-10) WHERE user_id=$1
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
            await conn.execute("UPDATE users SET is_premium=$1 WHERE user_id=$2", value, user_id)

    async def add_xp(self, user_id, amount=10):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT xp, level FROM users WHERE user_id=$1", user_id)
            new_xp = row["xp"] + amount
            level = row["level"]
            leveled_up = False
            while new_xp >= (level * level * 100):
                new_xp -= level * level * 100
                level += 1
                leveled_up = True
            await conn.execute("UPDATE users SET xp=$1, level=$2 WHERE user_id=$3",
                               new_xp, level, user_id)
            return (level, new_xp, leveled_up)

    async def incr_action_count(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET action_count=action_count+1, arc=arc+1 WHERE user_id=$1
            """, user_id)
            row = await conn.fetchrow("SELECT action_count, arc FROM users WHERE user_id=$1", user_id)
            return row["action_count"], row["arc"]

    async def add_item(self, user_id, item_name):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (user_id, item_name) VALUES ($1,$2)",
                               user_id, item_name)

    async def get_inventory(self, user_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT item_name FROM inventory WHERE user_id=$1 ORDER BY created_at",
                                    user_id)
            return [r["item_name"] for r in rows]

    async def add_location(self, user_id, location):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO locations (user_id, location_name) VALUES ($1,$2)
                ON CONFLICT (user_id, location_name) DO NOTHING
            """, user_id, location)
            await conn.execute("UPDATE users SET location=$1 WHERE user_id=$2", location, user_id)

    async def get_locations(self, user_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT location_name FROM locations WHERE user_id=$1 ORDER BY visited_at",
                                    user_id)
            return [r["location_name"] for r in rows]

    async def claim_daily(self, user_id):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT last_daily, daily_streak FROM users WHERE user_id=$1", user_id)
            if row["last_daily"] == today:
                return None
            yesterday = str(date.fromordinal(date.today().toordinal() - 1))
            streak = row["daily_streak"] + 1 if row["last_daily"] == yesterday else 1
            await conn.execute("""
                UPDATE users SET last_daily=$1, daily_streak=$2,
                requests_today=GREATEST(0, requests_today-$3) WHERE user_id=$4
            """, today, streak, 5, user_id))
            return streak
