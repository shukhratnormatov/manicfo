import asyncio
from datetime import date

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery

from bot.services import supabase_db as db, claude_parser, currency as cur
from bot.utils.formatters import format_sum, format_amount_display, progress_bar, format_percent
from bot.utils.constants import CATEGORY_EMOJI
from bot.keyboards.inline import cancel_tx_kb

router = Router()

MONTH_NAMES = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]

# tx_id-ы транзакций, для которых ещё не истёк таймаут отмены
_pending_cancel: set = set()


async def expire_cancel_button(msg: Message, tx_id: str) -> None:
    await asyncio.sleep(60)
    _pending_cancel.discard(tx_id)
    try:
        await msg.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # сообщение могли удалить — не критично


# ── Маппинг кнопок ReplyKeyboard ────────────────────────────────────────────

@router.message(F.text == "📊 Статистика")
async def menu_btn_stats(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.stats import cmd_stats
    await cmd_stats(message)


@router.message(F.text == "🎯 Цели")
async def menu_btn_goals(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.goals import cmd_goals
    await cmd_goals(message)


@router.message(F.text == "📋 История")
async def menu_btn_history(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.stats import cmd_history
    await cmd_history(message)


@router.message(F.text == "📱 Подписки")
async def menu_btn_subs(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.subscriptions import cmd_subs
    await cmd_subs(message)


@router.message(F.text == "💱 Курсы")
async def menu_btn_rates(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.rates import cmd_rates
    await cmd_rates(message)


@router.message(F.text == "📅 Неделя")
async def menu_btn_week(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.stats import cmd_week
    await cmd_week(message)


@router.message(F.text == "💰 Бюджет")
async def menu_btn_budget(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.budget import cmd_budget
    await cmd_budget(message, state)


# ── Callback: отмена транзакции ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_tx:"))
async def cancel_transaction_cb(callback: CallbackQuery):
    tx_id = callback.data[len("cancel_tx:"):]
    if tx_id in _pending_cancel:
        _pending_cancel.discard(tx_id)
        await db.delete_transaction(tx_id, callback.from_user.id)
        await callback.message.edit_text("↩️ Транзакция отменена")
        await callback.answer()
    else:
        await callback.answer(
            "⏱ Время истекло. Используй /history для редактирования",
            show_alert=True,
        )


# ── Обработка одной транзакции ───────────────────────────────────────────────

async def _process_single_tx(message: Message, parsed: dict) -> None:
    """Записывает одну распознанную транзакцию и отправляет подтверждение."""
    type_ = parsed["type"]
    amount = float(parsed["amount"])
    currency = parsed.get("currency", "UZS")

    # ── BUG-3: Валидация суммы ────────────────────────────────────────────────
    if amount <= 0:
        await message.answer(
            "🤔 Не понял сумму. Укажи сумму явно:\n"
            "«потратил 50к на продукты» или «получил зарплату 3 млн»"
        )
        return

    amount_uzs = await cur.to_uzs(amount, currency)
    category = parsed.get("category", "другое")
    description = parsed.get("description", "")

    # ── BUG-5: Автоматическое зачисление в цель при категории "накопления" ────
    if type_ == "expense" and category == "накопления":
        goal = await db.find_goal_by_keyword(message.from_user.id, description)
        if goal:
            await db.update_goal_saved(goal["id"], amount_uzs)
            new_saved = float(goal["saved_amount"] or 0) + amount_uzs
            goal_target = float(goal["target_amount"])
            bar = progress_bar(new_saved, goal_target)
            pct = format_percent(new_saved, goal_target)
            await message.answer(
                f"💰 *Накопления записаны*\n"
                f"Цель: *{goal['name']}*\n"
                f"+{format_sum(amount_uzs)} сум → {format_sum(new_saved)} / {format_sum(goal_target)} сум\n"
                f"{bar} {pct}",
                parse_mode="Markdown",
            )
            return
        # Нет активных целей — падаем в обычный расход

    tx = await db.add_transaction(
        user_id=message.from_user.id,
        type_=type_,
        amount=amount,
        currency=currency,
        amount_uzs=amount_uzs,
        category=category,
        description=description,
    )
    tx_id = (tx or {}).get("id")

    emoji = "✅" if type_ == "expense" else "💚"
    type_label = "Расход" if type_ == "expense" else "Доход"
    cat_emoji = CATEGORY_EMOJI.get(category, "📦")

    # ── BUG-2: Форматирование суммы с оригинальной валютой ───────────────────
    response = (
        f"{emoji} *{type_label} записан*\n"
        f"{cat_emoji} {description} — {format_amount_display(amount, currency, amount_uzs)}\n"
    )

    if type_ == "expense":
        today = date.today()
        month_total = await db.get_category_month_total(
            message.from_user.id, category, today.year, today.month
        )
        month_name = MONTH_NAMES[today.month]
        budget_limit = await db.get_budget_limit(
            message.from_user.id, category, today.replace(day=1).isoformat()
        )
        response += f"\n📊 {cat_emoji} {category.replace('_', '/')} в {month_name}: {format_sum(month_total)} сум"
        if budget_limit:
            remaining = budget_limit - month_total
            if remaining > 0:
                response += f"\nДо лимита: {format_sum(remaining)} сум"
            else:
                response += f"\n⚠️ Лимит превышен на {format_sum(-remaining)} сум"

        # ── FEAT-1: Статус месячного бюджета после расхода ───────────────────
        monthly_budget = await db.get_monthly_budget(message.from_user.id)
        if monthly_budget:
            total_spent = await db.get_total_expenses(message.from_user.id, today.year, today.month)
            remaining_budget = monthly_budget - total_spent
            if remaining_budget > 0:
                response += f"\n💰 Бюджет: {format_sum(remaining_budget)} сум осталось"
            else:
                response += f"\n💰 ⚠️ Бюджет превышен на {format_sum(-remaining_budget)} сум"

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

    if tx_id:
        _pending_cancel.add(tx_id)
        sent_msg = await message.answer(response, reply_markup=cancel_tx_kb(tx_id), parse_mode="Markdown")
        asyncio.create_task(expire_cancel_button(sent_msg, tx_id))
    else:
        await message.answer(response, parse_mode="Markdown")


# ── Основной хендлер свободного текста ──────────────────────────────────────

@router.message(StateFilter(default_state))
async def handle_free_text(message: Message, state: FSMContext):
    text = message.text or ""
    if text.startswith("/"):
        return

    parsed_list = await claude_parser.parse_transaction(text)
    if not parsed_list:
        await message.answer(
            "🤔 Не понял. Попробуй написать иначе:\n"
            "«потратил 50к на продукты» или «получил зарплату 3 млн»"
        )
        return

    # ── Одна запись: обрабатываем интент или unknown ─────────────────────────
    if len(parsed_list) == 1:
        parsed = parsed_list[0]
        type_ = parsed["type"]

        # ── FEAT-2: Диспетчер интентов ───────────────────────────────────────
        if type_ == "intent":
            intent = parsed.get("intent_action", "")
            if intent == "show_stats":
                from bot.handlers.stats import cmd_stats
                await cmd_stats(message)
            elif intent == "show_goals":
                from bot.handlers.goals import cmd_goals
                await cmd_goals(message)
            elif intent == "show_history":
                from bot.handlers.stats import cmd_history
                await cmd_history(message)
            elif intent == "show_subs":
                from bot.handlers.subscriptions import cmd_subs
                await cmd_subs(message)
            elif intent == "show_rates":
                from bot.handlers.rates import cmd_rates
                await cmd_rates(message)
            elif intent == "show_week":
                from bot.handlers.stats import cmd_week
                await cmd_week(message)
            elif intent == "show_budget":
                from bot.handlers.budget import cmd_budget
                await cmd_budget(message, state)
            else:
                await message.answer(
                    "🤔 Не понял. Попробуй написать иначе:\n"
                    "«потратил 50к на продукты» или «получил зарплату 3 млн»"
                )
            return

        # ── BUG-3: Фильтр нераспознанных транзакций ──────────────────────────
        if type_ == "unknown":
            await message.answer(
                "🤔 Не понял. Попробуй написать иначе:\n"
                "«потратил 50к на продукты» или «получил зарплату 3 млн»"
            )
            return

    # ── Одна или несколько транзакций: записываем каждую ────────────────────
    for parsed in parsed_list:
        if parsed["type"] in ("unknown", "intent"):
            continue
        await _process_single_tx(message, parsed)
