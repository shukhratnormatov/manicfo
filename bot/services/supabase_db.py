import os
import secrets
from datetime import date, datetime, timedelta
from typing import Optional
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


async def get_user_role(user_id: int) -> Optional[str]:
    db = get_client()
    result = db.table("access_control").select("role").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]["role"]
    return None


async def ensure_user(user_id: int, username: Optional[str]) -> None:
    db = get_client()
    existing = db.table("users").select("id").eq("id", user_id).execute()
    if not existing.data:
        db.table("users").insert({"id": user_id, "username": username}).execute()


async def add_beta_user(user_id: int, invited_by: int) -> None:
    db = get_client()
    db.table("access_control").upsert({
        "user_id": user_id,
        "role": "beta",
        "invited_by": invited_by,
    }).execute()


async def ban_user(user_id: int) -> None:
    db = get_client()
    db.table("access_control").update({"role": "banned"}).eq("user_id", user_id).execute()


async def get_user_by_username(username: str) -> Optional[dict]:
    db = get_client()
    clean = username.lstrip("@")
    result = db.table("users").select("id, username").eq("username", clean).execute()
    if result.data:
        return result.data[0]
    return None


async def get_all_beta_users() -> list:
    db = get_client()
    result = (
        db.table("access_control")
        .select("user_id, role, users(username)")
        .in_("role", ["beta", "owner"])
        .execute()
    )
    users = []
    for row in result.data:
        users.append({
            "user_id": row["user_id"],
            "role": row["role"],
            "username": (row.get("users") or {}).get("username"),
        })
    return users


async def add_transaction(
    user_id: int,
    type_: str,
    amount: float,
    currency: str,
    amount_uzs: float,
    category: str,
    description: str,
) -> dict:
    db = get_client()
    row = {
        "user_id": user_id,
        "type": type_,
        "amount": amount,
        "currency": currency,
        "amount_uzs": amount_uzs,
        "category": category,
        "description": description,
    }
    result = db.table("transactions").insert(row).execute()
    return result.data[0] if result.data else {}


async def get_monthly_stats(user_id: int, year: int, month: int) -> dict:
    db = get_client()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    result = (
        db.table("transactions")
        .select("type, amount_uzs, category")
        .eq("user_id", user_id)
        .gte("created_at", start)
        .lt("created_at", end)
        .execute()
    )
    rows = result.data or []
    income = sum(r["amount_uzs"] for r in rows if r["type"] == "income")
    expense = sum(r["amount_uzs"] for r in rows if r["type"] == "expense")

    by_category: dict = {}
    for r in rows:
        if r["type"] == "expense":
            by_category[r["category"]] = by_category.get(r["category"], 0) + r["amount_uzs"]

    return {"income": income, "expense": expense, "by_category": by_category}


async def get_weekly_stats(user_id: int) -> dict:
    from datetime import timedelta
    db = get_client()
    start = (date.today() - timedelta(days=7)).isoformat()
    result = (
        db.table("transactions")
        .select("type, amount_uzs, category, description, created_at")
        .eq("user_id", user_id)
        .gte("created_at", start)
        .execute()
    )
    rows = result.data or []
    income = sum(r["amount_uzs"] for r in rows if r["type"] == "income")
    expense = sum(r["amount_uzs"] for r in rows if r["type"] == "expense")
    by_category: dict = {}
    for r in rows:
        if r["type"] == "expense":
            by_category[r["category"]] = by_category.get(r["category"], 0) + r["amount_uzs"]
    return {"income": income, "expense": expense, "by_category": by_category}


async def get_recent_transactions(user_id: int, limit: int = 10) -> list:
    db = get_client()
    result = (
        db.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def get_category_month_total(user_id: int, category: str, year: int, month: int) -> float:
    db = get_client()
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month + 1:02d}-01" if month < 12 else f"{year + 1}-01-01"
    result = (
        db.table("transactions")
        .select("amount_uzs")
        .eq("user_id", user_id)
        .eq("category", category)
        .eq("type", "expense")
        .gte("created_at", start)
        .lt("created_at", end)
        .execute()
    )
    return sum(r["amount_uzs"] for r in (result.data or []))


async def get_budget_limit(user_id: int, category: str, month_date: str) -> Optional[float]:
    # Таблица budgets — заглушка до v2. Не бросать исключение если таблицы нет.
    try:
        db = get_client()
        result = (
            db.table("budgets")
            .select("limit_uzs")
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("month", month_date)
            .execute()
        )
        if result.data:
            return result.data[0]["limit_uzs"]
        return None
    except Exception:
        return None


async def update_transaction(transaction_id: str, user_id: int, **fields) -> bool:
    """Обновляет транзакцию. Проверяет что принадлежит user_id."""
    db = get_client()
    result = (
        db.table("transactions")
        .update(fields)
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .execute()
    )
    return len(result.data) > 0


async def delete_transaction(transaction_id: str, user_id: int) -> bool:
    """Удаляет транзакцию. Проверяет что принадлежит user_id."""
    db = get_client()
    result = (
        db.table("transactions")
        .delete()
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .execute()
    )
    return len(result.data) > 0


async def get_goals(user_id: int) -> list:
    db = get_client()
    result = (
        db.table("goals")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("priority")
        .execute()
    )
    return result.data or []


async def add_goal(
    user_id: int,
    name: str,
    target_amount: float,
    deadline: Optional[str],
    priority: int,
    currency: str = "UZS",
) -> dict:
    db = get_client()
    row = {
        "user_id": user_id,
        "name": name,
        "target_amount": target_amount,
        "saved_amount": 0,
        "currency": currency,
        "deadline": deadline,
        "priority": priority,
        "is_active": True,
    }
    result = db.table("goals").insert(row).execute()
    return result.data[0] if result.data else {}


async def update_goal_saved(goal_id: str, add_amount: float) -> dict:
    db = get_client()
    existing = db.table("goals").select("saved_amount").eq("id", goal_id).execute()
    if not existing.data:
        return {}
    current = existing.data[0]["saved_amount"] or 0
    new_amount = current + add_amount
    result = db.table("goals").update({"saved_amount": new_amount}).eq("id", goal_id).execute()
    return result.data[0] if result.data else {}


async def get_active_subscriptions(user_id: int) -> list:
    db = get_client()
    result = (
        db.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    return result.data or []


async def add_subscription(
    user_id: int,
    name: str,
    amount: float,
    currency: str,
    amount_uzs: float,
    billing_day: int,
    notes: Optional[str] = None,
) -> dict:
    db = get_client()
    row = {
        "user_id": user_id,
        "name": name,
        "amount": amount,
        "currency": currency,
        "amount_uzs": amount_uzs,
        "billing_day": billing_day,
        "notes": notes,
        "is_active": True,
    }
    result = db.table("subscriptions").insert(row).execute()
    return result.data[0] if result.data else {}


async def get_monthly_income_avg(user_id: int, months: int = 3) -> float:
    from datetime import timedelta
    db = get_client()
    start = (date.today().replace(day=1) - timedelta(days=months * 30)).isoformat()
    result = (
        db.table("transactions")
        .select("amount_uzs")
        .eq("user_id", user_id)
        .eq("type", "income")
        .gte("created_at", start)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return 0
    return sum(r["amount_uzs"] for r in rows) / max(months, 1)


async def create_invite_token(owner_id: int) -> str:
    """Создаёт одноразовый invite-токен, действующий 48 часов."""
    # Гарантируем что owner есть в users (FK constraint)
    await ensure_user(owner_id, None)
    db = get_client()
    token = "inv_" + secrets.token_urlsafe(8)
    expires = (datetime.utcnow() + timedelta(hours=48)).isoformat()
    db.table("invite_tokens").insert({
        "token": token,
        "created_by": owner_id,
        "expires_at": expires,
    }).execute()
    return token


async def use_invite_token(token: str, user_id: int) -> bool:
    """Проверяет токен и выдаёт доступ пользователю. Возвращает True если успешно."""
    db = get_client()
    now = datetime.utcnow().isoformat()
    result = (
        db.table("invite_tokens")
        .select("*")
        .eq("token", token)
        .eq("is_used", False)
        .gt("expires_at", now)
        .execute()
    )
    if not result.data:
        return False  # токен не найден, уже использован или истёк

    # Помечаем токен как использованный
    db.table("invite_tokens").update(
        {"is_used": True, "used_by": user_id}
    ).eq("token", token).execute()

    # Добавляем пользователя в access_control как beta
    invited_by = result.data[0]["created_by"]
    await add_beta_user(user_id, invited_by=invited_by)
    return True
