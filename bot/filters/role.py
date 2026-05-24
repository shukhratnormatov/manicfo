from aiogram.filters import BaseFilter
from aiogram.types import Message


class RoleFilter(BaseFilter):
    def __init__(self, role: str):
        self.role = role

    async def __call__(self, message: Message, user_role: str = "") -> bool:
        return user_role == self.role
