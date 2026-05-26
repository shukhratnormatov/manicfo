from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import EditStates, EditSubStates, EditGoalStates
from bot.services import supabase_db as db, claude_parser, currency as cur
from bot.keyboards.reply import get_main_menu, MENU_BUTTONS

router = Router()


@router.callback_query(F.data.startswith("edit:tx:"))
async def edit_transaction_cb(callback: CallbackQuery, state: FSMContext):
    tx_id = callback.data[len("edit:tx:"):]
    await state.set_state(EditStates.waiting_new_input)
    await state.update_data(tx_id=tx_id)
    await callback.answer()
    await callback.message.answer(
        "✏️ Введи новое описание транзакции в обычном формате:\n"
        "Например: «потратил 50к на продукты»"
    )


@router.message(EditStates.waiting_new_input)
async def process_edit_input(message: Message, state: FSMContext):
    data = await state.get_data()
    tx_id = data.get("tx_id")

    parsed = await claude_parser.parse_transaction(message.text or "")
    if not parsed:
        await message.answer(
            "🤔 Не понял. Попробуй ещё раз:\n"
            "«потратил 50к на продукты» или «получил зарплату 3 млн»"
        )
        return

    amount = float(parsed["amount"])
    currency = parsed.get("currency", "UZS")
    amount_uzs = await cur.to_uzs(amount, currency)

    fields = {
        "type": parsed["type"],
        "amount": amount,
        "currency": currency,
        "amount_uzs": amount_uzs,
        "category": parsed.get("category", "другое"),
        "description": parsed.get("description", ""),
    }

    updated = await db.update_transaction(tx_id, message.from_user.id, **fields)
    await state.clear()

    if updated:
        await message.answer("✅ Транзакция обновлена!", reply_markup=get_main_menu())
    else:
        await message.answer(
            "❌ Не удалось обновить. Транзакция не найдена.",
            reply_markup=get_main_menu(),
        )


@router.callback_query(F.data.startswith("delete:tx:"))
async def delete_transaction_cb(callback: CallbackQuery):
    tx_id = callback.data[len("delete:tx:"):]
    deleted = await db.delete_transaction(tx_id, callback.from_user.id)
    await callback.answer()
    if deleted:
        await callback.message.edit_text("🗑 Транзакция удалена")
    else:
        await callback.message.answer("❌ Транзакция не найдена")


# ── Редактирование подписок ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit:sub:"))
async def edit_sub_cb(callback: CallbackQuery, state: FSMContext):
    sub_id = callback.data[len("edit:sub:"):]
    await state.set_state(EditSubStates.waiting_name)
    await state.update_data(sub_id=sub_id)
    await callback.answer()
    await callback.message.answer("✏️ Новое название подписки:")


@router.message(EditSubStates.waiting_name, ~F.text.in_(MENU_BUTTONS))
async def process_edit_sub_name(message: Message, state: FSMContext):
    await state.update_data(new_name=message.text.strip())
    await message.answer("Новая сумма и валюта (например: 85к или 10$):")
    await state.set_state(EditSubStates.waiting_amount)


@router.message(EditSubStates.waiting_amount, ~F.text.in_(MENU_BUTTONS))
async def process_edit_sub_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "")
    currency = "UZS"
    if "$" in text or "usd" in text:
        currency = "USD"
        text = text.replace("$", "").replace("usd", "")
    elif "₽" in text or "rub" in text:
        currency = "RUB"
        text = text.replace("₽", "").replace("rub", "")
    try:
        if "млн" in text:
            amount = float(text.replace("млн", "")) * 1_000_000
        elif "к" in text:
            amount = float(text.replace("к", "")) * 1_000
        else:
            amount = float(text)
    except ValueError:
        await message.answer("Не понял сумму, попробуй: 85к или 85000")
        return
    await state.update_data(new_amount=amount, new_currency=currency)
    await message.answer("Какого числа списывается? (1-31):")
    await state.set_state(EditSubStates.waiting_day)


@router.message(EditSubStates.waiting_day, ~F.text.in_(MENU_BUTTONS))
async def process_edit_sub_day(message: Message, state: FSMContext):
    try:
        day = int(message.text.strip())
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 1 до 31")
        return

    data = await state.get_data()
    amount_uzs = await cur.to_uzs(data["new_amount"], data["new_currency"])
    updated = await db.update_subscription(
        data["sub_id"],
        message.from_user.id,
        name=data["new_name"],
        amount=data["new_amount"],
        currency=data["new_currency"],
        amount_uzs=amount_uzs,
        billing_day=day,
    )
    await state.clear()
    if updated:
        await message.answer("✅ Подписка обновлена!", reply_markup=get_main_menu())
    else:
        await message.answer("❌ Подписка не найдена.", reply_markup=get_main_menu())


@router.callback_query(F.data.startswith("delete:sub:"))
async def delete_sub_cb(callback: CallbackQuery):
    sub_id = callback.data[len("delete:sub:"):]
    deleted = await db.delete_subscription(sub_id, callback.from_user.id)
    await callback.answer()
    if deleted:
        await callback.message.edit_text("🗑 Подписка удалена")
    else:
        await callback.message.answer("❌ Подписка не найдена")


# ── Редактирование целей ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit:goal:"))
async def edit_goal_cb(callback: CallbackQuery, state: FSMContext):
    goal_id = callback.data[len("edit:goal:"):]
    await state.set_state(EditGoalStates.waiting_name)
    await state.update_data(goal_id=goal_id)
    await callback.answer()
    await callback.message.answer("✏️ Новое название цели:")


@router.message(EditGoalStates.waiting_name, ~F.text.in_(MENU_BUTTONS))
async def process_edit_goal_name(message: Message, state: FSMContext):
    await state.update_data(new_name=message.text.strip())
    await message.answer("Новая целевая сумма (в сумах):")
    await state.set_state(EditGoalStates.waiting_amount)


@router.message(EditGoalStates.waiting_amount, ~F.text.in_(MENU_BUTTONS))
async def process_edit_goal_amount(message: Message, state: FSMContext):
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
        await message.answer("Не понял сумму, попробуй: 8 млн или 8000000")
        return

    data = await state.get_data()
    updated = await db.update_goal(
        data["goal_id"],
        message.from_user.id,
        name=data["new_name"],
        target_amount=amount,
    )
    await state.clear()
    if updated:
        await message.answer("✅ Цель обновлена!", reply_markup=get_main_menu())
    else:
        await message.answer("❌ Цель не найдена.", reply_markup=get_main_menu())


@router.callback_query(F.data.startswith("delete:goal:"))
async def delete_goal_cb(callback: CallbackQuery):
    goal_id = callback.data[len("delete:goal:"):]
    deleted = await db.delete_goal(goal_id, callback.from_user.id)
    await callback.answer()
    if deleted:
        await callback.message.edit_text("🗑 Цель удалена")
    else:
        await callback.message.answer("❌ Цель не найдена")
