from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.filters.role import RoleFilter
from bot.services import supabase_db as db

router = Router()


@router.message(Command("invite_id"), RoleFilter("owner"))
async def invite_by_id(message: Message):
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


@router.message(Command("invite"), RoleFilter("owner"))
async def invite_by_username(message: Message):
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


@router.message(Command("ban"), RoleFilter("owner"))
async def ban_user_cmd(message: Message):
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


@router.message(Command("genlink"), RoleFilter("owner"))
async def generate_invite_link(message: Message):
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
        await message.answer(f"❌ Ошибка при создании ссылки:\n<code>{e}</code>", parse_mode="HTML")


@router.message(Command("users"), RoleFilter("owner"))
async def list_users(message: Message):
    users = await db.get_all_beta_users()
    if not users:
        await message.answer("Бета-тестеров пока нет")
        return

    text = "👥 *Бета-тестеры:*\n\n"
    for u in users:
        uname = f"@{u['username']}" if u.get("username") else "—"
        text += f"• {u['user_id']} — {uname} ({u['role']})\n"

    await message.answer(text, parse_mode="Markdown")
