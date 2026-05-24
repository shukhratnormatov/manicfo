import os
import httpx
from typing import Optional

_rates_cache: dict = {}
_cache_date: Optional[str] = None


async def fetch_rates() -> dict:
    global _rates_cache, _cache_date
    from datetime import date
    today = date.today().isoformat()
    if _cache_date == today and _rates_cache:
        return _rates_cache

    rates = {"USD": 12700.0, "RUB": 138.0}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://cbu.uz/ru/arkhiv-kursov-valyut/json/")
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    code = item.get("Ccy", "")
                    rate = float(item.get("Rate", 0))
                    if code == "USD":
                        rates["USD"] = rate
                    elif code == "RUB":
                        rates["RUB"] = rate
    except Exception:
        pass

    _rates_cache = rates
    _cache_date = today
    return rates


async def to_uzs(amount: float, currency: str) -> float:
    if currency == "UZS":
        return amount
    rates = await fetch_rates()
    rate = rates.get(currency, 1.0)
    return round(amount * rate, 2)


async def get_rates_text() -> str:
    rates = await fetch_rates()
    usd = rates.get("USD", 0)
    rub = rates.get("RUB", 0)
    return (
        f"💱 *Курсы валют*\n\n"
        f"🇺🇸 USD → {usd:,.0f} сум\n"
        f"🇷🇺 RUB → {rub:,.2f} сум\n\n"
        f"_Источник: cbu.uz_"
    )
