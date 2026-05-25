from datetime import date
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot.services import supabase_db as db, claude_parser, currency as cur
from bot.utils.formatters import format_sum
from bot.utils.constants import CATEGORY_EMOJI

router = Router()

MONTH_NAMES = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


@router.message(StateFilter(default_state))
async def handle_free_text(message: Message):
    text = message.text or ""
    if text.startswith("/"):
        return

    parsed = await claude_parser.parse_transaction(text)
    if not parsed:
        await message.answer(
            "🤔 Не понял. Попробуй написать иначе:\n"
            "«потратил 50к на продукты» или «получил зарплату 3 млн»"
        )
        return

    amount = float(parsed["amount"])
    currency = parsed.get("currency", "UZS")
    amount_uzs = await cur.to_uzs(amount, currency)
    category = parsed.get("category", "другое")
    description = parsed.get("description", "")
    type_ = parsed["type"]

    await db.add_transaction(
        user_id=message.from_user.id,
        type_=type_,
        amount=amount,
        currency=currency,
        amount_uzs=amount_uzs,
        category=category,
        description=description,
    )

    emoji = "✅" if type_ == "expense" else "💚"
    type_label = "Расход" if type_ == "expense" else "Доход"
    cat_emoji = CATEGORY_EMOJI.get(category, "📦")
    currency_label = "" if currency == "UZS" else f" ({currency})"

    response = (
        f"{emoji} *{type_label} записан*\n"
        f"{cat_emoji} {description} — {format_sum(amount_uzs)} сум{currency_label}\n"
    )

    if type_ == "expense":
        today = date.today()
        month_total = await db.get_category_month_total(
            message.from_user.id, category, today.year, today.month
        )
        month_name = MONTH_NAMES[today.month]
        budget = await db.get_budget_limit(
            message.from_user.id, category, today.replace(day=1).isoformat()
        )
        response += f"\n📊 {cat_emoji} {category.replace('_', '/')} в {month_name}: {format_sum(month_total)} сум"
        if budget:
            remaining = budget - month_total
            if remaining > 0:
                response += f"\nДо лимита: {format_sum(remaining)} сум"
            else:
                response += f"\n⚠️ Лимит превышен на {format_sum(-remaining)} сум"

    elif type_ == "income":
        goals = await db.get_goals(message.from_user.id)
        if goals:
            response += "\n\n🎯 Рекомендую отложить на цели:"
            remaining_income = amount_uzs
            for g in goals[:3]:
                needed = float(g["target_amount"]) - float(g["saved_amount"] or 0)
                if needed <= 0:
                    continue
                suggest = min(needed, remaining_income * 0.1)
                suggest = round(suggest / 1000) * 1000
                if suggest > 0:
                    new_total = float(g["saved_amount"] or 0) + suggest
                    response += (
                        f"\n🔹 {g['name']} (приор. {g['priority']}): "
                        f"+{format_sum(suggest)} → итого {format_sum(new_total)} / {format_sum(float(g['target_amount']))}"
                    )

    await message.answer(response, parse_mode="Markdown")
