from datetime import date
from typing import Optional
from bot.utils.formatters import months_to_human, forecast_date


def calc_months_to_goal(target: float, saved: float, monthly_rate: float) -> Optional[int]:
    remaining = target - saved
    if remaining <= 0:
        return 0
    if monthly_rate <= 0:
        return None
    return int(remaining / monthly_rate) + 1


def goal_forecast_text(goal: dict, monthly_rate: float) -> str:
    name = goal["name"]
    saved = float(goal["saved_amount"] or 0)
    target = float(goal["target_amount"])
    pct = min(saved / target * 100, 100) if target > 0 else 0

    from bot.utils.formatters import progress_bar, format_sum
    bar = progress_bar(saved, target)
    lines = [
        f"🎯 *{name}*",
        f"Накоплено: {format_sum(saved)} / {format_sum(target)} сум ({pct:.0f}%)",
        f"{bar} {pct:.0f}%",
    ]

    if goal.get("deadline"):
        lines.append(f"📅 Дедлайн: {goal['deadline']}")

    months = calc_months_to_goal(target, saved, monthly_rate)
    if months is None:
        lines.append("⏳ Темп накоплений не определён")
    elif months == 0:
        lines.append("✅ Цель достигнута!")
    else:
        lines.append(f"При +{format_sum(monthly_rate)}/мес → {months_to_human(months)}")
        lines.append(f"📆 Накопишь примерно: {forecast_date(months)}")

    return "\n".join(lines)
