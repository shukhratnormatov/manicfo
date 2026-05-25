from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import onboarding_goals_kb, skip_kb
from bot.keyboards.reply import get_main_menu
from bot.services import supabase_db as db

router = Router()


class OnboardingStates(StatesGroup):
    waiting_goal_name = State()
    waiting_goal_amount = State()
    waiting_goal_deadline = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    goals = await db.get_goals(message.from_user.id)
    if goals:
        await message.answer(
            "👋 С возвращением!\n\n"
            "Просто пиши о тратах и доходах:\n"
            "«потратил 50к на продукты» или «получил зарплату 3 млн»\n\n"
            "Команды: /goals /stats /subs /history /rates /help",
            reply_markup=get_main_menu(),
        )
        return

    await message.answer(
        "👋 Привет! Я твой личный финансовый ассистент 🤖\n\n"
        "Просто пиши мне о тратах и доходах обычным языком:\n"
        "«потратил 50к на такси» или «получил зарплату 3 млн»\n\n"
        "Я всё запишу и буду следить за твоими целями.\n\n"
        "Для начала — давай добавим твои цели накопления?",
        reply_markup=onboarding_goals_kb(),
    )


@router.callback_query(F.data.startswith("goal_preset:"))
async def goal_preset_cb(callback: CallbackQuery, state: FSMContext):
    preset = callback.data.split(":", 1)[1]
    await callback.answer()
    if preset == "custom":
        await callback.message.answer("Введи название своей цели:")
        await state.set_state(OnboardingStates.waiting_goal_name)
    else:
        await state.update_data(goal_name=preset)
        await callback.message.answer(
            f"Сколько нужно накопить на «{preset}»? (в сумах)\n"
            f"Пример: 8000000 или 8 млн"
        )
        await state.set_state(OnboardingStates.waiting_goal_amount)


@router.message(OnboardingStates.waiting_goal_name)
async def goal_name_input(message: Message, state: FSMContext):
    await state.update_data(goal_name=message.text.strip())
    await message.answer(
        f"Сколько нужно накопить на «{message.text.strip()}»? (в сумах)\n"
        f"Пример: 8000000 или 8 млн"
    )
    await state.set_state(OnboardingStates.waiting_goal_amount)


@router.message(OnboardingStates.waiting_goal_amount)
async def goal_amount_input(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "")
    try:
        if "млн" in text or "m" in text:
            amount = float(text.replace("млн", "").replace("m", "")) * 1_000_000
        elif "к" in text or "k" in text:
            amount = float(text.replace("к", "").replace("k", "")) * 1_000
        else:
            amount = float(text)
    except ValueError:
        await message.answer("Не понял сумму. Попробуй ещё раз, например: 8000000")
        return

    await state.update_data(goal_amount=amount)
    await message.answer(
        "К какой дате хочешь накопить? (формат: 01.12.2025)\nИли пропусти:",
        reply_markup=skip_kb("skip_deadline"),
    )
    await state.set_state(OnboardingStates.waiting_goal_deadline)


@router.callback_query(F.data == "skip_deadline", OnboardingStates.waiting_goal_deadline)
async def skip_deadline(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _save_onboarding_goal(callback.message, state, deadline=None)


@router.message(OnboardingStates.waiting_goal_deadline)
async def goal_deadline_input(message: Message, state: FSMContext):
    text = message.text.strip()
    deadline = None
    try:
        from datetime import datetime
        deadline = datetime.strptime(text, "%d.%m.%Y").date().isoformat()
    except ValueError:
        pass
    await _save_onboarding_goal(message, state, deadline=deadline)


async def _save_onboarding_goal(message: Message, state: FSMContext, deadline):
    data = await state.get_data()
    name = data.get("goal_name", "Цель")
    amount = data.get("goal_amount", 0)
    user_id = message.chat.id

    goals = await db.get_goals(user_id)
    priority = len(goals) + 1

    await db.add_goal(
        user_id=user_id,
        name=name,
        target_amount=amount,
        deadline=deadline,
        priority=priority,
    )
    await state.clear()

    from bot.utils.formatters import format_sum
    await message.answer(
        f"✅ Цель «{name}» добавлена!\n"
        f"Нужно накопить: {format_sum(amount)} сум\n\n"
        f"Добавить ещё одну цель?",
        reply_markup=onboarding_goals_kb(),
    )


@router.callback_query(F.data == "nav:menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 *Команды бота*\n\n"
        "Просто напиши о трате или доходе — бот всё поймёт:\n"
        "«потратил 50к на продукты»\n"
        "«получил зарплату 3 млн»\n\n"
        "*Команды:*\n"
        "/goals — цели накопления\n"
        "/stats — статистика за месяц\n"
        "/week — итоги за неделю\n"
        "/history — последние 10 транзакций\n"
        "/subs — подписки\n"
        "/add\\_sub — добавить подписку\n"
        "/add\\_goal — добавить цель\n"
        "/save — пополнить цель\n"
        "/rates — курсы валют\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )
