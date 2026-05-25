import os
from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.services import supabase_db as db


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user_id = event.from_user.id
        role = await db.get_user_role(user_id)

        if role == "banned":
            await event.answer("🚫 Доступ закрыт.")
            return

        if role is None:
            owner_username = os.environ.get("OWNER_USERNAME", "owner")
            await event.answer(
                "🔒 Бот пока в закрытом бета-тесте.\n"
                f"Напиши @{owner_username} чтобы получить доступ."
            )
            return

        await db.ensure_user(user_id, event.from_user.username)
        data["user_role"] = role
        return await handler(event, data)
