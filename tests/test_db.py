"""
Тесты методов supabase_db.py.
Supabase клиент полностью замокирован — реальных запросов к БД нет.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from bot.services.supabase_db import (
    get_user_role,
    ensure_user,
    add_beta_user,
    ban_user,
    get_user_by_username,
    add_transaction,
    get_monthly_stats,
    get_weekly_stats,
    get_recent_transactions,
    get_category_month_total,
    get_budget_limit,
    update_transaction,
    delete_transaction,
    update_subscription,
    delete_subscription,
    update_goal,
    delete_goal,
    find_goal_by_keyword,
    get_goals,
    set_monthly_budget,
    get_monthly_budget,
    delete_monthly_budget,
    get_total_expenses,
    get_all_active_users,
)

USER_ID = 123456789
MODULE = "bot.services.supabase_db.get_client"


# ── get_user_role ─────────────────────────────────────────────────────────────

class TestGetUserRole:
    async def test_returns_role_when_found(self, db_chain):
        mock_db = db_chain(data=[{"role": "owner"}])
        with patch(MODULE, return_value=mock_db):
            result = await get_user_role(USER_ID)
        assert result == "owner"

    async def test_returns_none_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_user_role(USER_ID)
        assert result is None

    async def test_returns_beta_role(self, db_chain):
        mock_db = db_chain(data=[{"role": "beta"}])
        with patch(MODULE, return_value=mock_db):
            result = await get_user_role(USER_ID)
        assert result == "beta"


# ── ensure_user ───────────────────────────────────────────────────────────────

class TestEnsureUser:
    async def test_no_insert_when_user_exists(self, db_chain):
        mock_db = db_chain(data=[{"id": USER_ID}])
        with patch(MODULE, return_value=mock_db):
            await ensure_user(USER_ID, "testuser")
        # insert должен НЕ вызываться
        mock_db.insert.assert_not_called()

    async def test_inserts_when_user_missing(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            await ensure_user(USER_ID, "newuser")
        mock_db.insert.assert_called_once()
        call_kwargs = mock_db.insert.call_args[0][0]
        assert call_kwargs["id"] == USER_ID
        assert call_kwargs["username"] == "newuser"


# ── add_beta_user ─────────────────────────────────────────────────────────────

class TestAddBetaUser:
    async def test_upserts_with_beta_role(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            await add_beta_user(USER_ID, invited_by=999)
        mock_db.upsert.assert_called_once()
        payload = mock_db.upsert.call_args[0][0]
        assert payload["user_id"] == USER_ID
        assert payload["role"] == "beta"
        assert payload["invited_by"] == 999


# ── ban_user ──────────────────────────────────────────────────────────────────

class TestBanUser:
    async def test_updates_role_to_banned(self, db_chain):
        mock_db = db_chain(data=[{"role": "banned"}])
        with patch(MODULE, return_value=mock_db):
            await ban_user(USER_ID)
        mock_db.update.assert_called_once_with({"role": "banned"})


# ── get_user_by_username ──────────────────────────────────────────────────────

class TestGetUserByUsername:
    async def test_found_with_at_sign(self, db_chain):
        mock_db = db_chain(data=[{"id": USER_ID, "username": "testuser"}])
        with patch(MODULE, return_value=mock_db):
            result = await get_user_by_username("@testuser")
        assert result["id"] == USER_ID
        assert result["username"] == "testuser"

    async def test_not_found_returns_none(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_user_by_username("nobody")
        assert result is None

    async def test_strips_at_prefix(self, db_chain):
        """@ в начале username должен обрезаться перед запросом."""
        mock_db = db_chain(data=[{"id": 1, "username": "alice"}])
        with patch(MODULE, return_value=mock_db):
            await get_user_by_username("@alice")
        # Проверяем что в eq передаётся "alice", а не "@alice"
        mock_db.eq.assert_any_call("username", "alice")


# ── add_transaction ───────────────────────────────────────────────────────────

class TestAddTransaction:
    async def test_returns_inserted_row(self, db_chain):
        row = {
            "id": "uuid-1",
            "user_id": USER_ID,
            "type": "expense",
            "amount": 50000,
            "currency": "UZS",
            "amount_uzs": 50000,
            "category": "транспорт",
            "description": "такси",
        }
        mock_db = db_chain(data=[row])
        with patch(MODULE, return_value=mock_db):
            result = await add_transaction(
                user_id=USER_ID,
                type_="expense",
                amount=50000,
                currency="UZS",
                amount_uzs=50000,
                category="транспорт",
                description="такси",
            )
        assert result["id"] == "uuid-1"
        assert result["type"] == "expense"

    async def test_returns_empty_dict_on_no_data(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await add_transaction(
                user_id=USER_ID, type_="income",
                amount=1000, currency="UZS", amount_uzs=1000,
                category="другое", description="",
            )
        assert result == {}


# ── get_monthly_stats ─────────────────────────────────────────────────────────

class TestGetMonthlyStats:
    async def test_correct_income_expense_split(self, db_chain):
        rows = [
            {"type": "income",  "amount_uzs": 3_000_000, "category": "зарплата"},
            {"type": "expense", "amount_uzs": 150_000,   "category": "продукты"},
            {"type": "expense", "amount_uzs": 50_000,    "category": "транспорт"},
        ]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            stats = await get_monthly_stats(USER_ID, 2026, 5)

        assert stats["income"] == 3_000_000
        assert stats["expense"] == 200_000

    async def test_by_category_aggregation(self, db_chain):
        rows = [
            {"type": "expense", "amount_uzs": 100_000, "category": "продукты"},
            {"type": "expense", "amount_uzs": 50_000,  "category": "продукты"},
            {"type": "expense", "amount_uzs": 70_000,  "category": "транспорт"},
        ]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            stats = await get_monthly_stats(USER_ID, 2026, 5)

        assert stats["by_category"]["продукты"] == 150_000
        assert stats["by_category"]["транспорт"] == 70_000

    async def test_empty_data_returns_zeros(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            stats = await get_monthly_stats(USER_ID, 2026, 5)

        assert stats["income"] == 0
        assert stats["expense"] == 0
        assert stats["by_category"] == {}

    async def test_december_end_date_wraps_year(self, db_chain):
        """Декабрь: end должен быть 2027-01-01, а не 2026-13-01."""
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            # Не должно бросать исключение
            stats = await get_monthly_stats(USER_ID, 2026, 12)
        assert stats["income"] == 0


# ── get_weekly_stats ──────────────────────────────────────────────────────────

class TestGetWeeklyStats:
    async def test_returns_income_and_expense(self, db_chain):
        rows = [
            {"type": "income",  "amount_uzs": 500_000, "category": "фриланс"},
            {"type": "expense", "amount_uzs": 80_000,  "category": "продукты"},
        ]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            stats = await get_weekly_stats(USER_ID)

        assert stats["income"] == 500_000
        assert stats["expense"] == 80_000


# ── get_recent_transactions ───────────────────────────────────────────────────

class TestGetRecentTransactions:
    async def test_returns_list(self, db_chain):
        rows = [{"id": "1", "amount_uzs": 10_000}, {"id": "2", "amount_uzs": 20_000}]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            result = await get_recent_transactions(USER_ID, limit=2)

        assert len(result) == 2
        assert result[0]["id"] == "1"

    async def test_empty_returns_empty_list(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_recent_transactions(USER_ID)
        assert result == []


# ── get_category_month_total ──────────────────────────────────────────────────

class TestGetCategoryMonthTotal:
    async def test_sums_correctly(self, db_chain):
        rows = [{"amount_uzs": 100_000}, {"amount_uzs": 50_000}]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            total = await get_category_month_total(USER_ID, "продукты", 2026, 5)
        assert total == 150_000

    async def test_empty_returns_zero(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            total = await get_category_month_total(USER_ID, "продукты", 2026, 5)
        assert total == 0


# ── get_budget_limit ──────────────────────────────────────────────────────────

class TestGetBudgetLimit:
    async def test_returns_limit_when_found(self, db_chain):
        mock_db = db_chain(data=[{"limit_uzs": 2_000_000}])
        with patch(MODULE, return_value=mock_db):
            result = await get_budget_limit(USER_ID, "продукты", "2026-05-01")
        assert result == 2_000_000

    async def test_returns_none_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_budget_limit(USER_ID, "продукты", "2026-05-01")
        assert result is None

    async def test_table_does_not_exist_returns_none(self):
        """Таблица budgets ещё не создана — любое исключение → None."""
        broken_client = MagicMock()
        broken_client.table.side_effect = Exception("relation 'budgets' does not exist")
        with patch(MODULE, return_value=broken_client):
            result = await get_budget_limit(USER_ID, "продукты", "2026-05-01")
        assert result is None

    async def test_any_db_exception_returns_none(self):
        """Любая ошибка БД обрабатывается gracefully."""
        broken_client = MagicMock()
        broken_client.table.return_value.select.side_effect = RuntimeError("network error")
        with patch(MODULE, return_value=broken_client):
            result = await get_budget_limit(USER_ID, "любая", "2026-05-01")
        assert result is None


# ── update_transaction ────────────────────────────────────────────────────────

class TestUpdateTransaction:
    async def test_returns_true_when_updated(self, db_chain):
        mock_db = db_chain(data=[{"id": "tx-1"}])
        with patch(MODULE, return_value=mock_db):
            result = await update_transaction("tx-1", USER_ID, description="новое")
        assert result is True

    async def test_returns_false_when_no_rows(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await update_transaction("tx-999", USER_ID, description="х")
        assert result is False


# ── delete_transaction ────────────────────────────────────────────────────────

class TestDeleteTransaction:
    async def test_returns_true_when_deleted(self, db_chain):
        mock_db = db_chain(data=[{"id": "tx-1"}])
        with patch(MODULE, return_value=mock_db):
            result = await delete_transaction("tx-1", USER_ID)
        assert result is True

    async def test_returns_false_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await delete_transaction("no-such-id", USER_ID)
        assert result is False


# ── update_subscription ───────────────────────────────────────────────────────

class TestUpdateSubscription:
    async def test_returns_true_when_updated(self, db_chain):
        mock_db = db_chain(data=[{"id": "sub-1"}])
        with patch(MODULE, return_value=mock_db):
            result = await update_subscription("sub-1", USER_ID, name="NewName")
        assert result is True

    async def test_returns_false_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await update_subscription("no-such", USER_ID, name="x")
        assert result is False


# ── delete_subscription ───────────────────────────────────────────────────────

class TestDeleteSubscription:
    async def test_soft_deletes_subscription(self, db_chain):
        mock_db = db_chain(data=[{"id": "sub-1", "is_active": False}])
        with patch(MODULE, return_value=mock_db):
            result = await delete_subscription("sub-1", USER_ID)
        assert result is True
        mock_db.update.assert_called_with({"is_active": False})

    async def test_returns_false_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await delete_subscription("no-such", USER_ID)
        assert result is False


# ── update_goal ───────────────────────────────────────────────────────────────

class TestUpdateGoal:
    async def test_returns_true_when_updated(self, db_chain):
        mock_db = db_chain(data=[{"id": "goal-1"}])
        with patch(MODULE, return_value=mock_db):
            result = await update_goal("goal-1", USER_ID, name="Отпуск")
        assert result is True

    async def test_returns_false_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await update_goal("no-such", USER_ID, name="x")
        assert result is False


# ── delete_goal ───────────────────────────────────────────────────────────────

class TestDeleteGoal:
    async def test_soft_deletes_goal(self, db_chain):
        mock_db = db_chain(data=[{"id": "goal-1", "is_active": False}])
        with patch(MODULE, return_value=mock_db):
            result = await delete_goal("goal-1", USER_ID)
        assert result is True
        mock_db.update.assert_called_with({"is_active": False})

    async def test_returns_false_when_not_found(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await delete_goal("no-such", USER_ID)
        assert result is False


# ── find_goal_by_keyword ──────────────────────────────────────────────────────

class TestFindGoalByKeyword:
    async def test_finds_goal_by_name_substring(self, db_chain):
        goals = [
            {"id": "g1", "name": "Машина", "target_amount": 50_000_000,
             "saved_amount": 0, "priority": 1, "is_active": True},
            {"id": "g2", "name": "Отпуск в Турции", "target_amount": 10_000_000,
             "saved_amount": 0, "priority": 2, "is_active": True},
        ]
        mock_db = db_chain(data=goals)
        with patch(MODULE, return_value=mock_db):
            result = await find_goal_by_keyword(USER_ID, "Турц")
        assert result is not None
        assert result["id"] == "g2"

    async def test_returns_first_goal_when_no_match(self, db_chain):
        goals = [
            {"id": "g1", "name": "Машина", "target_amount": 50_000_000,
             "saved_amount": 0, "priority": 1, "is_active": True},
        ]
        mock_db = db_chain(data=goals)
        with patch(MODULE, return_value=mock_db):
            result = await find_goal_by_keyword(USER_ID, "ремонт")
        assert result is not None
        assert result["id"] == "g1"

    async def test_returns_none_when_no_goals(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await find_goal_by_keyword(USER_ID, "что угодно")
        assert result is None


# ── set_monthly_budget / get_monthly_budget ───────────────────────────────────

class TestMonthlyBudget:
    async def test_set_inserts_when_no_existing_row(self, db_chain):
        """Если записи нет — делаем insert."""
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            await set_monthly_budget(USER_ID, 3_000_000)
        mock_db.insert.assert_called_once()
        payload = mock_db.insert.call_args[0][0]
        assert payload["user_id"] == USER_ID
        assert payload["amount_uzs"] == 3_000_000
        # update вызываться НЕ должен
        mock_db.update.assert_not_called()

    async def test_set_updates_when_existing_row(self, db_chain):
        """Если запись на этот месяц уже есть — делаем update."""
        mock_db = db_chain(data=[{"id": "existing-uuid"}])
        with patch(MODULE, return_value=mock_db):
            await set_monthly_budget(USER_ID, 10_000_000)
        mock_db.update.assert_called_once_with({"amount_uzs": 10_000_000})
        # insert вызываться НЕ должен
        mock_db.insert.assert_not_called()

    async def test_get_returns_value_when_found(self, db_chain):
        mock_db = db_chain(data=[{"amount_uzs": 5_000_000}])
        with patch(MODULE, return_value=mock_db):
            result = await get_monthly_budget(USER_ID)
        assert result == 5_000_000.0

    async def test_get_returns_none_when_not_set(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_monthly_budget(USER_ID)
        assert result is None

    async def test_get_returns_none_on_exception(self):
        broken = MagicMock()
        broken.table.side_effect = Exception("DB error")
        with patch(MODULE, return_value=broken):
            result = await get_monthly_budget(USER_ID)
        assert result is None


# ── get_total_expenses ────────────────────────────────────────────────────────

class TestGetTotalExpenses:
    async def test_sums_expense_rows(self, db_chain):
        rows = [{"amount_uzs": 200_000}, {"amount_uzs": 300_000}]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            total = await get_total_expenses(USER_ID, 2026, 5)
        assert total == 500_000

    async def test_empty_returns_zero(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            total = await get_total_expenses(USER_ID, 2026, 5)
        assert total == 0

    async def test_december_wraps_year_correctly(self, db_chain):
        """Декабрь: end = следующий год январь."""
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            # Не должно бросать исключение
            total = await get_total_expenses(USER_ID, 2026, 12)
        assert total == 0


# ── delete_monthly_budget ─────────────────────────────────────────────────────

class TestDeleteMonthlyBudget:
    async def test_returns_true_when_deleted(self, db_chain):
        mock_db = db_chain(data=[{"id": "budget-1"}])
        with patch(MODULE, return_value=mock_db):
            result = await delete_monthly_budget(USER_ID)
        assert result is True
        mock_db.delete.assert_called_once()

    async def test_returns_false_when_nothing_to_delete(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await delete_monthly_budget(USER_ID)
        assert result is False


# ── get_all_active_users ──────────────────────────────────────────────────────

class TestGetAllActiveUsers:
    async def test_returns_list_of_user_ids(self, db_chain):
        rows = [{"user_id": 111}, {"user_id": 222}, {"user_id": 333}]
        mock_db = db_chain(data=rows)
        with patch(MODULE, return_value=mock_db):
            result = await get_all_active_users()
        assert result == [111, 222, 333]

    async def test_empty_table_returns_empty_list(self, db_chain):
        mock_db = db_chain(data=[])
        with patch(MODULE, return_value=mock_db):
            result = await get_all_active_users()
        assert result == []

    async def test_queries_owner_and_beta_roles(self, db_chain):
        mock_db = db_chain(data=[{"user_id": 1}])
        with patch(MODULE, return_value=mock_db):
            await get_all_active_users()
        mock_db.in_.assert_called_once_with("role", ["owner", "beta"])

    async def test_single_user_returns_single_id(self, db_chain):
        mock_db = db_chain(data=[{"user_id": 999}])
        with patch(MODULE, return_value=mock_db):
            result = await get_all_active_users()
        assert len(result) == 1
        assert result[0] == 999
