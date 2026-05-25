from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🎯 Цели")],
            [KeyboardButton(text="📋 История"), KeyboardButton(text="📱 Подписки")],
            [KeyboardButton(text="💱 Курсы"), KeyboardButton(text="📅 Неделя")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
