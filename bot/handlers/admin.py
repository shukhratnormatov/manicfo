import logging
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services import supabase_db as db

router = Router()
logger = logging.getLogger(__name__)

OWNER_TG_ID = int(os.environ.get("OWNER_TG_ID", "0"))


def _is_owner(message: Message) -> bool:
    """Проверяет: либо user_id совпадает с OWNER_TG_ID из env, либо ждёт роль в data."""
    return OWNER_TG_ID and message.from_user.id == OWNER_TG_ID


@router.message(Command("invite_id"))
async def invite_by_id(message: Message, user_role: str = ""):
    if user_role != "owner" and not _is_owner(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /invite_id 123456789")
        return

    try:
        new_user_id = int(parts[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    await db.add_beta_user(new_user_id, invited_by=message.from_user.id)
    await message.answer(f"✅ Пользователь {new_user_id} добавлен в бету")


@router.message(Command("invite"))
async def invite_by_username(message: Message, user_role: str = ""):
    if user_role != "owner" and not _is_owner(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /invite @username")
        return

    username = parts[1].lstrip("@")
    user = await db.get_user_by_username(username)
    if not user:
        await message.answer(
            f"Пользователь @{username} ещё не писал боту.\n"
            f"Попроси его написать /start, потом используй /invite_id с его ID."
        )
        return

    await db.add_beta_user(user["id"], invited_by=message.from_user.id)
    await message.answer(f"✅ @{username} добавлен в бету")


@router.message(Command("ban"))
async def ban_user_cmd(message: Message, user_role: str = ""):
    if user_role != "owner" and not _is_owner(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /ban @username или /ban 123456789")
        return

    target = parts[1].lstrip("@")
    try:
        user_id = int(target)
    except ValueError:
        user = await db.get_user_by_username(target)
        if not user:
            await message.answer(f"Пользователь @{target} не найден")
            return
        user_id = user["id"]

    await db.ban_user(user_id)
    await message.answer(f"🚫 Пользователь {user_id} заблокирован")


@router.message(Command("genlink"))
async def generate_invite_link(message: Message, user_role: str = ""):
    logger.info(
        "[genlink] called: user_id=%s, user_role=%r, is_owner=%s",
        message.from_user.id, user_role, _is_owner(message),
    )
    if user_role != "owner" and not _is_owner(message):
        logger.warning("[genlink] rejected for user_id=%s", message.from_user.id)
        return

    try:
        token = await db.create_invite_token(message.from_user.id)
        bot_username = (await message.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={token}"
        await message.answer(
            "🔗 Invite-ссылка готова:\n\n"
            f"`{link}`\n\n"
            "⏱ Действует 48 часов\n"
            "🔂 Одноразовая",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("[genlink] error: %s", e, exc_info=True)
        await message.answer(f"❌ Ошибка при создании ссылки:\n<code>{e}</code>", parse_mode="HTML")


@router.message(Command("users"))
async def list_users(message: Message, user_role: str = ""):
    if user_role != "owner" and not _is_owner(message):
        return
    users = await db.get_all_beta_users()
    if not users:
        await message.answer("Бета-тестеров пока нет")
        return

    text = "👥 *Бета-тестеры:*\n\n"
    for u in users:
        uname = f"@{u['username']}" if u.get("username") else "—"
        text += f"• {u['user_id']} — {uname} ({u['role']})\n"

    await message.answer(text, parse_mode="Markdown")
