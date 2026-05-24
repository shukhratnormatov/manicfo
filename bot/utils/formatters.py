from datetime import date
from typing import Optional


def format_sum(amount: float, currency: str = "UZS") -> str:
    if currency == "UZS":
        return f"{amount:,.0f}".replace(",", " ")
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "RUB":
        return f"{amount:,.0f} ₽".replace(",", " ")
    return f"{amount:,.0f}".replace(",", " ")


def progress_bar(current: float, target: float, length: int = 16) -> str:
    if target <= 0:
        return "░" * length
    pct = min(current / target, 1.0)
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def format_percent(current: float, target: float) -> str:
    if target <= 0:
        return "0%"
    return f"{min(current / target * 100, 100):.0f}%"


def months_to_human(months: int) -> str:
    if months <= 0:
        return "уже!"
    if months == 1:
        return "1 месяц"
    if 2 <= months <= 4:
        return f"{months} месяца"
    if 5 <= months <= 12:
        return f"{months} месяцев"
    years = months // 12
    rem = months % 12
    parts = []
    if years == 1:
        parts.append("1 год")
    elif 2 <= years <= 4:
        parts.append(f"{years} года")
    else:
        parts.append(f"{years} лет")
    if rem:
        parts.append(f"{rem} мес.")
    return " ".join(parts)


def forecast_date(months: int) -> str:
    from datetime import date
    import calendar
    today = date.today()
    month = today.month + months
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    month_names = [
        "", "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
    ]
    return f"{month_names[month]} {year}"


def days_until(day_of_month: int) -> int:
    today = date.today()
    target = date(today.year, today.month, day_of_month)
    if target < today:
        import calendar
        _, days_in_month = calendar.monthrange(today.year, today.month)
        if today.month == 12:
            target = date(today.year + 1, 1, day_of_month)
        else:
            target = date(today.year, today.month + 1, day_of_month)
    return (target - today).days
