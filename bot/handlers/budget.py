from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import budget_empty_kb, budget_set_kb
from bot.keyboards.reply import MENU_BUTTONS
from bot.services import supabase_db as db
from bot.utils.formatters import format_sum, progress_bar, format_percent

router = Router()

MONTH_NAMES = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


class BudgetStates(StatesGroup):
    waiting_amount = State()


@router.message(Command("budget"))
async def cmd_budget(message: Message, state: FSMContext):
    await state.clear()
    today = date.today()
    budget = await db.get_monthly_budget(message.from_user.id)
    total_spent = await db.get_total_expenses(message.from_user.id, today.year, today.month)
    month_name = MONTH_NAMES[today.month]

    if budget is None:
        await message.answer(
            f"💰 *Бюджет на {month_name}*\n\n"
            f"Бюджет не установлен.\n"
            f"Уже потрачено: *{format_sum(total_spent)} сум*",
            parse_mode="Markdown",
            reply_markup=budget_empty_kb(),
        )
        return

    remaining = budget - total_spent
    bar = progress_bar(total_spent, budget)
    pct = format_percent(total_spent, budget)

    text = (
        f"💰 *Бюджет на {month_name}*\n\n"
        f"Бюджет: {format_sum(budget)} сум\n"
        f"Потрачено: *{format_sum(total_spent)} сум* ({pct})\n"
        f"{bar}\n"
    )
    if remaining > 0:
        text += f"✅ Остаток: *{format_sum(remaining)} сум*"
    else:
        text += f"⚠️ Превышен на *{format_sum(-remaining)} сум*"

    await message.answer(text, parse_mode="Markdown", reply_markup=budget_set_kb())


@router.callback_query(F.data == "budget:set")
async def budget_set_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введи сумму месячного бюджета (в сумах):\n"
        "Например: 3 млн или 3000000"
    )
    await state.set_state(BudgetStates.waiting_amount)


@router.message(BudgetStates.waiting_amount, ~F.text.in_(MENU_BUTTONS))
async def budget_amount_input(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "")
    try:
        if "млн" in text:
            amount = float(text.replace("млн", "")) * 1_000_000
        elif "к" in text:
            amount = float(text.replace("к", "")) * 1_000
        else:
            amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Не понял сумму, попробуй: 3 млн или 3000000")
        return

    await db.set_monthly_budget(message.from_user.id, amount)
    await state.clear()

    await message.answer(
        f"✅ Бюджет на этот месяц установлен: *{format_sum(amount)} сум*\n\n"
        f"Смотри статус: /budget",
        parse_mode="Markdown",
    )
