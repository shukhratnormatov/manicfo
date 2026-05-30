"""
Тесты NLP-парсера (claude_parser.py).
Все вызовы к Anthropic API замокированы — реальных запросов нет.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

import bot.services.claude_parser as parser_module
from bot.services.claude_parser import parse_transaction, parse_subscription_nlp


def _make_claude_response(text: str) -> MagicMock:
    """Создаёт мок ответа Anthropic Messages API."""
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    return response


def _make_client(response_text: str) -> MagicMock:
    """Создаёт мок claude-клиента с заданным текстом ответа."""
    client = MagicMock()
    client.messages.create.return_value = _make_claude_response(response_text)
    return client


@pytest.fixture(autouse=True)
def reset_parser_client():
    """Сбрасываем кэшированный клиент перед каждым тестом."""
    original = parser_module._client
    parser_module._client = None
    yield
    parser_module._client = original


# ── parse_transaction ─────────────────────────────────────────────────────────

class TestParseTransaction:
    async def test_expense_returns_list(self):
        payload = {
            "type": "expense",
            "amount": 50000,
            "currency": "UZS",
            "category": "транспорт",
            "description": "такси",
        }
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("потратил 50к на такси")

        assert result is not None
        assert len(result) == 1
        assert result[0]["type"] == "expense"
        assert result[0]["amount"] == 50000
        assert result[0]["category"] == "транспорт"

    async def test_income_returns_list(self):
        payload = {
            "type": "income",
            "amount": 3_000_000,
            "currency": "UZS",
            "category": "зарплата",
            "description": "зарплата",
        }
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("получил зарплату 3 млн")

        assert result is not None
        assert result[0]["type"] == "income"
        assert result[0]["amount"] == 3_000_000

    async def test_unknown_type_returns_list(self):
        """type='unknown' теперь возвращается как список — handle_free_text покажет 'не понял'."""
        payload = {"type": "unknown", "amount": 0}
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("привет как дела")

        assert result is not None
        assert result[0]["type"] == "unknown"

    async def test_intent_type_returns_list(self):
        """type='intent' должен возвращаться как список для диспетчеризации в handle_free_text."""
        payload = {
            "type": "intent",
            "intent_action": "show_stats",
            "amount": 0,
            "currency": "UZS",
            "category": "другое",
            "description": "",
        }
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("покажи статистику")

        assert result is not None
        assert result[0]["type"] == "intent"
        assert result[0]["intent_action"] == "show_stats"

    async def test_multi_transaction_returns_list(self):
        """Несколько транзакций в одном сообщении — список из нескольких элементов."""
        payload = [
            {"type": "expense", "amount": 120000, "currency": "UZS",
             "category": "одежда", "description": "Одежда", "confidence": 0.90},
            {"type": "expense", "amount": 50000, "currency": "UZS",
             "category": "еда_питание", "description": "Обед", "confidence": 0.90},
            {"type": "expense", "amount": 200000, "currency": "UZS",
             "category": "транспорт", "description": "Бензин", "confidence": 0.93},
        ]
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("купил одежду 120к, обед 50к, бензин 200000")

        assert result is not None
        assert len(result) == 3
        assert result[0]["amount"] == 120000
        assert result[1]["category"] == "еда_питание"
        assert result[2]["amount"] == 200000

    async def test_invalid_json_returns_none(self):
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client("not valid json at all")):
            result = await parse_transaction("что-то непонятное")

        assert result is None

    async def test_api_exception_returns_none(self):
        client = MagicMock()
        client.messages.create.side_effect = Exception("API unavailable")
        with patch("bot.services.claude_parser.get_client", return_value=client):
            result = await parse_transaction("потратил 100к")

        assert result is None

    async def test_markdown_json_fences_stripped(self):
        """Ответ завёрнут в ```json ... ``` — должен корректно парситься."""
        payload = {
            "type": "expense",
            "amount": 200_000,
            "currency": "UZS",
            "category": "продукты",
            "description": "Korzinka",
        }
        wrapped = f"```json\n{json.dumps(payload)}\n```"
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(wrapped)):
            result = await parse_transaction("продукты в корзинке 200к")

        assert result is not None
        assert result[0]["type"] == "expense"

    async def test_expense_usd(self):
        payload = {
            "type": "expense",
            "amount": 50,
            "currency": "USD",
            "category": "подписки",
            "description": "ChatGPT",
        }
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("заплатил 50 долларов за ChatGPT")

        assert result[0]["currency"] == "USD"
        assert result[0]["amount"] == 50

    async def test_invalid_type_value_returns_none(self):
        payload = {"type": "transfer", "amount": 100000}
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_transaction("перевёл 100к другу")

        assert result is None


# ── parse_subscription_nlp ────────────────────────────────────────────────────

class TestParseSubscriptionNlp:
    async def test_valid_subscription(self):
        payload = {
            "name": "Netflix",
            "amount": 50,
            "currency": "USD",
            "billing_day": 15,
            "notes": None,
        }
        with patch("bot.services.claude_parser.get_client",
                   return_value=_make_client(json.dumps(payload))):
            result = await parse_subscription_nlp("Netflix 50 долларов каждый месяц 15 числа")

        assert result is not None
        assert result["name"] == "Netflix"
        assert result["currency"] == "USD"

    async def test_exception_returns_none(self):
        client = MagicMock()
        client.messages.create.side_effect = Exception("timeout")
        with patch("bot.services.claude_parser.get_client", return_value=client):
            result = await parse_subscription_nlp("какая-то подписка")

        assert result is None
