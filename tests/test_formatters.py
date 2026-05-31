"""
Тесты чистых функций форматирования — без внешних зависимостей.
"""
import pytest
from bot.utils.formatters import (
    format_sum,
    progress_bar,
    format_percent,
    months_to_human,
)


# ── format_sum ───────────────────────────────────────────────────────────────

class TestFormatSum:
    def test_uzs_zero(self):
        assert format_sum(0) == "0"

    def test_uzs_basic(self):
        assert format_sum(50000) == "50 000"

    def test_uzs_large(self):
        assert format_sum(3_000_000) == "3 000 000"

    def test_uzs_explicit_currency(self):
        assert format_sum(150_000, "UZS") == "150 000"

    def test_usd(self):
        result = format_sum(12.5, "USD")
        assert result == "$12.50"

    def test_usd_integer(self):
        result = format_sum(100, "USD")
        assert result == "$100.00"

    def test_rub(self):
        result = format_sum(5000, "RUB")
        assert "5 000" in result
        assert "₽" in result

    def test_unknown_currency_falls_back(self):
        # Неизвестная валюта — возвращает числовое представление
        result = format_sum(1000, "EUR")
        assert "1 000" in result


# ── progress_bar ─────────────────────────────────────────────────────────────

class TestProgressBar:
    def test_zero_progress(self):
        bar = progress_bar(0, 1_000_000)
        assert bar == "░" * 16
        assert "█" not in bar

    def test_half_progress(self):
        bar = progress_bar(500_000, 1_000_000)
        assert bar.count("█") == 8
        assert bar.count("░") == 8

    def test_full_progress(self):
        bar = progress_bar(1_000_000, 1_000_000)
        assert bar == "█" * 16
        assert "░" not in bar

    def test_over_target_capped_at_full(self):
        bar = progress_bar(2_000_000, 1_000_000)
        assert bar == "█" * 16

    def test_zero_target_returns_empty_bar(self):
        bar = progress_bar(500, 0)
        assert bar == "░" * 16

    def test_custom_length(self):
        bar = progress_bar(5, 10, length=10)
        assert len(bar) == 10
        assert bar.count("█") == 5

    def test_default_length_is_16(self):
        bar = progress_bar(1, 4)
        assert len(bar) == 16


# ── format_percent ────────────────────────────────────────────────────────────

class TestFormatPercent:
    def test_zero(self):
        assert format_percent(0, 100) == "0%"

    def test_50_percent(self):
        assert format_percent(50, 100) == "50%"

    def test_100_percent(self):
        assert format_percent(100, 100) == "100%"

    def test_over_100_capped(self):
        assert format_percent(200, 100) == "100%"

    def test_zero_target(self):
        assert format_percent(50, 0) == "0%"


# ── months_to_human ───────────────────────────────────────────────────────────

class TestMonthsToHuman:
    def test_zero_months(self):
        assert months_to_human(0) == "уже!"

    def test_negative(self):
        assert months_to_human(-1) == "уже!"

    def test_one_month(self):
        assert months_to_human(1) == "1 месяц"

    def test_two_months(self):
        result = months_to_human(2)
        assert "2" in result and "месяца" in result

    def test_four_months(self):
        result = months_to_human(4)
        assert "4" in result and "месяца" in result

    def test_five_months(self):
        result = months_to_human(5)
        assert "5" in result and "месяцев" in result

    def test_twelve_months(self):
        result = months_to_human(12)
        assert "12" in result and "месяцев" in result

    def test_thirteen_months_is_one_year(self):
        result = months_to_human(13)
        assert "год" in result or "лет" in result

    def test_24_months_is_2_years(self):
        result = months_to_human(24)
        assert "2" in result
