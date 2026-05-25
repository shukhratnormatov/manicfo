from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import EditStates
from bot.services import supabase_db as db, claude_parser, currency as cur
from bot.keyboards.reply import get_main_menu

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
