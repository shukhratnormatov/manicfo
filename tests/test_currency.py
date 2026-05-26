"""
Тесты конвертации валют (currency.py).
HTTP-запросы к cbu.uz полностью замокированы.
"""
from datetime import date

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import bot.services.currency as currency_module
from bot.services.currency import fetch_rates, to_uzs, get_rates_text

# Дата сегодня — кэш в fetch_rates() срабатывает только если _cache_date == today
_TODAY = date.today().isoformat()

CBU_SAMPLE = [
    {"Ccy": "USD", "Rate": "12800.0"},
    {"Ccy": "RUB", "Rate": "140.0"},
    {"Ccy": "EUR", "Rate": "13500.0"},  # лишняя валюта — должна игнорироваться
]


@pytest.fixture(autouse=True)
def reset_cache():
    """Сбрасываем кэш курсов перед каждым тестом."""
    currency_module._rates_cache = {}
    currency_module._cache_date = None
    yield
    currency_module._rates_cache = {}
    currency_module._cache_date = None


def _mock_httpx(status: int = 200, json_data=None):
    """Создаёт мок httpx.AsyncClient с заданным ответом."""
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or CBU_SAMPLE

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ── fetch_rates ───────────────────────────────────────────────────────────────

class TestFetchRates:
    async def test_parses_usd_and_rub_from_response(self):
        with patch("httpx.AsyncClient", return_value=_mock_httpx()):
            rates = await fetch_rates()

        assert rates["USD"] == 12800.0
        assert rates["RUB"] == 140.0

    async def test_ignores_extra_currencies(self):
        with patch("httpx.AsyncClient", return_value=_mock_httpx()):
            rates = await fetch_rates()

        assert "EUR" not in rates

    async def test_falls_back_to_defaults_on_http_error(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            rates = await fetch_rates()

        # Дефолтные значения из кода
        assert "USD" in rates
        assert "RUB" in rates
        assert rates["USD"] > 0
        assert rates["RUB"] > 0

    async def test_falls_back_on_non_200_status(self):
        with patch("httpx.AsyncClient", return_value=_mock_httpx(status=503)):
            rates = await fetch_rates()

        # При non-200 данные не парсятся, используются дефолты (12700 / 138)
        assert rates["USD"] == 12700.0
        assert rates["RUB"] == 138.0

    async def test_result_is_cached_for_same_day(self):
        with patch("httpx.AsyncClient", return_value=_mock_httpx()) as mock_cls:
            await fetch_rates()
            await fetch_rates()  # второй вызов — из кэша

        # AsyncClient должен быть создан только один раз
        assert mock_cls.call_count == 1

    async def test_cache_respects_date(self):
        """Кэш привязан к дате — новый день сбрасывает кэш."""
        currency_module._rates_cache = {"USD": 11000.0, "RUB": 120.0}
        currency_module._cache_date = "2000-01-01"  # устаревшая дата

        with patch("httpx.AsyncClient", return_value=_mock_httpx()):
            rates = await fetch_rates()

        assert rates["USD"] == 12800.0  # свежие данные


# ── to_uzs ────────────────────────────────────────────────────────────────────

class TestToUzs:
    async def test_uzs_passthrough(self):
        result = await to_uzs(100_000, "UZS")
        assert result == 100_000.0

    async def test_usd_conversion(self):
        # Кэш срабатывает только когда _cache_date == today
        currency_module._rates_cache = {"USD": 12800.0, "RUB": 140.0}
        currency_module._cache_date = _TODAY

        result = await to_uzs(10, "USD")
        assert result == 128_000.0

    async def test_rub_conversion(self):
        currency_module._rates_cache = {"USD": 12800.0, "RUB": 140.0}
        currency_module._cache_date = _TODAY

        result = await to_uzs(100, "RUB")
        assert result == 14_000.0

    async def test_unknown_currency_rate_is_1(self):
        currency_module._rates_cache = {"USD": 12800.0, "RUB": 140.0}
        currency_module._cache_date = _TODAY

        result = await to_uzs(500, "GBP")
        assert result == 500.0

    async def test_zero_amount(self):
        result = await to_uzs(0, "UZS")
        assert result == 0.0


# ── get_rates_text ────────────────────────────────────────────────────────────

class TestGetRatesText:
    async def test_contains_usd_and_rub(self):
        currency_module._rates_cache = {"USD": 12800.0, "RUB": 140.0}
        currency_module._cache_date = _TODAY

        text = await get_rates_text()
        assert "USD" in text
        assert "RUB" in text
        assert "12 800" in text or "12800" in text or "12,800" in text

    async def test_contains_source_label(self):
        currency_module._rates_cache = {"USD": 12800.0, "RUB": 140.0}
        currency_module._cache_date = _TODAY

        text = await get_rates_text()
        assert "cbu.uz" in text
