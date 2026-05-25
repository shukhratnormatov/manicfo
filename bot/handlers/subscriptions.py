from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import subs_actions_kb
from bot.services import supabase_db as db, claude_parser, currency as cur
from bot.utils.formatters import format_sum, days_until

router = Router()


class AddSubStates(StatesGroup):
    waiting_name = State()
    waiting_amount = State()
    waiting_day = State()


def _get_next_billing(subs: list) -> dict | None:
    if not subs:
        return None
    enriched = []
    for s in subs:
        d = days_until(s["billing_day"])
        enriched.append({**s, "days_until": d})
    enriched.sort(key=lambda x: x["days_until"])
    return enriched[0] if enriched else None


@router.message(Command("subs"))
async def cmd_subs(message: Message):
    subs = await db.get_active_subscriptions(message.from_user.id)
    if not subs:
        await message.answer(
            "У тебя пока нет подписок.\n"
            "Добавь первую командой /add_sub\n"
            "Или напиши: «добавил подписку Netflix 85к каждый месяц 5-го числа»"
        )
        return

    total_uzs = sum(s["amount_uzs"] for s in subs)
    rates = await cur.fetch_rates()
    usd_rate = rates.get("USD", 12700)
    total_usd = total_uzs / usd_rate

    text = "📱 *Твои подписки*\n\n"
    text += f"✅ Активные — {format_sum(total_uzs)} сум/мес (~${total_usd:.1f})\n\n"

    for i, sub in enumerate(sorted(subs, key=lambda x: x["billing_day"] or 31), 1):
        day = sub.get("billing_day", "?")
        text += f"{i}. {sub['name']}  {format_sum(sub['amount_uzs'])} сум • {day}-го числа\n"

    next_sub = _get_next_billing(subs)
    if next_sub:
        text += (
            f"\n⏰ Ближайшее: {next_sub['name']} — "
            f"через {next_sub['days_until']} дн. ({format_sum(next_sub['amount_uzs'])} сум)"
        )

    await message.answer(text, parse_mode="Markdown", reply_markup=subs_actions_kb())


@router.message(Command("add_sub"))
@router.callback_query(F.data == "sub_add")
async def cmd_add_sub(event, state: FSMContext):
    msg = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer("Название подписки? Например: Netflix, Spotify, VPN")
    await state.set_state(AddSubStates.waiting_name)


@router.message(AddSubStates.waiting_name)
async def add_sub_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Сумма и валюта? Например: 85к или 10$")
    await state.set_state(AddSubStates.waiting_amount)


@router.message(AddSubStates.waiting_amount)
async def add_sub_amount(message: Message, state: FSMContext):
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

    await state.update_data(amount=amount, currency=currency)
    await message.answer("Какого числа списывается? Введи число от 1 до 31:")
    await state.set_state(AddSubStates.waiting_day)


@router.message(AddSubStates.waiting_day)
async def add_sub_day(message: Message, state: FSMContext):
    try:
        day = int(message.text.strip())
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 1 до 31")
        return

    data = await state.get_data()
    amount_uzs = await cur.to_uzs(data["amount"], data["currency"])

    await db.add_subscription(
        user_id=message.from_user.id,
        name=data["name"],
        amount=data["amount"],
        currency=data["currency"],
        amount_uzs=amount_uzs,
        billing_day=day,
    )
    await state.clear()

    subs = await db.get_active_subscriptions(message.from_user.id)
    total = sum(s["amount_uzs"] for s in subs)

    await message.answer(
        f"✅ *{data['name']}* добавлен — {format_sum(amount_uzs)} сум/мес, {day}-го числа\n\n"
        f"📊 Итого подписок: {format_sum(total)} сум/мес",
        parse_mode="Markdown",
    )
