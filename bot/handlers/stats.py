from datetime import date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services import supabase_db as db
from bot.utils.formatters import format_sum
from bot.utils.constants import CATEGORY_EMOJI
from bot.keyboards.inline import back_to_menu_btn, history_item_kb

router = Router()

MONTH_NAMES = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    today = date.today()
    stats = await db.get_monthly_stats(message.from_user.id, today.year, today.month)
    month_name = MONTH_NAMES[today.month]

    expense = stats["expense"]
    income = stats["income"]
    balance = income - expense
    by_cat = stats["by_category"]

    text = f"📊 *{month_name} {today.year}*\n\n"
    text += f"🔴 Расходы: {format_sum(expense)} сум\n"

    if by_cat:
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        for cat, amt in sorted_cats[:7]:
            emoji = CATEGORY_EMOJI.get(cat, "📦")
            text += f"  ├ {emoji} {cat.replace('_', '/')}: {format_sum(amt)}\n"

    text += f"\n🟢 Доходы: {format_sum(income)} сум\n"
    sign = "+" if balance >= 0 else ""
    text += f"{'📈' if balance >= 0 else '📉'} Остаток: {sign}{format_sum(balance)} сум"

    await message.answer(text, parse_mode="Markdown", reply_markup=back_to_menu_btn())


@router.message(Command("week"))
async def cmd_week(message: Message):
    stats = await db.get_weekly_stats(message.from_user.id)
    expense = stats["expense"]
    income = stats["income"]
    by_cat = stats["by_category"]
    balance = income - expense

    text = "📅 *Итоги за 7 дней*\n\n"
    text += f"🔴 Расходы: {format_sum(expense)} сум\n"

    if by_cat:
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        for cat, amt in sorted_cats[:5]:
            emoji = CATEGORY_EMOJI.get(cat, "📦")
            text += f"  ├ {emoji} {cat.replace('_', '/')}: {format_sum(amt)}\n"

    text += f"\n🟢 Доходы: {format_sum(income)} сум\n"
    sign = "+" if balance >= 0 else ""
    text += f"{'📈' if balance >= 0 else '📉'} Баланс: {sign}{format_sum(balance)} сум"

    await message.answer(text, parse_mode="Markdown", reply_markup=back_to_menu_btn())


@router.message(Command("history"))
async def cmd_history(message: Message):
    txns = await db.get_recent_transactions(message.from_user.id, limit=10)
    if not txns:
        await message.answer("История транзакций пока пуста.", reply_markup=back_to_menu_btn())
        return

    await message.answer("📋 *Последние транзакции*", parse_mode="Markdown")
    for t in txns:
        type_emoji = "🔴" if t["type"] == "expense" else "🟢"
        cat = t.get("category", "другое")
        cat_emoji = CATEGORY_EMOJI.get(cat, "📦")
        desc = t.get("description", cat)
        amount = format_sum(float(t["amount_uzs"]))
        created = str(t["created_at"])[:10]
        tx_text = f"{type_emoji} {cat_emoji} {desc} — {amount} сум\n_{created}_"
        await message.answer(
            tx_text,
            parse_mode="Markdown",
            reply_markup=history_item_kb(str(t["id"])),
        )
