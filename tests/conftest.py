import asyncio
import os
import pytest
from unittest.mock import MagicMock

# Фиктивные env-переменные — предотвращают KeyError при импорте модулей
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("BOT_TOKEN", "0000000000:test-token")
os.environ.setdefault("OWNER_TG_ID", "36566562")


@pytest.fixture
def event_loop():
    """Отдельный event loop на каждый тест."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_chain():
    """
    Фабрика chainable-мока Supabase query builder.

    Использование:
        mock_db = db_chain(data=[{"role": "owner"}])
    """
    def _make(data=None):
        mock = MagicMock()
        result = MagicMock()
        result.data = data if data is not None else []

        for method in (
            "table", "select", "eq", "neq",
            "gte", "lte", "gt", "lt",
            "in_", "order", "limit",
            "update", "insert", "upsert", "delete",
        ):
            getattr(mock, method).return_value = mock

        mock.execute.return_value = result
        return mock

    return _make
