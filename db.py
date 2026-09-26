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
            await conn.execute("CREATE TABLE IF NOT EXISTS locations (id SERIAL PRIMARY KEY, user_id BIGINT, location_name TEXT, visited_at TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, location_name))")
            await conn.execute("CREATE TABLE IF NOT EXISTS user_achievements (id SERIAL PRIMARY KEY, user_id BIGINT, code TEXT, earned_at TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, code))")
            await conn.execute("CREATE TABLE IF NOT EXISTS world_events (id SERIAL PRIMARY KEY, user_id BIGINT, username TEXT, event_text TEXT, created_at TIMESTAMP DEFAULT NOW())")
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
            await conn.execute("CREATE TABLE IF NOT EXISTS graffiti (id SERIAL PRIMARY KEY, user_id BIGINT, username TEXT, location TEXT, text TEXT, created_at TIMESTAMP DEFAULT NOW())")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS duel_offers (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT, challenger_name TEXT,
                    opponent_id BIGINT, opponent_name TEXT,
                    stake INTEGER, status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # === НОВЫЕ ТАБЛИЦЫ ===
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
            # === МИГРАЦИИ ===
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
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS is_pvp INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS opponent_id BIGINT DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS stake INTEGER DEFAULT 0",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS my_turn INTEGER DEFAULT 1",
                "ALTER TABLE active_combat ADD COLUMN IF NOT EXISTS is_dungeon INTEGER DEFAULT 0",
            ]
            for sql in migrations:
                try:
                    await conn.execute(sql)
                except Exception as e:
                    logging.warning(f"Migration skipped: {e}")

    # ============ БАЗОВЫЕ ============
    async def get_user(self, user_id, username=""):
        today = str(date.today())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
            if not row:
                await conn.execute("INSERT INTO users (user_id, username, last_reset) VALUES ($1,$2,$3)",
                                   user_id, username, today)
                return self._empty_user(user_id)
            if row["last_reset"] != today:
                await conn.execute("UPDATE users SET requests_today=0, last_reset=$1 WHERE user_id=$2",
                                   today, user_id)
                d = dict(row); d["requests_today"] = 0
                return d
            return dict(row)

    def _empty_user(self, uid):
        return {"user_id": uid, "is_premium": 0, "requests_today": 0, "story": "",
                "consent_given": 0, "referred_by": 0, "referral_count": 0, "xp": 0,
                "level": 1, "last_daily": None, "daily_streak": 0, "arc": 1,
                "action_count": 0, "location": "Начальная деревня", "race": "", "class": "",
                "char_name": "", "stat_str": 5, "stat_dex": 5, "stat_con": 5,
                "stat_int": 5, "stat_wit": 5, "stat_men": 5, "hp": 100, "max_hp": 100,
                "bosses_defeated": 0, "gold": 0, "equipped_weapon": "", "equipped_armor": "",
                "equipped_accessory": "", "deaths": 0, "reputation": 0, "pvp_wins": 0,
                "pvp_losses": 0, "faction": "", "mat_iron": 0, "mat_leather": 0,
                "mat_dust": 0, "mat_crystal": 0, "dungeon_id": "", "dungeon_room": 0,
                "dungeon_loot_gold": 0, "dungeon_loot_items": "[]"}

    async def give_consent(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET consent_given=1, consent_date=$1 WHERE user_id=$2", str(date.today()), uid)

    async def revoke_consent(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET consent_given=0, story='' WHERE user_id=$1", uid)

    async def set_referrer(self, uid, ref):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT referred_by FROM users WHERE user_id=$1", uid)
            if row and row["referred_by"] == 0 and ref != uid:
                await c.execute("UPDATE users SET referred_by=$1 WHERE user_id=$2", ref, uid)
                await c.execute("UPDATE users SET referral_count=referral_count+1, requests_today=GREATEST(0, requests_today-10) WHERE user_id=$1", ref)
                return True
        return False

    async def increment(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET requests_today=requests_today+1 WHERE user_id=$1", uid)

    async def update_story(self, uid, s):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET story=$1 WHERE user_id=$2", s, uid)

    async def set_premium(self, uid, v=1):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET is_premium=$1 WHERE user_id=$2", v, uid)

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
            return (lvl, nx, up)

    async def incr_action_count(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET action_count=action_count+1, arc=arc+1 WHERE user_id=$1", uid)
            row = await c.fetchrow("SELECT action_count, arc FROM users WHERE user_id=$1", uid)
            return row["action_count"], row["arc"]

    # ============ ИНВЕНТАРЬ ============
    async def add_item(self, uid, item, lvl=0):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO inventory (user_id, item_name, item_level) VALUES ($1,$2,$3)", uid, item, lvl)

    async def get_inventory(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT item_name, item_level FROM inventory WHERE user_id=$1 ORDER BY created_at", uid)
            return [dict(r) for r in rows]

    async def remove_item(self, uid, item, lvl=0):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT id FROM inventory WHERE user_id=$1 AND item_name=$2 AND item_level=$3 LIMIT 1", uid, item, lvl)
            if row:
                await c.execute("DELETE FROM inventory WHERE id=$1", row["id"])
                return True
        return False

    # ============ ЛОКАЦИИ / ГРАФФИТИ ============
    async def add_location(self, uid, loc):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO locations (user_id, location_name) VALUES ($1,$2) ON CONFLICT DO NOTHING", uid, loc)
            await c.execute("UPDATE users SET location=$1 WHERE user_id=$2", loc, uid)

    async def get_locations(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT location_name FROM locations WHERE user_id=$1 ORDER BY visited_at", uid)
            return [r["location_name"] for r in rows]

    async def get_players_in_location(self, loc, ex):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT user_id, char_name, level, race, class, hp FROM users WHERE location=$1 AND char_name!='' AND user_id!=$2 LIMIT 30", loc, ex)
            return [dict(r) for r in rows]

    async def get_user_by_char_name(self, name):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM users WHERE LOWER(char_name)=LOWER($1) LIMIT 1", name)
            return dict(row) if row else None

    async def add_graffiti(self, uid, uname, loc, text):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO graffiti (user_id, username, location, text) VALUES ($1,$2,$3,$4)", uid, uname, loc, text)

    async def get_graffiti(self, loc, limit=15):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT username, text FROM graffiti WHERE location=$1 ORDER BY created_at DESC LIMIT $2", loc, limit)
            return [dict(r) for r in rows]

    # ============ ЕЖЕДНЕВНАЯ ============
    async def claim_daily(self, uid):
        today = str(date.today())
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT last_daily, daily_streak FROM users WHERE user_id=$1", uid)
            if row["last_daily"] == today:
                return None
            y = str(date.fromordinal(date.today().toordinal() - 1))
            streak = row["daily_streak"] + 1 if row["last_daily"] == y else 1
            if streak > 7:
                streak = 1
            await c.execute("UPDATE users SET last_daily=$1, daily_streak=$2, requests_today=GREATEST(0, requests_today-$3) WHERE user_id=$4",
                            today, streak, 5, uid)
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
            rows = await c.fetch("""SELECT char_name, username, level, xp, bosses_defeated, race, class, faction
                FROM users WHERE race!='' AND char_name!='' ORDER BY level DESC, xp DESC LIMIT $1""", limit)
            return [dict(r) for r in rows]

    async def get_pvp_top(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""SELECT char_name, pvp_wins, pvp_losses, reputation
                FROM users WHERE race!='' AND pvp_wins>0 ORDER BY pvp_wins DESC LIMIT $1""", limit)
            return [dict(r) for r in rows]

    # ============ ДОСТИЖЕНИЯ ============
    async def add_achievement(self, uid, code):
        async with self.pool.acquire() as c:
            try:
                await c.execute("INSERT INTO user_achievements (user_id, code) VALUES ($1,$2)", uid, code)
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_achievements(self, uid):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT code FROM user_achievements WHERE user_id=$1", uid)
            return [dict(r) for r in rows]

    # ============ МИР ============
    async def add_world_event(self, uid, uname, text):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO world_events (user_id, username, event_text) VALUES ($1,$2,$3)", uid, uname, text)

    async def get_world_events(self, limit=10):
        async with self.pool.acquire() as c:
            rows = await c.fetch("SELECT username, event_text FROM world_events ORDER BY created_at DESC LIMIT $1", limit)
            return [dict(r) for r in rows]

    # ============ БОЙ ============
    async def get_combat(self, uid):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", uid)
            return dict(row) if row else None

    async def start_combat(self, uid, name, lvl, hp, boss=0, dungeon=0):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM active_combat WHERE user_id=$1", uid)
            await c.execute("""INSERT INTO active_combat (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_boss, is_dungeon)
                VALUES ($1,$2,$3,$4,$4,$5,$6)""", uid, name, lvl, hp, boss, dungeon)

    async def update_combat_enemy_hp(self, uid, hp):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2", max(0, hp), uid)

    async def set_combat_defending(self, uid, d):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE active_combat SET defending=$1 WHERE user_id=$2", d, uid)

    async def incr_combat_round(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE active_combat SET round_num=round_num+1 WHERE user_id=$1", uid)

    async def end_combat(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM active_combat WHERE user_id=$1", uid)

    # ============ PVP ============
    async def start_pvp_combat(self, a, b, stake):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM active_combat WHERE user_id IN ($1,$2)", a["user_id"], b["user_id"])
            await c.execute("""INSERT INTO active_combat (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,1)""",
                            a["user_id"], b["char_name"], b["level"], b["hp"], b["user_id"], stake)
            await c.execute("""INSERT INTO active_combat (user_id, enemy_name, enemy_level, enemy_hp, enemy_max_hp, is_pvp, opponent_id, stake, my_turn)
                VALUES ($1,$2,$3,$4,$4,1,$5,$6,0)""",
                            b["user_id"], a["char_name"], a["level"], a["hp"], a["user_id"], stake)

    async def pvp_damage(self, aid, dmg):
        async with self.pool.acquire() as c:
            ac = await c.fetchrow("SELECT * FROM active_combat WHERE user_id=$1", aid)
            if not ac or not ac["is_pvp"]:
                return None
            opp_id = ac["opponent_id"]
            opp = await c.fetchrow("SELECT hp FROM users WHERE user_id=$1", opp_id)
            nhp = max(0, opp["hp"] - dmg)
            await c.execute("UPDATE users SET hp=$1 WHERE user_id=$2", nhp, opp_id)
            await c.execute("UPDATE active_combat SET enemy_hp=$1 WHERE user_id=$2", nhp, aid)
            return nhp, opp_id

    async def pvp_switch_turn(self, uid):
        async with self.pool.acquire() as c:
            ac = await c.fetchrow("SELECT opponent_id FROM active_combat WHERE user_id=$1", uid)
            if not ac:
                return
            opp = ac["opponent_id"]
            await c.execute("UPDATE active_combat SET my_turn=0 WHERE user_id=$1", uid)
            await c.execute("UPDATE active_combat SET my_turn=1, round_num=round_num+1 WHERE user_id=$1", opp)

    # ============ ДУЭЛИ ============
    async def create_duel_offer(self, cid, cname, oid, oname, stake):
        async with self.pool.acquire() as c:
            await c.execute("DELETE FROM duel_offers WHERE status='pending' AND ((challenger_id=$1 AND opponent_id=$2) OR (challenger_id=$2 AND opponent_id=$1))", cid, oid)
            row = await c.fetchrow("""INSERT INTO duel_offers (challenger_id, challenger_name, opponent_id, opponent_name, stake)
                VALUES ($1,$2,$3,$4,$5) RETURNING id""", cid, cname, oid, oname, stake)
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
            await c.execute("INSERT INTO pets (user_id, pet_type, name) VALUES ($1,$2,$3)", uid, ptype, name)

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
            await c.execute("UPDATE pets SET level=$1, xp=$2 WHERE user_id=$3", lvl, nx, uid)
            return lvl

    # ============ МАТЕРИАЛЫ ============
    async def add_material(self, uid, mat, amount):
        col = f"mat_{mat}"
        async with self.pool.acquire() as c:
            await c.execute(f"UPDATE users SET {col}={col}+$1 WHERE user_id=$2", amount, uid)

    async def spend_material(self, uid, mat, amount):
        col = f"mat_{mat}"
        async with self.pool.acquire() as c:
            row = await c.fetchrow(f"SELECT {col} FROM users WHERE user_id=$1", uid)
            if row and row[col] >= amount:
                await c.execute(f"UPDATE users SET {col}={col}-$1 WHERE user_id=$2", amount, uid)
                return True
        return False

    # ============ ПОДЗЕМЕЛЬЯ ============
    async def start_dungeon(self, uid, dungeon_id):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET dungeon_id=$1, dungeon_room=1, dungeon_loot_gold=0, dungeon_loot_items='[]' WHERE user_id=$2",
                            dungeon_id, uid)

    async def advance_dungeon(self, uid, gold, items_json):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET dungeon_room=dungeon_room+1, dungeon_loot_gold=dungeon_loot_gold+$1, dungeon_loot_items=$2 WHERE user_id=$3",
                            gold, items_json, uid)

    async def exit_dungeon(self, uid):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET dungeon_id='', dungeon_room=0, dungeon_loot_gold=0, dungeon_loot_items='[]' WHERE user_id=$1", uid)
