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


def back_to_menu_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])


def history_item_kb(tx_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit:tx:{tx_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:tx:{tx_id}"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])


def goals_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Пополнить", callback_data="goal_save"),
            InlineKeyboardButton(text="➕ Добавить", callback_data="goal_add"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])


def subs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="sub_add")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])


def cancel_tx_kb(tx_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отменить", callback_data=f"cancel_tx:{tx_id}")],
    ])


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=callback_data)],
    ])


def sub_item_kb(sub_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit:sub:{sub_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:sub:{sub_id}"),
        ],
    ])


def goal_item_kb(goal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit:goal:{goal_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:goal:{goal_id}"),
        ],
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="goal_save")],
    ])


def budget_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Установить бюджет", callback_data="budget:set")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])


def budget_set_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data="budget:set"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data="budget:delete"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])
