import asyncpg
import os
import logging
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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    code TEXT,
                    earned_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, code)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS world_events (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    event_text TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_combat (
                    user_id BIGINT PRIMARY KEY,
                    enemy_name TEXT,
                    enemy_level INTEGER,
                    enemy_hp INTEGER,
                    enemy_max_hp INTEGER,
                    is_boss INTEGER DEFAULT 0,
                    round_num INTEGER DEFAULT 1,
                    defending INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS graffiti (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    location TEXT,
                    text TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS duel_offers (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT,
                    challenger_name TEXT,
                    opponent_id BIGINT,
                    opponent_name TEXT,
                    stake INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            migrations = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS race TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS class TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS char_name TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_str INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_dex INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_con INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_int INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_wit INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS stat_men INTEGER DEFAULT 5",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS hp INTEGER DEFAULT 100",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_hp INTEGER DEFAULT 100",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS bosses_defeated INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS gold INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_weapon TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_armor TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_accessory TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS deaths INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS reputation INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS pvp_wins INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS pvp_losses INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS is_pvp INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS opponent_id BIGINT DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS stake INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS my_turn INTEGER DEFAULT 1",
            ]
            for sql in migrations:
                try:
                    await conn.execute(sql)
                except Exception as e:
                    logging.warning(f"Migration skipped: {e}")

    # ================= БАЗОВЫЕ =================
    async def get_user(self, user_id, username=""):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
            if not row:
                await conn.execute(
                    "INSERT INTO users (user_id, username, last_reset) VALUES ($1,$2,$3)",
                    user_id, username, today
                )
                return self._empty_user(user_id)
            if row["last_reset"] != today:
                await conn.execute(
                    "UPDATE users SET requests_today=0, last_reset=$1 WHERE user_id=$2",
                    today, user_id
                )
                d = dict(row); d["requests_today"] = 0
                return d
            return dict(row)

    def _empty_user(self, user_id):
        return {"user_id": user_id, "is_premium": 0, "requests_today": 0,
                "story": "", "consent_given": 0, "referred_by": 0,
                "referral_count": 0, "xp": 0, "level": 1, "last_daily": None,
                "daily_streak": 0, "arc": 1, "action_count": 0,
                "location": "Начальная деревня", "race": "", "class": "",
                "char_name": "", "stat_str": 5, "stat_dex": 5, "stat_con": 5,
                "stat_int": 5, "stat_wit": 5, "stat_men": 5,
                "hp": 100, "max_hp": 100, "bosses_defeated": 0,
                "gold": 0, "equipped_weapon": "", "equipped_armor": "",
                "equipped_accessory": "", "deaths": 0, "reputation": 0,
                "pvp_wins": 0, "pvp_losses": 0}

    async def give_consent(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET consent_given=1, consent_date=$1 WHERE user_id=$2",
                str(date.today()), user_id
            )

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
            await conn.execute(
                "UPDATE users SET requests_today=requests_today+1 WHERE user_id=$1", user_id
            )

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
            await conn.execute(
                "UPDATE users SET action_count=action_count+1, arc=arc+1 WHERE user_id=$1", user_id
            )
            row = await conn.fetchrow("SELECT action_count, arc FROM users WHERE user_id=$1", user_id)
            return row["action_count"], row["arc"]

    # ================= ИНВЕНТАРЬ =================
    async def add_item(self, user_id, item_name):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (user_id, item_name) VALUES ($1,$2)",
                               user_id, item_name)

    async def get_inventory(self, user_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT item_name FROM inventory WHERE user_id=$1 ORDER BY created_at", user_id
            )
            return [r["item_name"] for r in rows]

    async def remove_item(self, user_id, item_name):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id FROM inventory WHERE user_id=$1 AND item_name=$2 LIMIT 1
            """, user_id, item_name)
            if row:
                await conn.execute("DELETE FROM inventory WHERE id=$1", row["id"])
                return True
            return False

    # ================= ЛОКАЦИИ =================
    async def add_location(self, user_id, location):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO locations (user_id, location_name) VALUES ($1,$2)
                ON CONFLICT (user_id, location_name) DO NOTHING
            """, user_id, location)
            await conn.execute("UPDATE users SET location=$1 WHERE user_id=$2", location, user_id)

    async def get_locations(self, user_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT location_name FROM locations WHERE user_id=$1 ORDER BY visited_at", user_id
            )
            return [r["location_name"] for r in rows]

    async def get_players_in_location(self, location, exclude_id=0):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, char_name, level, race, class, hp, max_hp
                FROM users WHERE location=$1 AND char_name != '' AND user_id != $2
                ORDER BY level DESC LIMIT 30
            """, location, exclude_id)
            return [dict(r) for r in rows]

    async def get_user_by_char_name(self, char_name):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE LOWER(char_name)=LOWER($1) LIMIT 1", char_name
            )
            return dict(row) if row else None

    # ================= ГРАФФИТИ =================
    async def add_graffiti(self, user_id, username, location, text):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO graffiti (user_id, username, location, text) VALUES ($1,$2,$3,$4)
            """, user_id, username, location, text)

    async def get_graffiti(self, location, limit=15):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT username, text, created_at FROM graffiti
                WHERE location=$1 ORDER BY created_at DESC LIMIT $2
            """, location, limit)
            return [dict(r) for r in rows]

    # ================= ЕЖЕДНЕВНАЯ =================
    async def claim_daily(self, user_id):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT last_daily, daily_streak FROM users WHERE user_id=$1", user_id
            )
            if row["last_daily"] == today:
                return None
            yesterday = str(date.fromordinal(date.today().toordinal() - 1))
            streak = row["daily_streak"] + 1 if row["last_daily"] == yesterday else 1
            if streak > 7:
                streak = 1
            await conn.execute("""
                UPDATE users SET last_daily=$1, daily_streak=$2,
                requests_today=GREATEST(0, requests_today-$3) WHERE user_id=$4
            """, today, streak, 5, user_id)
            return streak

    # ================= СОЗДАНИЕ ГЕРОЯ =================
    async def set_race(self, user_id, race):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET race=$1 WHERE user_id=$2", race, user_id)

    async def set_class(self, user_id, cls):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET class=$1 WHERE user_id=$2", cls, user_id)

    async def set_char(self, user_id, name, stats, hp):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET char_name=$1,
                stat_str=$2, stat_dex=$3, stat_con=$4,
                stat_int=$5, stat_wit=$6, stat_men=$7,
                hp=$8, max_hp=$8, gold=100 WHERE user_id=$9
            """, name, stats["str"], stats["dex"], stats["con"],
                 stats["int"], stats["wit"], stats["men"], hp, user_id)

    # ================= HP / GOLD =================
    async def update_hp(self, user_id, hp):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET hp=$1 WHERE user_id=$2", max(0, hp), user_id)

    async def update_hp_max(self, user_id, hp, max_hp):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET hp=$1, max_hp=$2 WHERE user_id=$3",
                               hp, max_hp, user_id)

    async def add_gold(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET gold=gold+$1 WHERE user_id=$2", amount, user_id
            )

    async def spend_gold(self, user_id, amount):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT gold FROM users WHERE user_id=$1", user_id)
            if row and row["gold"] >= amount:
                await conn.execute("UPDATE users SET gold=gold-$1 WHERE user_id=$2",
                                   amount, user_id)
                return True
            return False

    async def set_gold(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET gold=$1 WHERE user_id=$2", amount, user_id)

    async def incr_bosses(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET bosses_defeated=bosses_defeated+1 WHERE user_id=$1", user_id
            )

    async def incr_deaths(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET deaths=deaths+1 WHERE user_id=$1", user_id)

    async def add_reputation(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET reputation=reputation+$1 WHERE user_id=$2", amount, user_id
            )

    async def incr_pvp_wins(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET pvp_wins=pvp_wins+1 WHERE user_id=$1", user_id
            )

    async def incr_pvp_losses(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET pvp_losses=pvp_losses+1 WHERE user_id=$1", user_id
            )

    # ================= ЭКИПИРОВКА =================
    async def equip_item(self, user_id, slot, item_name):
        col = f"equipped_{slot}"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", user_id)
            old = row[col] if row else ""
            await conn.execute(f"UPDATE users SET {col}=$1 WHERE user_id=$2",
                               item_name, user_id)
            return old

    async def unequip_item(self, user_id, slot):
        col = f"equipped_{slot}"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", user_id)
            old = row[col] if row else ""
            await conn.execute(f"UPDATE users SET {col}='' WHERE user_id=$1", user_id)
            return old

    # ================= РЕЙТИНГ =================
    async def get_top_players(self, limit=10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT char_name, username, level, xp, bosses_defeated, race, class, pvp_wins
                FROM users WHERE race != '' AND char_name != ''
                ORDER BY level DESC, xp DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    async def get_pvp_top(self, limit=10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT char_name, username, level, pvp_wins, pvp_losses, reputation
                FROM users WHERE race != '' AND char_name != '' AND pvp_wins > 0
                ORDER BY pvp_wins DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    # ================= ДОСТИЖЕНИЯ =================
    async def add_achievement(self, user_id, code):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO user_achievements (user_id, code) VALUES ($1,$2)",
                    user_id, code
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_achievements(self, user_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT code, earned_at FROM user_achievements WHERE user_id=$1 ORDER BY earned_at",
                user_id
            )
            return [dict(r) for r in rows]

    # ================= МИР =================
    async def add_world_event(self, user_id, username, text):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO world_events (user_id, username, event_text) VALUES ($1,$2,$3)",
                user_id, username, text
            )

    async def get_world_events(self, limit=10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT username, event_text, created_at FROM world_events
                ORDER BY created_at DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    # ================= БОЙ =================
    async def get_combat(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", user_id)
            return dict(row) if row else None

    async def start_combat(self, user_id, enemy_name, enemy_level, enemy_hp, is_boss=0):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM active_combat WHERE user_id=$1", user_id)
            await conn.execute("""
                INSERT INTO active_combat (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_boss)
                VALUES ($1,$2,$3,$4,$4,$5)
            """, user_id, enemy_name, enemy_level, enemy_hp, is_boss)

    async def update_combat_enemy_hp(self, user_id, enemy_hp):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
                               max(0, enemy_hp), user_id)

    async def set_combat_defending(self, user_id, defending):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE active_combat SET defending=$1 WHERE user_id=$2",
                               defending, user_id)

    async def incr_combat_round(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE active_combat SET round_num=round_num+1 WHERE user_id=$1", user_id)
            row = await conn.fetchrow("SELECT round_num FROM active_combat WHERE user_id=$1", user_id)
            return row["round_num"] if row else 1

    async def end_combat(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM active_combat WHERE user_id=$1", user_id)

    # ================= PVP =================
    async def start_pvp_combat(self, user_a, user_b, stake):
        """Создаёт бой у обоих. A ходит первым."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM active_combat WHERE user_id IN ($1,$2)",
                               user_a["user_id"], user_b["user_id"])
            await conn.execute("""
                INSERT INTO active_combat
                (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,1)
            """, user_a["user_id"], user_b["char_name"], user_b["level"],
                 user_b["hp"], user_b["user_id"], stake)
            await conn.execute("""
                INSERT INTO active_combat
                (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,0)
            """, user_b["user_id"], user_a["char_name"], user_a["level"],
                 user_a["hp"], user_a["user_id"], stake)

    async def pvp_damage(self, attacker_id, damage):
        """Атакующий бьёт противника. Возвращает (opponent_hp, opponent_id, ended)."""
        async with self.pool.acquire() as conn:
            ac = await conn.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", attacker_id)
            if not ac or not ac["is_pvp"]:
                return None
            opp_id = ac["opponent_id"]
            opp = await conn.fetchrow("SELECT hp FROM users WHERE user_id=$1", opp_id)
            new_hp = max(0, opp["hp"] - damage)
            await conn.execute("UPDATE users SET hp=$1 WHERE user_id=$2", new_hp, opp_id)
            await conn.execute("UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2",
                               new_hp, attacker_id)
            return new_hp, opp_id

    async def pvp_switch_turn(self, user_id):
        """Отдаёт ход противнику."""
        async with self.pool.acquire() as conn:
            ac = await conn.fetchrow("SELECT opponent_id FROM active_combat WHERE user_id=$1", user_id)
            if not ac:
                return
            opp_id = ac["opponent_id"]
            await conn.execute("UPDATE active_combat SET my_turn=0 WHERE user_id=$1", user_id)
            await conn.execute("UPDATE active_combat SET my_turn=1, round_num=round_num+1 WHERE user_id=$1", opp_id)

    # ================= ДУЭЛЬНЫЕ ПРЕДЛОЖЕНИЯ =================
    async def create_duel_offer(self, challenger_id, challenger_name, opponent_id, opponent_name, stake):
        async with self.pool.acquire() as conn:
            # Удаляем старые незавершённые
            await conn.execute("""
                DELETE FROM duel_offers WHERE status='pending' AND
                ((challenger_id=$1 AND opponent_id=$2) OR (challenger_id=$2 AND opponent_id=$1))
            """, challenger_id, opponent_id)
            row = await conn.fetchrow("""
                INSERT INTO duel_offers (challenger_id, challenger_name, opponent_id, opponent_name, stake)
                VALUES ($1,$2,$3,$4,$5) RETURNING id
            """, challenger_id, challenger_name, opponent_id, opponent_name, stake)
            return row["id"]

    async def get_duel_offer(self, offer_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM duel_offers WHERE id=$1", offer_id)
            return dict(row) if row else None

    async def get_pending_duel_for(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM duel_offers WHERE opponent_id=$1 AND status='pending'
                ORDER BY created_at DESC LIMIT 1
            """, user_id)
            return dict(row) if row else None

    async def set_duel_status(self, offer_id, status, stake=None):
        async with self.pool.acquire() as conn:
            if stake is not None:
                await conn.execute("UPDATE duel_offers SET status=$1, stake=$2 WHERE id=$3",
                                   status, stake, offer_id)
            else:
                await conn.execute("UPDATE duel_offers SET status=$1 WHERE id=$2",
                                   status, offer_id)

    async def swap_duel_parties(self, offer_id):
        """Меняет местами challenger и opponent (для встречного предложения)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM duel_offers WHERE id=$1", offer_id)
            if not row:
                return
            await conn.execute("""
                UPDATE duel_offers SET
                challenger_id=$1, challenger_name=$2,
                opponent_id=$3, opponent_name=$4,
                status='pending'
                WHERE id=$5
            """, row["opponent_id"], row["opponent_name"],
                 row["challenger_id"], row["challenger_name"], offer_id)
