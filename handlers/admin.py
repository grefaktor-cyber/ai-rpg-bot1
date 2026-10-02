

# ================= УРОВЕНЬ 1 =================
@router.message(Command("admin_resetlevel"))
async def admin_resetlevel(m: Message):
    """Сбросить уровень до 1 и обнулить очки умений."""
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return
    uid = m.from_user.id
    async with g.db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET level=1, xp=0, skill_points=0 WHERE user_id=$1",
            uid
        )
    u = await g.db.get_user(uid)
    nm = calc_max_hp(u)
    nmp = calc_max_mp(u)
    await g.db.update_hp_max(uid, nm, nm)
    await g.db.update_mp(uid, nmp)
    await m.answer(
        f"🛠 <b>Уровень сброшен: 1</b>\n"
        f"HP: {nm}/{nm} · MP: {nmp}/{nmp}\n"
        f"🎯 Очки умений: 0",
        parse_mode=ParseMode.HTML)


# ================= СПАВН БОССА (ТЕСТ) =================
@router.message(Command("admin_spawn_boss"))
async def admin_spawn_boss(m: Message):
    """Форс-спавн обычного босса."""
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return

    parts = m.text.split()
    boss_code = parts[1] if len(parts) > 1 else None
    location_code = parts[2] if len(parts) > 2 else None

    try:
        from services.world_boss_service import force_spawn_boss
    except ImportError:
        await m.answer("⚠️ В services/world_boss_service.py нет force_spawn_boss.")
        return

    result = await force_spawn_boss(boss_code, location_code, notify=False)

    if "error" in result:
        err_text = f"❌ {result['error']}\n\n"
        if "available" in result:
            err_text += "<b>Доступные коды:</b>\n"
            for code in result["available"]:
                err_text += f"• <code>{code}</code>\n"
        await m.answer(err_text, parse_mode=ParseMode.HTML)
        return

    await m.answer(
        f"🛠 <b>Босс заспавнен!</b>\n\n"
        f"🐉 <b>{result['boss_name']}</b> (ур. {result['boss_level']})\n"
        f"❤️ HP: <b>{result['hp']}</b>\n"
        f"⚔️ Урон: ~{result['attack_dmg']} ({result['dmg_type']})\n"
        f"📍 Локация: <b>{result['location_name']}</b>\n"
        f"   код: <code>{result['location_code']}</code>\n\n"
        f"<b>Что дальше:</b>\n"
        f"1. <code>/admin_teleport {result['location_code']}</code>\n"
        f"2. В боте напиши <code>/boss</code>\n"
        f"3. Жми «⚔️ Атаковать»",
        parse_mode=ParseMode.HTML)


@router.message(Command("admin_spawn_raid"))
async def admin_spawn_raid(m: Message):
    """Форс-спавн РЕЙД-босса (требует 2-3 игрока)."""
    if not _is_admin(m.from_user.id):
        await m.answer("❌"); return

    parts = m.text.split()
    boss_code = parts[1] if len(parts) > 1 else None
    location_code = parts[2] if len(parts) > 2 else None

    try:
        from services.world_boss_service import force_spawn_boss, RAID_BOSSES
    except ImportError:
        await m.answer("⚠️ В services/world_boss_service.py нет RAID_BOSSES.")
        return

    if boss_code is None:
        import random as _r
        boss_code = _r.choice(list(RAID_BOSSES.keys()))

    if boss_code not in RAID_BOSSES:
        avail = ", ".join(f"<code>{c}</code>" for c in RAID_BOSSES)
        await m.answer(
            f"❌ Рейд-босс «{boss_code}» не найден.\n\n"
            f"<b>Доступные:</b> {avail}",
            parse_mode=ParseMode.HTML)
        return

    result = await force_spawn_boss(boss_code, location_code, notify=True)

    if "error" in result:
        err_text = f"❌ {result['error']}\n\n"
        if "available" in result:
            err_text += "<b>Доступные коды:</b>\n"
            for code in result["available"]:
                err_text += f"• <code>{code}</code>\n"
        await m.answer(err_text, parse_mode=ParseMode.HTML)
        return

    await m.answer(
        f"🛠 <b>⚔️ РЕЙД-БОСС заспавнен!</b>\n\n"
        f"👹 <b>{result['boss_name']}</b> (ур. {result['boss_level']})\n"
        f"❤️ HP: <b>{result['hp']}</b>\n"
        f"⚔️ Урон: ~{result['attack_dmg']} ({result['dmg_type']})\n"
        f"👥 Требуется: <b>{result['min_players']}+ игрока</b>\n"
        f"📍 Локация: <b>{result['location_name']}</b>\n"
        f"   код: <code>{result['location_code']}</code>\n\n"
        f"<i>Все игроки получили уведомление.</i>\n\n"
        f"<b>Что дальше:</b>\n"
        f"1. <code>/admin_teleport {result['location_code']}</code>\n"
        f"2. Позови друга с собой\n"
        f"3. В боте напиши <code>/boss</code>\n"
        f"4. Жми «⚔️ Атаковать»",
        parse_mode=ParseMode.HTML)
