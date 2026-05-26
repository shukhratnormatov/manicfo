from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Набор текстов кнопок главного меню — используется для исключения их
# из FSM-хендлеров, чтобы пользователь мог выйти из любого состояния.
MENU_BUTTONS = frozenset([
    "📊 Статистика",
    "🎯 Цели",
    "📋 История",
    "📱 Подписки",
    "💱 Курсы",
    "📅 Неделя",
    "💰 Бюджет",
])


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🎯 Цели")],
            [KeyboardButton(text="📋 История"), KeyboardButton(text="📱 Подписки")],
            [KeyboardButton(text="💱 Курсы"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="💰 Бюджет")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
