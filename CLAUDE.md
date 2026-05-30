# CLAUDE.md — maniCFO

Контекст проекта для AI-ассистента. Читай перед тем как что-то менять.

---

## Что это

Telegram-бот личного финансового учёта для пользователей из Узбекистана/СНГ.
Парсит свободный текст (через Claude API), записывает доходы/расходы в Supabase,
показывает статистику, управляет целями накопления и подписками.

Деплой: **Railway**, ветка `feat/ux-v1.2-pr`.
БД: **Supabase** (PostgreSQL).

---

## Стек

| Компонент | Версия/инструмент |
|-----------|-------------------|
| Python | 3.11 |
| Bot framework | aiogram 3.4.1 |
| Database | Supabase Python client |
| NLP | Claude API (Anthropic) |
| Курсы валют | cbu.uz (httpx) |
| Package manager | `uv` (`~/.local/bin/uv`) |
| Тесты | pytest + pytest-asyncio (`asyncio_mode=auto`) |

---

## Структура

```
bot/
  main.py                  — точка входа, регистрация роутеров и middleware
  states.py                — все FSM StatesGroup в одном месте
  handlers/
    start.py               — /start, онбординг
    transactions.py        — свободный текст (NLP), "💰 Бюджет" кнопка, интент-диспетчер
    stats.py               — /stats, /week
    goals.py               — /goals, /add_goal, /save
    subscriptions.py       — /subs, /add_sub
    rates.py               — /rates
    budget.py              — /budget, FSM установки лимита, callback budget:set/delete
    edit.py                — FSM редактирования/удаления транзакций, подписок, целей
    admin.py               — /genlink, /invite_id, /invite, /ban, /users (owner only)
  keyboards/
    reply.py               — главное меню (MENU_BUTTONS frozenset)
    inline.py              — все InlineKeyboardMarkup фабрики
  services/
    supabase_db.py         — все обращения к БД (без бизнес-логики)
    claude_parser.py       — парсинг свободного текста через Claude API
    currency.py            — курсы валют cbu.uz
  utils/
    formatters.py          — format_sum, format_amount_display, progress_bar, format_percent
    constants.py           — PARSE_SYSTEM_PROMPT и прочие константы
  middlewares/             — AccessMiddleware (проверка роли)
  filters/                 — RoleFilter (не используется напрямую, owner через env)
tests/
  conftest.py              — фикстуры event_loop, db_chain
  test_db.py               — 49 тестов БД (все методы supabase_db.py)
  test_parser.py           — 11 тестов парсера
  test_formatters.py       — тесты форматтеров
  test_currency.py         — тесты курсов валют
  test_invite.py           — тесты инвайт-токенов
```

---

## Критические правила

### 1. Не переписывать — только точечные изменения
Принцип «хирургических правок». Никаких рефакторингов, не связанных с задачей.

### 2. Порядок роутеров в main.py важен
```python
dp.include_router(budget.router)      # до transactions!
dp.include_router(transactions.router)
```
Иначе "💰 Бюджет" захватывает `handle_free_text`.

### 3. Supabase upsert без UNIQUE constraint = всегда INSERT
В таблице `monthly_budget` нет `UNIQUE(user_id, month)`. Если делать `upsert()` без `id`
в payload — каждый раз создаётся новая строка. Используй явный паттерн:
```python
existing = db.table(...).select("id").eq(...).execute()
if existing.data:
    db.table(...).update({...}).eq(...).execute()
else:
    db.table(...).insert({...}).execute()
```

### 4. FSM escape через MENU_BUTTONS
Все FSM-обработчики имеют фильтр `~F.text.in_(MENU_BUTTONS)`.
`MENU_BUTTONS` — frozenset в `bot/keyboards/reply.py` — единственный источник истины.
При добавлении новой кнопки меню — добавить туда же.

### 5. Тесты — без реальных API вызовов
Все тесты мокируют Supabase client и Claude API через `unittest.mock`.
Фикстура `db_chain` в `conftest.py` имитирует цепочку `table().select().eq().execute()`.

---

## Запуск тестов

```bash
~/.local/bin/uv run pytest          # все тесты
~/.local/bin/uv run pytest tests/test_db.py -v   # конкретный файл
```

**Текущий результат: 115 passed, 0 failed** (по состоянию на 30.05.2026)

---

## Схема БД (Supabase)

| Таблица | Ключевые колонки |
|---------|-----------------|
| `users` | `id` (tg_id), `username` |
| `access_control` | `user_id`, `role` (beta/owner/banned), `invited_by` |
| `transactions` | `id`, `user_id`, `type`, `amount`, `currency`, `amount_uzs`, `category`, `description`, `created_at` |
| `goals` | `id`, `user_id`, `name`, `target_amount`, `saved_amount`, `currency`, `deadline`, `priority`, `is_active` |
| `subscriptions` | `id`, `user_id`, `name`, `amount`, `currency`, `amount_uzs`, `billing_day`, `notes`, `is_active` |
| `monthly_budget` | `id`, `user_id`, `amount_uzs`, `month` (date, первый день месяца), `created_at` |
| `invite_tokens` | `id`, `token`, `created_by`, `expires_at`, `is_used`, `used_by` |

**Важно:** `monthly_budget.amount_uzs` — не `budget_uzs`. Колонка называется именно так.

---

## NLP / Парсер

`PARSE_SYSTEM_PROMPT` в `bot/utils/constants.py` инструктирует Claude возвращать JSON:

```json
{"type": "expense|income|unknown|intent", "amount": float, "currency": "UZS|USD|RUB|EUR",
 "amount_uzs": float, "category": "...", "description": "...", "intent_action": "..."}
```

Поддерживаемые интенты (`type="intent"`):
`show_stats`, `show_goals`, `show_history`, `show_subs`, `show_rates`, `show_week`, `show_budget`

`handle_free_text` в `transactions.py` диспетчеризует интенты в соответствующие handler-функции.
`type="unknown"` → бот просит уточнить сумму или тип операции.

---

## Soft delete

Подписки и цели **не удаляются физически**. Флаг `is_active=False`.
Все выборки фильтруют `.eq("is_active", True)`.

---

## Что было сделано — 30.05.2026 (v1.3)

### Новые функции

**FEAT-1 — Месячный бюджет**
- Новый обработчик `/budget` (`bot/handlers/budget.py`)
- Кнопка «💰 Бюджет» в главном меню
- FSM-флоу: установка → подтверждение → изменение → удаление
- После каждого расхода в чате появляется строка остатка/превышения бюджета
- Новые методы БД: `set_monthly_budget`, `get_monthly_budget`, `get_total_expenses`, `delete_monthly_budget`

**FEAT-2 — Интент-детекция**
- Пользователь может написать «покажи статистику» — бот поймёт и покажет
- 7 интентов: stats, goals, history, subs, rates, week, budget
- Claude возвращает `type="intent"` + `intent_action` поле

### Исправления

**BUG-1** — Дата в курсах валют (`get_rates_text()` теперь показывает дату)

**BUG-2** — Форматирование валюты: `format_amount_display()` показывает `500 $ (6 350 000 сум)` для иностранных валют

**BUG-3** — Защита от нулевых сумм: `amount=0` при неясной сумме → запрос уточнения

**BUG-4** — Редактирование и удаление подписок и целей (FSM-флоу + `sub_item_kb`, `goal_item_kb`)

**BUG-5** — Автозачисление в цель при категории «накопления» (не пишет как расход, а пополняет цель)

**BUG-6** — Валидация суммы в FSM целей (`amount <= 0` → повтор без выхода из FSM)

### Хотфиксы после деплоя

- `budget_uzs` → `amount_uzs` (реальное имя колонки в Supabase)
- `upsert()` без `UNIQUE constraint` → заменено на `select → update/insert` (иначе дубли)

### Новые файлы

- `bot/handlers/budget.py`
- `CHANGELOG.md`

---

## Текущий статус (30.05.2026)

| Параметр | Значение |
|----------|----------|
| Версия | v1.3 |
| Ветка | `feat/ux-v1.2-pr` |
| Последний коммит | `92057ec` — fix: budget duplicate row + delete |
| Тесты | **115 passed, 0 failed** |
| Деплой | Railway (активен) |
| Бюджет-фича | Работает после двух хотфиксов |

### Известные технические долги

- `datetime.utcnow()` в `create_invite_token` / `use_invite_token` — deprecated в Python 3.12+, нужно заменить на `datetime.now(timezone.utc)`
- В таблице `monthly_budget` стоит добавить `UNIQUE(user_id, month)` в Supabase — тогда можно будет использовать `upsert()` вместо select→update/insert
- Возможны дублирующие строки в `monthly_budget` из-за бага, работавшего до хотфикса — при необходимости почистить SQL: `DELETE FROM monthly_budget WHERE id NOT IN (SELECT MAX(id) FROM monthly_budget GROUP BY user_id, month)`
