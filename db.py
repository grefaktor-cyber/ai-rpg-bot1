import asyncpg
import os
import logging
import json
from datetime import date

DATABASE_URL = os.environ.get("DATABASE_URL", "")


class DB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with self.pool.acquire() as conn:
            # ============ ОСНОВНЫЕ ТАБЛИЦЫ ============
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
                    item_level INTEGER DEFAULT 0,
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
                    challenger_id BIGINT, challenger_name TEXT,
                    opponent_id BIGINT, opponent_name TEXT,
                    stake INTEGER, status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    pet_type TEXT,
                    name TEXT,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tutorial_progress (
                    user_id BIGINT PRIMARY KEY,
                    step INTEGER DEFAULT 0,
                    finished INTEGER DEFAULT 0
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    quest_type TEXT,
                    target INTEGER,
                    progress INTEGER DEFAULT 0,
                    reward_gold INTEGER,
                    reward_xp INTEGER,
                    completed INTEGER DEFAULT 0,
                    quest_date TEXT,
                    UNIQUE(user_id, quest_type, quest_date)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE,
                    tag TEXT,
                    leader_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    treasury INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_members (
                    user_id BIGINT PRIMARY KEY,
                    guild_id BIGINT,
                    rank TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS location_owners (
                    location_code TEXT PRIMARY KEY,
                    guild_id BIGINT,
                    captured_at TIMESTAMP DEFAULT NOW(),
                    defense_points INTEGER DEFAULT 100
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS location_bosses (
                    location_code TEXT PRIMARY KEY,
                    boss_name TEXT,
                    killed_at TIMESTAMP,
                    killed_by BIGINT DEFAULT 0
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS npc_quest_progress (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    quest_code TEXT,
                    progress INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    accepted_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, quest_code)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS world_events_dyn (
                    id SERIAL PRIMARY KEY,
                    location_code TEXT,
                    event_code TEXT,
                    event_name TEXT,
                    event_desc TEXT,
                    xp_mult REAL DEFAULT 1.0,
                    gold_mult REAL DEFAULT 1.0,
                    spawn_mult REAL DEFAULT 1.0,
                    enemy_dmg_mult REAL DEFAULT 1.0,
                    started_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """)

            # ============ МИГРАЦИИ ============
            migrations = [
                "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS item_level INTEGER DEFAULT 0",
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
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS faction TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mat_iron INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mat_leather INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mat_dust INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mat_crystal INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS dungeon_id TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS dungeon_room INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS dungeon_loot_gold INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS dungeon_loot_items TEXT DEFAULT '[]'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS location_code TEXT DEFAULT 'village'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS guild_id BIGINT DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS energy INTEGER DEFAULT 20",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS energy_max INTEGER DEFAULT 20",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_energy_regen TIMESTAMP DEFAULT NOW()",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS is_pvp INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS opponent_id BIGINT DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS stake INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS my_turn INTEGER DEFAULT 1",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS is_dungeon INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS next_atk_mult REAL DEFAULT 1.0",
                                # === Этап 2.1: миграция на новые расы/классы ===
                "UPDATE users SET race='', class='', char_name='' WHERE race='dwarf'",
                "UPDATE users SET class='' WHERE race IN ('human','elf','dark_elf','orc') AND class NOT IN ('warrior','knight','mage','archer','guardian','bard','assassin','necro','dancer','destroyer','tyrant','overlord')",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS mp INTEGER DEFAULT 50",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_mp INTEGER DEFAULT 50",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS skill_points INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_skills TEXT DEFAULT '[]'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS learned_skills TEXT DEFAULT '{}'",
            ]
            for sql in migrations:
                try:
                    await conn.execute(sql)
                except Exception as e:
                    logging.warning(f"Migration skipped: {e}")

    # ============ ЭНЕРГИЯ ============
    async def _refresh_energy(self, uid):
        """Пересчитать energy_max, подтянуть energy к росту max + регенерация."""
        async with self.pool.acquire() as c:
            await c.execute("""
                WITH calc AS (
                    SELECT
                        user_id,
                        LEAST(9999, GREATEST(20,
                            ((20 + level * 2 + COALESCE(referral_count, 0) * 10) *
                             (CASE WHEN is_premium=1 THEN 1.5 ELSE 1.0 END))::int
                        ))::int AS new_max,
                        COALESCE(energy, 0) AS old_energy,
                        COALESCE(energy_max, 20) AS old_max,
                        COALESCE(last_energy_regen, NOW()) AS old_regen,
                        is_premium
                    FROM users WHERE user_id = $1
                )
                UPDATE users u SET
                    energy_max = calc.new_max,
                    energy = LEAST(
                        calc.new_max,
                        GREATEST(0,
                            calc.old_energy
                            + GREATEST(0, calc.new_max - calc.old_max)
                            + (FLOOR(EXTRACT(EPOCH FROM (NOW() - calc.old_regen)) / 1800)::int
                               * (CASE WHEN calc.is_premium=1 THEN 2 ELSE 1 END))
                        )
                    )::int,
                    last_energy_regen = CASE
                        WHEN EXTRACT(EPOCH FROM (NOW() - calc.old_regen)) >= 1800
                        THEN NOW()
                        ELSE calc.old_regen
                    END
                FROM calc
                WHERE u.user_id = calc.user_id
            """, uid)

    async def spend_energy(self, uid, amount=1):
        """Списать энергию. Премиум и админ — безлимит."""
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT energy, is_premium FROM users WHERE user_id=$1", uid
            )
            if not row:
                return False
            if row["is_premium"]:
                return True
            if row["energy"] >= amount:
                await c.execute(
                    "UPDATE users SET energy=energy-$1 WHERE user_id=$2",
                    amount, uid
                )
                return True
            return False

    async def get_energy_wait(self, uid):
        """Сколько минут до следующей единицы энергии."""
        async with self.pool.acquire() as c:
            row = await c.fetchrow("""
                SELECT GREATEST(0,
                    30 - FLOOR(EXTRACT(EPOCH FROM (NOW() - COALESCE(last_energy_regen, NOW()))) / 60)
                )::int as wait_min
                FROM users WHERE user_id=$1
            """, uid)
            return row["wait_min"] if row else 30

    # ============ БАЗОВЫЕ ============
    async def get_user(self, user_id, username=""):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
            if not row:
                await conn.execute(
                    "INSERT INTO users (user_id, username, last_reset, last_energy_regen) "
                    "VALUES ($1,$2,$3,NOW())",
                    user_id, username, today
                )
            elif row["last_reset"] != today:
                await conn.execute(
                    "UPDATE users SET requests_today=0, last_reset=$1 WHERE user_id=$2",
                    today, user_id
                )
        await self._refresh_energy(user_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
            return dict(row) if row else self._empty_user(user_id, username)

    def _empty_user(self, uid, username=""):
        return {
            "user_id": uid, "username": username, "is_premium": 0,
            "requests_today": 0, "last_reset": str(date.today()),
            "story": "", "consent_given": 0, "consent_date": None,
            "referred_by": 0, "referral_count": 0, "xp": 0,
            "level": 1, "last_daily": None, "daily_streak": 0, "arc": 1,
            "action_count": 0, "location": "Начальная деревня",
            "location_code": "village", "guild_id": 0,
            "race": "", "class": "", "char_name": "",
            "stat_str": 5, "stat_dex": 5, "stat_con": 5,
            "stat_int": 5, "stat_wit": 5, "stat_men": 5,
            "hp": 100, "max_hp": 100, "bosses_defeated": 0,
            "gold": 0, "equipped_weapon": "", "equipped_armor": "",
            "equipped_accessory": "", "deaths": 0, "reputation": 0,
            "pvp_wins": 0, "pvp_losses": 0, "faction": "",
            "mat_iron": 0, "mat_leather": 0, "mat_dust": 0, "mat_crystal": 0,
            "dungeon_id": "", "dungeon_room": 0,
            "dungeon_loot_gold": 0, "dungeon_loot_items": "[]",
            "energy": 20, "energy_max": 20, "last_energy_regen": None,
            "mp": 50, "max_mp": 50,
            "skill_points": 0, "active_skills": "[]", "learned_skills": "{}",
        }

    async def give_consent(self, uid):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET consent_given=1, consent_date=$1 WHERE user_id=$2",
                str(date.today()), uid
            )

    async def revoke_consent(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET consent_given=0, story='' WHERE user_id=$1", uid)

    async def set_referrer(self, uid, ref):
        """+10 к максимуму энергии за каждого приглашённого (навсегда)."""
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT referred_by FROM users WHERE user_id=$1", uid)
            if row and row["referred_by"] == 0 and ref != uid:
                await c.execute("UPDATE users SET referred_by=$1 WHERE user_id=$2", ref, uid)
                await c.execute(
                    "UPDATE users SET referral_count=referral_count+1 WHERE user_id=$1",
                    ref
                )
        await self._refresh_energy(ref)
        return True

    async def increment(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET requests_today=requests_today+1 WHERE user_id=$1", uid)

    async def update_story(self, uid, s):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET story=$1 WHERE user_id=$2", s, uid)

    async def set_premium(self, uid, v=1):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET is_premium=$1 WHERE user_id=$2", v, uid)
        await self._refresh_energy(uid)

    async def add_xp(self, uid, amount):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT xp, level FROM users WHERE user_id=$1", uid)
            nx = row["xp"] + amount
            lvl = row["level"]
            up = False
            while nx >= lvl * lvl * 100:
                nx -= lvl * lvl * 100
                lvl += 1
                up = True
            await c.execute("UPDATE users SET xp=$1, level=$2 WHERE user_id=$3", nx, lvl, uid)
        if up:
            await self._refresh_energy(uid)
        return (lvl, nx, up)

    async def incr_action_count(self, uid):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET action_count=action_count+1, arc=arc+1 WHERE user_id=$1", uid
            )
            row = await c.fetchrow(
                "SELECT action_count, arc FROM users WHERE user_id=$1", uid
            )
            return row["action_count"], row["arc"]

    # ============ ИНВЕНТАРЬ ============
    async def add_item(self, uid, item, lvl=0):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO inventory (user_id, item_name, item_level) VALUES ($1,$2,$3)",
                uid, item, lvl
            )

    async def get_inventory(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT item_name, item_level FROM inventory "
                "WHERE user_id=$1 ORDER BY created_at", uid
            )
            return [dict(r) for r in rows]

    async def remove_item(self, uid, item, lvl=0):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT id FROM inventory WHERE user_id=$1 AND item_name=$2 "
                "AND item_level=$3 LIMIT 1",
                uid, item, lvl
            )
            if row:
                await c.execute("DELETE FROM inventory WHERE id=$1", row["id"])
                return True
        return False

    # ============ ЛОКАЦИИ / ГРАФФИТИ ============
    async def add_location(self, uid, loc):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO locations (user_id, location_name) VALUES ($1,$2) "
                "ON CONFLICT DO NOTHING", uid, loc
            )
            await c.execute("UPDATE users SET location=$1 WHERE user_id=$2", loc, uid)

    async def get_locations(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT location_name FROM locations WHERE user_id=$1 ORDER BY visited_at", uid
            )
            return [r["location_name"] for r in rows]

    async def get_user_by_char_name(self, name):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT * FROM users WHERE LOWER(char_name)=LOWER($1) LIMIT 1", name
            )
            return dict(row) if row else None

    async def add_graffiti(self, uid, uname, loc, text):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO graffiti (user_id, username, location, text) VALUES ($1,$2,$3,$4)",
                uid, uname, loc, text
            )

    async def get_graffiti(self, loc, limit=15):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT username, text FROM graffiti WHERE location=$1 "
                "ORDER BY created_at DESC LIMIT $2", loc, limit
            )
            return [dict(r) for r in rows]

    # ============ ЕЖЕДНЕВНАЯ ============
    async def claim_daily(self, uid):
        today = str(date.today())
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT last_daily, daily_streak FROM users WHERE user_id=$1", uid
            )
            if row["last_daily"] == today:
                return None
            y = str(date.fromordinal(date.today().toordinal() - 1))
            streak = row["daily_streak"] + 1 if row["last_daily"] == y else 1
            if streak > 7:
                streak = 1
            await c.execute(
                "UPDATE users SET last_daily=$1, daily_streak=$2, "
                "energy=energy_max, last_energy_regen=NOW() WHERE user_id=$3",
                today, streak, uid
            )
            return streak

    # ============ ГЕРОЙ ============
    async def set_race(self, uid, r):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET race=$1 WHERE user_id=$2", r, uid)

    async def set_class(self, uid, cl):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET class=$1 WHERE user_id=$2", cl, uid)

    async def set_faction(self, uid, f):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET faction=$1 WHERE user_id=$2", f, uid)

    async def set_char(self, uid, name, stats, hp):
        async with self.pool.acquire() as c:
            await c.execute("""UPDATE users SET char_name=$1,
                stat_str=$2, stat_dex=$3, stat_con=$4, stat_int=$5, stat_wit=$6, stat_men=$7,
                hp=$8, max_hp=$8, gold=100 WHERE user_id=$9""",
                            name, stats["str"], stats["dex"], stats["con"],
                            stats["int"], stats["wit"], stats["men"], hp, uid)
        await self._refresh_energy(uid)
        
            async def update_stats(self, uid, stats, hp=None, mp=None):
        """Обновить статы персонажа (при смене класса)."""
        async with self.pool.acquire() as c:
            await c.execute("""UPDATE users SET
                stat_str=$1, stat_dex=$2, stat_con=$3,
                stat_int=$4, stat_wit=$5, stat_men=$6
                WHERE user_id=$7""",
                stats["str"], stats["dex"], stats["con"],
                stats["int"], stats["wit"], stats["men"], uid)
            if hp is not None:
                await c.execute(
                    "UPDATE users SET hp=$1, max_hp=$1 WHERE user_id=$2", hp, uid
                )
            if mp is not None:
                await c.execute(
                    "UPDATE users SET mp=$1, max_mp=$1 WHERE user_id=$2", mp, uid
                )

    # ============ HP / GOLD / РЕПУТАЦИЯ ============
    async def update_hp(self, uid, hp):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET hp=$1 WHERE user_id=$2", max(0, hp), uid)

    async def update_hp_max(self, uid, hp, mx):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET hp=$1, max_hp=$2 WHERE user_id=$3", hp, mx, uid)

    async def add_gold(self, uid, amt):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET gold=gold+$1 WHERE user_id=$2", amt, uid)

    async def spend_gold(self, uid, amt):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT gold FROM users WHERE user_id=$1", uid)
            if row and row["gold"] >= amt:
                await c.execute("UPDATE users SET gold=gold-$1 WHERE user_id=$2", amt, uid)
                return True
        return False

    async def set_gold(self, uid, amt):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET gold=$1 WHERE user_id=$2", amt, uid)

    async def incr_bosses(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET bosses_defeated=bosses_defeated+1 WHERE user_id=$1", uid)

    async def incr_deaths(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET deaths=deaths+1 WHERE user_id=$1", uid)

    async def add_reputation(self, uid, amt):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET reputation=reputation+$1 WHERE user_id=$2", amt, uid)

    async def incr_pvp_wins(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET pvp_wins=pvp_wins+1 WHERE user_id=$1", uid)

    async def incr_pvp_losses(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET pvp_losses=pvp_losses+1 WHERE user_id=$1", uid)

    # ============ ЭКИПИРОВКА ============
    async def equip_item(self, uid, slot, item):
        col = f"equipped_{slot}"
        async with self.pool.acquire() as c:
            row = await c.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", uid)
            old = row[col] if row else ""
            await c.execute(f"UPDATE users SET {col}=$1 WHERE user_id=$2", item, uid)
            return old

    async def unequip_item(self, uid, slot):
        col = f"equipped_{slot}"
        async with self.pool.acquire() as c:
            row = await c.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", uid)
            old = row[col] if row else ""
            await c.execute(f"UPDATE users SET {col}='' WHERE user_id=$1", uid)
            return old

    # ============ РЕЙТИНГИ ============
    async def get_top_players(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT char_name, username, level, xp, bosses_defeated, race, class, faction
                FROM users WHERE race!='' AND char_name!=''
                ORDER BY level DESC, xp DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    async def get_pvp_top(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT char_name, pvp_wins, pvp_losses, reputation
                FROM users WHERE race!='' AND pvp_wins>0
                ORDER BY pvp_wins DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    # ============ ДОСТИЖЕНИЯ ============
    async def add_achievement(self, uid, code):
        async with self.pool.acquire() as c:
            try:
                await c.execute(
                    "INSERT INTO user_achievements (user_id, code) VALUES ($1,$2)", uid, code
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_achievements(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT code FROM user_achievements WHERE user_id=$1", uid)
            return [dict(r) for r in rows]

    # ============ МИР (события) ============
    async def add_world_event(self, uid, uname, text):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO world_events (user_id, username, event_text) VALUES ($1,$2,$3)",
                uid, uname, text
            )

    async def get_world_events(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT username, event_text FROM world_events "
                "ORDER BY created_at DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]

    # ============ БОЙ ============
    async def get_combat(self, uid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", uid)
            return dict(row) if row else None

    async def start_combat(self, uid, name, lvl, hp, boss=0, dungeon=0):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM active_combat WHERE user_id=$1", uid)
            await c.execute("""
                INSERT INTO active_combat
                (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_boss, is_dungeon)
                VALUES ($1,$2,$3,$4,$4,$5,$6)
            """, uid, name, lvl, hp, boss, dungeon)

    async def update_combat_enemy_hp(self, uid, hp):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2", max(0, hp), uid
            )

    async def set_combat_defending(self, uid, d):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE active_combat SET defending=$1 WHERE user_id=$2", d, uid)

    async def incr_combat_round(self, uid):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE active_combat SET round_num=round_num+1 WHERE user_id=$1", uid
            )

    async def end_combat(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM active_combat WHERE user_id=$1", uid)

    # ============ PVP ============
    async def start_pvp_combat(self, a, b, stake):
        async with self.pool.acquire() as c:
            await c.execute(
                "DELETE FROM active_combat WHERE user_id IN ($1,$2)",
                a["user_id"], b["user_id"]
            )
            await c.execute("""
                INSERT INTO active_combat
                (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp,
                 is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,1)
            """, a["user_id"], b["char_name"], b["level"], b["hp"], b["user_id"], stake)
            await c.execute("""
                INSERT INTO active_combat
                (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp,
                 is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,0)
            """, b["user_id"], a["char_name"], a["level"], a["hp"], a["user_id"], stake)

    async def pvp_damage(self, aid, dmg):
        async with self.pool.acquire() as c:
            ac = await c.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", aid)
            if not ac or not ac["is_pvp"]:
                return None
            opp_id = ac["opponent_id"]
            opp = await c.fetchrow("SELECT hp FROM users WHERE user_id=$1", opp_id)
            nhp = max(0, opp["hp"] - dmg)
            await c.execute("UPDATE users SET hp=$1 WHERE user_id=$2", nhp, opp_id)
            await c.execute(
                "UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2", nhp, aid
            )
            return nhp, opp_id

    async def pvp_switch_turn(self, uid):
        async with self.pool.acquire() as c:
            ac = await c.fetchrow(
                "SELECT opponent_id FROM active_combat WHERE user_id=$1", uid
            )
            if not ac:
                return
            opp = ac["opponent_id"]
            await c.execute("UPDATE active_combat SET my_turn=0 WHERE user_id=$1", uid)
            await c.execute(
                "UPDATE active_combat SET my_turn=1, round_num=round_num+1 WHERE user_id=$1", opp
            )

    # ============ ДУЭЛИ ============
    async def create_duel_offer(self, cid, cname, oid, oname, stake):
        async with self.pool.acquire() as c:
            await c.execute("""
                DELETE FROM duel_offers WHERE status='pending' AND
                ((challenger_id=$1 AND opponent_id=$2) OR (challenger_id=$2 AND opponent_id=$1))
            """, cid, oid)
            row = await c.fetchrow("""
                INSERT INTO duel_offers
                (challenger_id, challenger_name, opponent_id, opponent_name, stake)
                VALUES ($1,$2,$3,$4,$5) RETURNING id
            """, cid, cname, oid, oname, stake)
            return row["id"]

    async def get_duel_offer(self, oid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM duel_offers WHERE id=$1", oid)
            return dict(row) if row else None

    async def set_duel_status(self, oid, status):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE duel_offers SET status=$1 WHERE id=$2", status, oid)

    # ============ ПИТОМЦЫ ============
    async def get_pet(self, uid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM pets WHERE user_id=$1", uid)
            return dict(row) if row else None

    async def add_pet(self, uid, ptype, name):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO pets (user_id, pet_type, name) VALUES ($1,$2,$3)",
                uid, ptype, name
            )

    async def set_pet_name(self, uid, name):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE pets SET name=$1 WHERE user_id=$2", name, uid)

    async def add_pet_xp(self, uid, amount):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT level, xp FROM pets WHERE user_id=$1", uid)
            if not row:
                return 1
            nx = row["xp"] + amount
            lvl = row["level"]
            while nx >= lvl * 100:
                nx -= lvl * 100
                lvl += 1
            await c.execute(
                "UPDATE pets SET level=$1, xp=$2 WHERE user_id=$3", lvl, nx, uid
            )
            return lvl

    # ============ МАТЕРИАЛЫ ============
    async def add_material(self, uid, mat, amount):
        col = f"mat_{mat}"
        async with self.pool.acquire() as c:
            await c.execute(
                f"UPDATE users SET {col}={col}+$1 WHERE user_id=$2", amount, uid
            )

    async def spend_material(self, uid, mat, amount):
        col = f"mat_{mat}"
        async with self.pool.acquire() as c:
            row = await c.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", uid)
            if row and row[col] >= amount:
                await c.execute(
                    f"UPDATE users SET {col}={col}-$1 WHERE user_id=$2", amount, uid
                )
                return True
        return False

    # ============ ПОДЗЕМЕЛЬЯ ============
    async def start_dungeon(self, uid, dungeon_id):
        async with self.pool.acquire() as c:
            await c.execute("""
                UPDATE users SET dungeon_id=$1, dungeon_room=1,
                dungeon_loot_gold=0, dungeon_loot_items='[]' WHERE user_id=$2
            """, dungeon_id, uid)

    async def advance_dungeon(self, uid, gold, items_json):
        async with self.pool.acquire() as c:
            await c.execute("""
                UPDATE users SET dungeon_room=dungeon_room+1,
                dungeon_loot_gold=dungeon_loot_gold+$1,
                dungeon_loot_items=$2 WHERE user_id=$3
            """, gold, items_json, uid)

    async def exit_dungeon(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("""
                UPDATE users SET dungeon_id='', dungeon_room=0,
                dungeon_loot_gold=0, dungeon_loot_items='[]' WHERE user_id=$1
            """, uid)

    # ============ ОНБОРДИНГ ============
    async def get_tutorial_step(self, uid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT step, finished FROM tutorial_progress WHERE user_id=$1", uid
            )
            if not row:
                await c.execute("INSERT INTO tutorial_progress (user_id) VALUES ($1)", uid)
                return 0, False
            return row["step"], bool(row["finished"])

    async def set_tutorial_step(self, uid, step, finished=False):
        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO tutorial_progress (user_id, step, finished)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET step=$2, finished=$3
            """, uid, step, 1 if finished else 0)

    # ============ ЕЖЕДНЕВНЫЕ КВЕСТЫ ============
    async def get_daily_quests(self, uid):
        today = str(date.today())
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT * FROM daily_quests WHERE user_id=$1 AND quest_date=$2 ORDER BY id",
                uid, today
            )
            if rows:
                return [dict(r) for r in rows]
            quest_pool = [
                ("kill_enemies", 3, 100, 50),
                ("visit_locations", 2, 80, 40),
                ("win_duels", 1, 150, 80),
                ("craft_items", 1, 120, 60),
                ("earn_gold", 200, 100, 50),
            ]
            import random as _r
            picked = _r.sample(quest_pool, 3)
            for qtype, target, rgold, rxp in picked:
                await c.execute("""
                    INSERT INTO daily_quests
                    (user_id, quest_type, target, reward_gold, reward_xp, quest_date)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, uid, qtype, target, rgold, rxp, today)
            rows = await c.fetch(
                "SELECT * FROM daily_quests WHERE user_id=$1 AND quest_date=$2 ORDER BY id",
                uid, today
            )
            return [dict(r) for r in rows]

    async def progress_quest(self, uid, quest_type, amount=1):
        today = str(date.today())
        async with self.pool.acquire() as c:
            row = await c.fetchrow("""
                SELECT id, progress, target, reward_gold, reward_xp, completed
                FROM daily_quests WHERE user_id=$1 AND quest_type=$2 AND quest_date=$3
            """, uid, quest_type, today)
            if not row or row["completed"]:
                return None
            new_progress = min(row["progress"] + amount, row["target"])
            if new_progress >= row["target"]:
                await c.execute(
                    "UPDATE daily_quests SET progress=$1, completed=1 WHERE id=$2",
                    new_progress, row["id"]
                )
                await c.execute(
                    "UPDATE users SET gold=gold+$1 WHERE user_id=$2", row["reward_gold"], uid
                )
                await self.add_xp(uid, row["reward_xp"])
                return {"completed": True, "gold": row["reward_gold"], "xp": row["reward_xp"]}
            await c.execute(
                "UPDATE daily_quests SET progress=$1 WHERE id=$2", new_progress, row["id"]
            )
            return {"completed": False}

    # ============ ЛОКАЦИИ (новая система) ============
    async def set_location_code(self, uid, code):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET location_code=$1 WHERE user_id=$2", code, uid)

    async def get_players_at_location(self, code, exclude=0):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT user_id, char_name, level, race, class, hp, max_hp, guild_id
                FROM users WHERE location_code=$1 AND char_name!='' AND user_id!=$2
                ORDER BY level DESC LIMIT 30
            """, code, exclude)
            return [dict(r) for r in rows]

    async def get_all_location_codes_visited(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT location_name FROM locations WHERE user_id=$1 ORDER BY visited_at", uid
            )
            return [r["location_name"] for r in rows]

    # ============ NPC-КВЕСТЫ ============
    async def accept_npc_quest(self, uid, quest_code):
        async with self.pool.acquire() as c:
            try:
                await c.execute(
                    "INSERT INTO npc_quest_progress (user_id, quest_code) VALUES ($1,$2)",
                    uid, quest_code
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_npc_quest(self, uid, quest_code):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT * FROM npc_quest_progress WHERE user_id=$1 AND quest_code=$2",
                uid, quest_code
            )
            return dict(row) if row else None

    async def get_user_quests(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch(
                "SELECT * FROM npc_quest_progress WHERE user_id=$1 ORDER BY accepted_at DESC", uid
            )
            return [dict(r) for r in rows]

    async def incr_npc_quest(self, uid, quest_code, amount=1):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT id, progress, completed FROM npc_quest_progress "
                "WHERE user_id=$1 AND quest_code=$2",
                uid, quest_code
            )
            if not row or row["completed"]:
                return None
            new_progress = row["progress"] + amount
            await c.execute(
                "UPDATE npc_quest_progress SET progress=$1 WHERE id=$2",
                new_progress, row["id"]
            )
            return new_progress

    async def complete_npc_quest(self, uid, quest_code):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE npc_quest_progress SET completed=1 WHERE user_id=$1 AND quest_code=$2",
                uid, quest_code
            )

    # ============ ГИЛЬДИИ ============
    async def create_guild(self, name, tag, leader_id):
        async with self.pool.acquire() as c:
            try:
                row = await c.fetchrow("""
                    INSERT INTO guilds (name, tag, leader_id) VALUES ($1,$2,$3) RETURNING id
                """, name, tag, leader_id)
                gid = row["id"]
                await c.execute("""
                    INSERT INTO guild_members (user_id, guild_id, rank)
                    VALUES ($1,$2,'leader')
                    ON CONFLICT (user_id) DO UPDATE SET guild_id=$2, rank='leader'
                """, leader_id, gid)
                await c.execute("UPDATE users SET guild_id=$1 WHERE user_id=$2", gid, leader_id)
                return gid
            except asyncpg.UniqueViolationError:
                return None

    async def get_guild(self, gid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM guilds WHERE id=$1", gid)
            return dict(row) if row else None

    async def get_user_guild(self, uid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("""
                SELECT g.* FROM guilds g
                JOIN guild_members gm ON g.id = gm.guild_id
                WHERE gm.user_id=$1
            """, uid)
            return dict(row) if row else None

    async def get_guild_members(self, gid):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT gm.user_id, gm.rank, u.char_name, u.level, u.race, u.class
                FROM guild_members gm
                JOIN users u ON u.user_id = gm.user_id
                WHERE gm.guild_id=$1
                ORDER BY gm.rank DESC, u.level DESC
            """, gid)
            return [dict(r) for r in rows]

    async def add_guild_member(self, uid, gid):
        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO guild_members (user_id, guild_id, rank)
                VALUES ($1,$2,'member')
                ON CONFLICT (user_id) DO UPDATE SET guild_id=$2, rank='member'
            """, uid, gid)
            await c.execute("UPDATE users SET guild_id=$1 WHERE user_id=$2", gid, uid)

    async def remove_guild_member(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM guild_members WHERE user_id=$1", uid)
            await c.execute("UPDATE users SET guild_id=0 WHERE user_id=$1", uid)

    async def get_guilds_top(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT g.id, g.name, g.tag, g.level, g.treasury,
                       (SELECT COUNT(*) FROM guild_members WHERE guild_id=g.id) as members
                FROM guilds g ORDER BY g.level DESC, members DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    # ============ ЗАХВАТ ЛОКАЦИЙ ============
    async def get_location_owner(self, location_code):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("""
                SELECT lo.*, g.name as guild_name, g.tag as guild_tag
                FROM location_owners lo
                LEFT JOIN guilds g ON g.id = lo.guild_id
                WHERE lo.location_code=$1
            """, location_code)
            return dict(row) if row else None

    async def capture_location(self, location_code, gid):
        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO location_owners (location_code, guild_id, captured_at, defense_points)
                VALUES ($1, $2, NOW(), 100)
                ON CONFLICT (location_code) DO UPDATE
                SET guild_id=$2, captured_at=NOW(), defense_points=100
            """, location_code, gid)

    async def get_all_captured_locations(self):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT lo.location_code, lo.guild_id, lo.captured_at,
                       g.name, g.tag
                FROM location_owners lo
                JOIN guilds g ON g.id = lo.guild_id
            """)
            return [dict(r) for r in rows]

    # ============ БОССЫ ЛОКАЦИЙ ============
    async def get_location_boss_state(self, location_code):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT * FROM location_bosses WHERE location_code=$1", location_code
            )
            return dict(row) if row else None

    async def kill_location_boss(self, location_code, boss_name, killer_id):
        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO location_bosses (location_code, boss_name, killed_at, killed_by)
                VALUES ($1, $2, NOW(), $3)
                ON CONFLICT (location_code) DO UPDATE
                SET boss_name=$2, killed_at=NOW(), killed_by=$3
            """, location_code, boss_name, killer_id)

    # ============ ДИНАМИЧЕСКИЕ СОБЫТИЯ ============
    async def get_active_event(self, location_code):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("""
                SELECT * FROM world_events_dyn
                WHERE location_code=$1 AND expires_at > NOW()
                ORDER BY started_at DESC LIMIT 1
            """, location_code)
            return dict(row) if row else None

    async def get_all_active_events(self):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
                SELECT * FROM world_events_dyn WHERE expires_at > NOW()
                ORDER BY started_at DESC
            """)
            return [dict(r) for r in rows]

    async def create_world_event(self, location_code, event_code, event_name, event_desc,
                                  duration_min, xp_mult, gold_mult, spawn_mult,
                                  enemy_dmg_mult=1.0):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM world_events_dyn WHERE location_code=$1", location_code)
            await c.execute("""
                INSERT INTO world_events_dyn
                (location_code, event_code, event_name, event_desc,
                 xp_mult, gold_mult, spawn_mult, enemy_dmg_mult, expires_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8, NOW() + ($9 || ' minutes')::INTERVAL)
            """, location_code, event_code, event_name, event_desc,
                xp_mult, gold_mult, spawn_mult, enemy_dmg_mult, str(duration_min))
                # ============ СКИЛЫ ============
    async def set_active_skills(self, uid, json_str):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET active_skills=$1 WHERE user_id=$2", json_str, uid
            )

    async def set_learned_skills(self, uid, json_str):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET learned_skills=$1 WHERE user_id=$2", json_str, uid
            )

    async def spend_skill_point(self, uid, amount=1):
        async with self.pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT skill_points FROM users WHERE user_id=$1", uid
            )
            if row and row["skill_points"] >= amount:
                await c.execute(
                    "UPDATE users SET skill_points=skill_points-$1 WHERE user_id=$2",
                    amount, uid
                )
                return True
        return False

    async def clean_expired_events(self):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM world_events_dyn WHERE expires_at < NOW()")
