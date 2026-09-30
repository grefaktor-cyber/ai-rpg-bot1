"""Мелкие команды: /help, /revoke, /reset."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

from core import globals as g
from core.keyboards import main_kb
from core.texts import HELP_TEXT

router = Router()


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP_TEXT, reply_markup=main_kb(), parse_mode=ParseMode.HTML)


@router.message(Command("revoke"))
async def revoke(m: Message):
    await g.db.revoke_consent(m.from_user.id)
    await m.answer("🗑 Согласие отозвано.")


@router.message(Command("reset"))
async def reset(m: Message):
    await g.db.update_story(m.from_user.id, "")
    await m.answer("🔄 История сброшена.")
