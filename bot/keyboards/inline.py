from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def onboarding_goals_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔨 Ремонт", callback_data="goal_preset:Ремонт"),
            InlineKeyboardButton(text="✈️ Поездка", callback_data="goal_preset:Поездка"),
        ],
        [
            InlineKeyboardButton(text="🏠 Ипотека", callback_data="goal_preset:Ипотека"),
            InlineKeyboardButton(text="➕ Своя цель", callback_data="goal_preset:custom"),
        ],
    ])


def goals_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить цель", callback_data="goal_add"),
            InlineKeyboardButton(text="💳 Пополнить", callback_data="goal_save"),
        ],
    ])


def subs_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="sub_add"),
        ],
    ])


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=callback_data)],
    ])
