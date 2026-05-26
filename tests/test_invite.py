"""
Тесты invite-системы: create_invite_token / use_invite_token.
Supabase и вспомогательные функции замокированы.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call

from bot.services.supabase_db import create_invite_token, use_invite_token

OWNER_ID = 36566562
INVITEE_ID = 55555555
TOKEN = "inv_abc12345"
MODULE_GET_CLIENT = "bot.services.supabase_db.get_client"
MODULE_ENSURE_USER = "bot.services.supabase_db.ensure_user"
MODULE_ADD_BETA = "bot.services.supabase_db.add_beta_user"


# ── create_invite_token ───────────────────────────────────────────────────────

class TestCreateInviteToken:
    async def test_returns_inv_prefixed_token(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock):
            token = await create_invite_token(OWNER_ID)

        assert token.startswith("inv_")

    async def test_token_is_unique_each_call(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock):
            t1 = await create_invite_token(OWNER_ID)
            t2 = await create_invite_token(OWNER_ID)

        assert t1 != t2

    async def test_calls_ensure_user_first(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock) as mock_ensure:
            await create_invite_token(OWNER_ID)

        mock_ensure.assert_called_once_with(OWNER_ID, None)

    async def test_inserts_into_invite_tokens_table(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock):
            await create_invite_token(OWNER_ID)

        # Проверяем что был вызов insert с нужными полями
        mock_db.insert.assert_called_once()
        payload = mock_db.insert.call_args[0][0]
        assert payload["created_by"] == OWNER_ID
        assert "token" in payload
        assert "expires_at" in payload

    async def test_token_starts_with_inv_prefix_exactly(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock):
            token = await create_invite_token(OWNER_ID)

        # Убеждаемся что это "inv_" + что-то, а не просто "inv"
        parts = token.split("_", 1)
        assert parts[0] == "inv"
        assert len(parts[1]) > 0

    async def test_inserted_token_matches_returned_token(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ENSURE_USER, new_callable=AsyncMock):
            returned_token = await create_invite_token(OWNER_ID)

        inserted_payload = mock_db.insert.call_args[0][0]
        assert inserted_payload["token"] == returned_token


# ── use_invite_token ──────────────────────────────────────────────────────────

class TestUseInviteToken:
    def _make_db_for_valid_token(self):
        """
        Мок БД с двумя execute()-вызовами:
        1. SELECT invite_tokens → нашли токен
        2. UPDATE invite_tokens → помечаем использованным
        """
        mock_db = MagicMock()
        for method in ("table", "select", "eq", "neq", "gte", "lte",
                       "gt", "lt", "in_", "order", "limit",
                       "update", "insert", "upsert", "delete"):
            getattr(mock_db, method).return_value = mock_db

        select_result = MagicMock()
        select_result.data = [{
            "token": TOKEN,
            "created_by": OWNER_ID,
            "is_used": False,
        }]
        update_result = MagicMock()
        update_result.data = [{"token": TOKEN}]

        mock_db.execute.side_effect = [select_result, update_result]
        return mock_db

    async def test_valid_token_returns_true(self):
        mock_db = self._make_db_for_valid_token()
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock):
            result = await use_invite_token(TOKEN, INVITEE_ID)

        assert result is True

    async def test_valid_token_calls_add_beta_user(self):
        mock_db = self._make_db_for_valid_token()
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock) as mock_add_beta:
            await use_invite_token(TOKEN, INVITEE_ID)

        mock_add_beta.assert_called_once_with(INVITEE_ID, invited_by=OWNER_ID)

    async def test_valid_token_passes_correct_invited_by(self):
        """invited_by должен браться из токена (created_by), а не из вызова."""
        mock_db = self._make_db_for_valid_token()
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock) as mock_add_beta:
            await use_invite_token(TOKEN, INVITEE_ID)

        _, kwargs = mock_add_beta.call_args
        assert kwargs["invited_by"] == OWNER_ID

    async def test_token_not_found_returns_false(self, db_chain):
        mock_db = db_chain(data=[])  # пустой результат SELECT
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock) as mock_add_beta:
            result = await use_invite_token("inv_invalid", INVITEE_ID)

        assert result is False
        mock_add_beta.assert_not_called()

    async def test_expired_or_used_token_returns_false(self, db_chain):
        """SELECT с фильтром is_used=False и gt(expires_at) вернул пусто → False."""
        mock_db = db_chain(data=[])
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock):
            result = await use_invite_token(TOKEN, INVITEE_ID)

        assert result is False

    async def test_marks_token_as_used(self):
        mock_db = self._make_db_for_valid_token()
        with patch(MODULE_GET_CLIENT, return_value=mock_db), \
             patch(MODULE_ADD_BETA, new_callable=AsyncMock):
            await use_invite_token(TOKEN, INVITEE_ID)

        # Проверяем что update был вызван с {"is_used": True, "used_by": ...}
        mock_db.update.assert_called()
        update_payload = mock_db.update.call_args[0][0]
        assert update_payload["is_used"] is True
        assert update_payload["used_by"] == INVITEE_ID
