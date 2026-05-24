from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import goals_actions_kb, skip_kb
from bot.services import supabase_db as db, analytics
from bot.utils.formatters import format_sum, progress_bar, format_percent

router = Router()


class AddGoalStates(StatesGroup):
    waiting_name = State()
    waiting_amount = State()
    waiting_deadline = State()


class SaveGoalStates(StatesGroup):
    waiting_goal_choice = State()
    waiting_amount = State()


@router.message(Command("goals"))
async def cmd_goals(message: Message):
    goals = await db.get_goals(message.from_user.id)
    if not goals:
        await message.answer(
            "У тебя пока нет целей накопления.\n"
            "Добавь первую командой /add_goal"
        )
        return

    monthly_avg = await db.get_monthly_income_avg(message.from_user.id, 3)
    monthly_rate = monthly_avg * 0.15

    text = "🎯 *Твои цели накопления*\n\n"
    for i, goal in enumerate(goals, 1):
        saved = float(goal["saved_amount"] or 0)
        target = float(goal["target_amount"])
        bar = progress_bar(saved, target)
        pct = format_percent(saved, target)

        text += f"*{i}. {goal['name']}*\n"
        text += f"{format_sum(saved)} / {format_sum(target)} сум\n"
        text += f"{bar} {pct}\n"
        if goal.get("deadline"):
            text += f"📅 Дедлайн: {goal['deadline']}\n"
        if monthly_rate > 0:
            from bot.services.analytics import calc_months_to_goal
            from bot.utils.formatters import months_to_human
            months = calc_months_to_goal(target, saved, monthly_rate)
            if months == 0:
                text += "✅ Цель достигнута!\n"
            elif months:
                text += f"При +{format_sum(monthly_rate)}/мес → {months_to_human(months)}\n"
        text += "\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=goals_actions_kb())


@router.message(Command("add_goal"))
@router.callback_query(F.data == "goal_add")
async def cmd_add_goal(event, state: FSMContext):
    msg = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer("Как назовём цель? Например: «Ремонт», «Машина», «Отпуск»")
    await state.set_state(AddGoalStates.waiting_name)


@router.message(AddGoalStates.waiting_name)
async def add_goal_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        f"Сколько нужно накопить на «{message.text.strip()}»? (в сумах)\n"
        "Пример: 8000000 или 8 млн"
    )
    await state.set_state(AddGoalStates.waiting_amount)


@router.message(AddGoalStates.waiting_amount)
async def add_goal_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "")
    try:
        if "млн" in text:
            amount = float(text.replace("млн", "")) * 1_000_000
        elif "к" in text:
            amount = float(text.replace("к", "")) * 1_000
        else:
            amount = float(text)
    except ValueError:
        await message.answer("Не понял сумму, попробуй: 8000000")
        return

    await state.update_data(amount=amount)
    await message.answer(
        "К какой дате? Формат: 01.12.2025\nИли пропусти:",
        reply_markup=skip_kb("skip_goal_deadline"),
    )
    await state.set_state(AddGoalStates.waiting_deadline)


@router.callback_query(F.data == "skip_goal_deadline", AddGoalStates.waiting_deadline)
async def skip_goal_deadline(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _finish_add_goal(callback.message, state, None)


@router.message(AddGoalStates.waiting_deadline)
async def add_goal_deadline(message: Message, state: FSMContext):
    deadline = None
    try:
        from datetime import datetime
        deadline = datetime.strptime(message.text.strip(), "%d.%m.%Y").date().isoformat()
    except ValueError:
        pass
    await _finish_add_goal(message, state, deadline)


async def _finish_add_goal(message: Message, state: FSMContext, deadline):
    data = await state.get_data()
    goals = await db.get_goals(message.chat.id)
    priority = len(goals) + 1
    await db.add_goal(
        user_id=message.chat.id,
        name=data["name"],
        target_amount=data["amount"],
        deadline=deadline,
        priority=priority,
    )
    await state.clear()
    await message.answer(
        f"✅ Цель «{data['name']}» добавлена!\n"
        f"Нужно накопить: {format_sum(data['amount'])} сум\n\n"
        "Смотри все цели: /goals"
    )


@router.message(Command("save"))
@router.callback_query(F.data == "goal_save")
async def cmd_save(event, state: FSMContext):
    msg = event if isinstance(event, Message) else event.message
    user_id = msg.chat.id
    if isinstance(event, CallbackQuery):
        await event.answer()
        user_id = event.from_user.id

    goals = await db.get_goals(user_id)
    if not goals:
        await msg.answer("У тебя пока нет активных целей. Добавь через /add_goal")
        return

    text = "В какую цель пополняем? Введи номер:\n\n"
    for i, g in enumerate(goals, 1):
        saved = float(g["saved_amount"] or 0)
        target = float(g["target_amount"])
        text += f"{i}. {g['name']} — {format_sum(saved)} / {format_sum(target)} сум\n"

    await state.update_data(goals=[g["id"] for g in goals], goal_names=[g["name"] for g in goals])
    await msg.answer(text)
    await state.set_state(SaveGoalStates.waiting_goal_choice)


@router.message(SaveGoalStates.waiting_goal_choice)
async def save_goal_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    goals = data.get("goals", [])
    try:
        idx = int(message.text.strip()) - 1
        if idx < 0 or idx >= len(goals):
            raise ValueError
    except ValueError:
        await message.answer("Введи номер цели из списка")
        return

    await state.update_data(goal_id=goals[idx], goal_name=data["goal_names"][idx])
    await message.answer(f"Сколько пополняем на «{data['goal_names'][idx]}»? (в сумах)")
    await state.set_state(SaveGoalStates.waiting_amount)


@router.message(SaveGoalStates.waiting_amount)
async def save_goal_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "")
    try:
        if "млн" in text:
            amount = float(text.replace("млн", "")) * 1_000_000
        elif "к" in text:
            amount = float(text.replace("к", "")) * 1_000
        else:
            amount = float(text)
    except ValueError:
        await message.answer("Не понял сумму")
        return

    data = await state.get_data()
    goal = await db.update_goal_saved(data["goal_id"], amount)
    await state.clear()

    new_saved = float(goal.get("saved_amount", 0))
    target = float(goal.get("target_amount", 0))
    bar = progress_bar(new_saved, target)
    pct = format_percent(new_saved, target)

    await message.answer(
        f"✅ Пополнено +{format_sum(amount)} сум\n"
        f"🎯 {data['goal_name']}: {format_sum(new_saved)} / {format_sum(target)} сум\n"
        f"{bar} {pct}"
    )
