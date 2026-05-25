from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.services.currency import get_rates_text
from bot.keyboards.inline import back_to_menu_btn

router = Router()


@router.message(Command("rates"))
async def cmd_rates(message: Message):
    text = await get_rates_text()
    await message.answer(text, parse_mode="Markdown", reply_markup=back_to_menu_btn())
