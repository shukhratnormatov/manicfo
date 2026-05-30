# maniCFO — Журнал выполненных работ

> Документ для составления ТЗ на следующие итерации разработки.
> Актуален на **30.05.2026**, ветка `feat/ux-v1.2-pr`.

---

## Оглавление

1. [Технический стек](#технический-стек)
2. [Схема базы данных](#схема-базы-данных)
3. [Архитектура бота](#архитектура-бота)
4. [История релизов](#история-релизов)
   - [v1.0 — MVP](#v10--mvp)
   - [v1.2 — UX и доступ](#v12--ux-и-доступ)
   - [v1.3 — Бюджет, интенты, редактирование](#v13--бюджет-интенты-редактирование)
   - [v1.4 — Мульти-транзакции и уведомления](#v14--мульти-транзакции-и-уведомления)
5. [Тестовое покрытие](#тестовое-покрытие)
6. [Технический долг](#технический-долг)
7. [Идеи для следующих версий (бэклог)](#идеи-для-следующих-версий-бэклог)

---

## Технический стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.11 |
| Bot framework | aiogram 3.4.1 |
| База данных | Supabase (PostgreSQL) |
| NLP | Claude API — claude-sonnet-4-5 |
| Курсы валют | cbu.uz (httpx) |
| Планировщик | APScheduler 3.10.4 |
| Деплой | Railway |
| Package manager | uv |
| Тесты | pytest + pytest-asyncio (asyncio_mode=auto) |

---

## Схема базы данных

### `users`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | bigint | Telegram user_id (PK) |
| `username` | text | @username без @ |

### `access_control`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | bigint | FK → users.id |
| `role` | text | `owner` / `beta` / `banned` |
| `invited_by` | bigint | user_id того, кто пригласил |

### `transactions`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | uuid | PK |
| `user_id` | bigint | FK → users.id |
| `type` | text | `expense` / `income` |
| `amount` | numeric | Сумма в оригинальной валюте |
| `currency` | text | `UZS` / `USD` / `RUB` |
| `amount_uzs` | numeric | Сумма в сумах (для статистики) |
| `category` | text | Категория расхода/дохода |
| `description` | text | Краткое описание |
| `created_at` | timestamptz | Дата создания |

### `goals`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | uuid | PK |
| `user_id` | bigint | FK → users.id |
| `name` | text | Название цели |
| `target_amount` | numeric | Целевая сумма |
| `saved_amount` | numeric | Накоплено на данный момент |
| `currency` | text | Валюта цели |
| `deadline` | date | Дедлайн (опционально) |
| `priority` | int | Приоритет (для сортировки) |
| `is_active` | bool | Soft delete |

### `subscriptions`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | uuid | PK |
| `user_id` | bigint | FK → users.id |
| `name` | text | Название сервиса |
| `amount` | numeric | Сумма |
| `currency` | text | Валюта |
| `amount_uzs` | numeric | В сумах |
| `billing_day` | int | День списания (1–31) |
| `notes` | text | Заметка |
| `is_active` | bool | Soft delete |

### `monthly_budget`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | uuid | PK |
| `user_id` | bigint | FK → users.id |
| `amount_uzs` | numeric | Лимит бюджета в сумах |
| `month` | date | Первый день месяца (YYYY-MM-01) |
| `created_at` | timestamptz | |

> ⚠️ Нет `UNIQUE(user_id, month)` — обновление через `select → update/insert`.

### `invite_tokens`
| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | uuid | PK |
| `token` | text | `inv_` + случайные символы |
| `created_by` | bigint | user_id owner |
| `expires_at` | timestamptz | Срок действия (48 ч) |
| `is_used` | bool | Флаг использования |
| `used_by` | bigint | user_id того, кто использовал |

---

## Архитектура бота

```
bot/
  main.py                  — точка входа, роутеры, middleware, планировщик
  states.py                — все FSM StatesGroup
  handlers/
    start.py               — /start, онбординг
    transactions.py        — NLP-ввод, интент-диспетчер, _process_single_tx
    stats.py               — /stats, /week, /history
    goals.py               — /goals, /add_goal, /save
    subscriptions.py       — /subs, /add_sub
    rates.py               — /rates
    budget.py              — /budget, FSM установки лимита
    edit.py                — FSM редактирования транзакций, подписок, целей
    admin.py               — /genlink, /invite_id, /invite, /ban, /users
  keyboards/
    reply.py               — MENU_BUTTONS frozenset + главное меню
    inline.py              — все InlineKeyboardMarkup фабрики
  services/
    supabase_db.py         — все методы работы с БД
    claude_parser.py       — парсинг текста через Claude API → list[dict]
    currency.py            — курсы валют cbu.uz с кэшем на день
    scheduler.py           — APScheduler, ежедневные уведомления 10:00 UZT
  utils/
    formatters.py          — format_sum, format_amount_display, progress_bar
    constants.py           — PARSE_SYSTEM_PROMPT, категории
  middlewares/
    auth.py                — AccessMiddleware (проверка роли + OWNER bypass)
  filters/
    role.py                — RoleFilter (не используется напрямую)
scripts/
  test_reminder.py         — ручной запуск send_daily_reminders (mock DB)
tests/
  conftest.py              — фикстуры event_loop, db_chain
  test_db.py               — тесты всех методов supabase_db.py
  test_parser.py           — тесты claude_parser.py
  test_formatters.py       — тесты formatters.py
  test_currency.py         — тесты currency.py
  test_invite.py           — тесты invite-токенов
```

### Порядок роутеров (критично)
```python
dp.include_router(admin.router)
dp.include_router(start.router)
dp.include_router(edit.router)       # FSM редактирования — до transactions
dp.include_router(budget.router)     # кнопка "💰 Бюджет" — до transactions
dp.include_router(goals.router)
dp.include_router(stats.router)
dp.include_router(rates.router)
dp.include_router(subscriptions.router)
dp.include_router(transactions.router)  # catch-all — последним
```

### NLP-парсер: формат ответа
Claude возвращает **JSON-массив** (даже для одной транзакции):
```json
[
  {
    "type": "expense | income | unknown | intent",
    "amount": 50000,
    "currency": "UZS | USD | RUB",
    "category": "продукты",
    "description": "Korzinka",
    "intent_action": "show_stats | show_goals | show_history | ...",
    "confidence": 0.95
  }
]
```

---

## История релизов

---

### v1.0 — MVP

**Дата:** первоначальный релиз

**Функционал:**
- Ввод расходов и доходов свободным текстом через Claude API
- Статистика за месяц (`/stats`) и неделю (`/week`)
- История транзакций (`/history`)
- Цели накопления (`/goals`, `/add_goal`, `/save`)
- Подписки (`/subs`, `/add_sub`)
- Курсы валют USD/RUB к UZS через cbu.uz (`/rates`)
- Поддержка USD, RUB (конвертация в UZS для статистики)
- Онбординг при первом запуске (`/start`)
- Система доступа: `owner`, `beta`, `banned`
- Инвайт-система: `/genlink` генерирует одноразовую ссылку на 48 ч
- Команды владельца: `/invite_id`, `/invite`, `/ban`, `/users`

---

### v1.2 — UX и доступ

**Ключевые изменения:**

| # | Что сделано |
|---|-------------|
| FIX-1 | **FSM escape**: любая кнопка главного меню из любого FSM-состояния сбрасывает его и открывает нужный раздел. `MENU_BUTTONS` frozenset — единственный источник истины |
| FIX-2 | **`/genlink` не реагировал**: заменён `RoleFilter` на inline-проверку `user_role` + fallback `_is_owner(message)` |
| FIX-3 | **OWNER_TG_ID bypass**: middleware проверяет env-переменную до запроса к БД — гарантированная роль `owner` без DB lookup |
| TEST | Создан полный pytest-suite: **93 теста**, 5 файлов, нулевые реальные запросы. Фикстура `db_chain` для мока цепочки Supabase |

---

### v1.3 — Бюджет, интенты, редактирование

**Дата:** 26.05.2026 + хотфиксы 30.05.2026

#### Новые функции

| Фича | Описание |
|------|----------|
| **FEAT-1: Месячный бюджет** | `/budget` — установка, просмотр, изменение, удаление месячного лимита. После каждого расхода бот показывает остаток/превышение. Новая таблица `monthly_budget` |
| **FEAT-2: Интент-детекция** | Пользователь пишет «покажи статистику» — бот понимает и показывает. 7 интентов: `show_stats`, `show_goals`, `show_history`, `show_subs`, `show_rates`, `show_week`, `show_budget` |

#### Исправления

| # | Баг | Решение |
|---|-----|---------|
| BUG-1 | Дата не показывалась в курсах валют | `get_rates_text()` добавляет `DD.MM.YYYY` |
| BUG-2 | Иностранные валюты отображались только в UZS | `format_amount_display()`: показывает `500 $ (6 350 000 сум)` |
| BUG-3 | Бот сохранял транзакции с нулевой суммой | Проверка `amount <= 0` в `handle_free_text` и парсере |
| BUG-4 | Нельзя редактировать/удалять подписки и цели | FSM-флоу в `edit.py`, кнопки `sub_item_kb` / `goal_item_kb` |
| BUG-5 | Накопления записывались как расход | При `category="накопления"` — пополняет цель, не пишет расход |
| BUG-6 | Сумма цели принимала отрицательные значения | Валидация `amount <= 0` в FSM цели с повтором запроса |

#### Хотфиксы (после деплоя на Railway)

| # | Проблема | Решение |
|---|---------|---------|
| HOT-1 | Колонка `budget_uzs` не найдена (PGRST204) | Переименовано в `amount_uzs` (реальное имя в Supabase) |
| HOT-2 | «Изменить бюджет» создавал дубли строк | `upsert()` без `UNIQUE` → явный `select → update/insert` |

#### Новые методы БД
`set_monthly_budget`, `get_monthly_budget`, `get_total_expenses`, `delete_monthly_budget`, `update_subscription`, `delete_subscription`, `update_goal`, `delete_goal`, `find_goal_by_keyword`

#### Тесты: 93 → **112** (+19 в test_db.py, +1 в test_parser.py)

---

### v1.4 — Мульти-транзакции и уведомления

**Дата:** 30.05.2026

#### Новые функции

| Фича | Описание |
|------|----------|
| **FEAT-3: Мульти-транзакции** | Несколько транзакций одним сообщением: `"купил одежду 120к, обед 50к, бензин за 200000"` — бот создаёт 3 записи с отдельными подтверждениями. Разделители: запятая, перенос строки, естественный текст |
| **FEAT-4: Ежедневные уведомления** | APScheduler отправляет напоминание всем активным пользователям каждый день в **10:00 по Ташкенту (05:00 UTC)**. Текст: напомнить записать расходы за день |

#### UX-улучшения

| # | Что изменилось |
|---|----------------|
| UX-1 | **Кнопка «🏠 Меню» в истории** — теперь отображается только под последней транзакцией, а не под каждой |

#### Технические изменения

| Файл | Изменение |
|------|-----------|
| `PARSE_SYSTEM_PROMPT` | Всегда возвращает JSON-массив `[{...}]`; добавлены 2 multi-tx примера |
| `claude_parser.py` | `parse_transaction` → `list[dict]`; `max_tokens` 256 → 1024; обратная совместимость с dict-ответом |
| `transactions.py` | Логика транзакции вынесена в `_process_single_tx()`; `handle_free_text` итерируется по списку |
| `inline.py` | `history_item_kb(tx_id, show_menu=True)` — новый параметр |
| `scheduler.py` | Новый файл: `AsyncIOScheduler`, `send_daily_reminders`, `setup_scheduler` |
| `supabase_db.py` | `get_all_active_users()` — список user_id для owner + beta |
| `main.py` | Планировщик стартует при запуске бота, останавливается при выключении |
| `requirements.txt` | `APScheduler==3.10.4`, `pytz==2024.1` |
| `CLAUDE.md` | Новый файл — контекст проекта для AI-сессий |

#### Тесты: 116 → **120** (+4 в test_db.py, +1 в test_parser.py)

---

## Тестовое покрытие

| Файл | Тестов | Покрытие |
|------|--------|----------|
| `test_db.py` | 53 | Все методы `supabase_db.py` |
| `test_parser.py` | 12 | `parse_transaction`, `parse_subscription_nlp`, multi-tx |
| `test_formatters.py` | 31 | `format_sum`, `progress_bar`, `format_percent`, `months_to_human` |
| `test_currency.py` | 12 | `fetch_rates`, `to_uzs`, `get_rates_text` |
| `test_invite.py` | 12 | `create_invite_token`, `use_invite_token` |
| **Итого** | **120** | **0 реальных API-запросов** |

Запуск: `~/.local/bin/uv run pytest`

---

## Технический долг

| Приоритет | Проблема | Решение |
|-----------|---------|---------|
| 🔴 Высокий | `datetime.utcnow()` deprecated в Python 3.12+ | Заменить на `datetime.now(timezone.utc)` в `create_invite_token` и `use_invite_token` |
| 🟡 Средний | `monthly_budget` без `UNIQUE(user_id, month)` | Добавить constraint в Supabase → использовать `upsert` вместо `select→update/insert` |
| 🟡 Средний | Возможны дубли в `monthly_budget` из-за старого бага | SQL-очистка: `DELETE FROM monthly_budget WHERE id NOT IN (SELECT MAX(id) FROM monthly_budget GROUP BY user_id, month)` |
| 🟡 Средний | `data.env.md` с реальными токенами лежит в репо | Удалить файл, добавить в `.gitignore` |
| 🟢 Низкий | Нет `pyproject.toml` / `uv.lock` | Перейти с `requirements.txt` на `uv` проект для воспроизводимых сборок |
| 🟢 Низкий | Логи планировщика не попадают в Railway | Настроить `structlog` или форматтер для Railway |

---

## Идеи для следующих версий (бэклог)

### 🔴 Высокий приоритет

#### v1.5 — Категорийные лимиты
- Установка бюджета не только на месяц, но и по категориям (еда, транспорт и т.д.)
- Таблица `budgets (id, user_id, category, limit_uzs, month)` уже заготовлена в `get_budget_limit()`
- При каждом расходе показывать остаток по категории

#### v1.5 — Отмена последней транзакции
- Кнопка ↩️ «Отменить» уже реализована через `cancel_tx_kb` и `_pending_cancel`
- Проблема: кнопка исчезает через 60 сек (таймер) — иногда не успевают
- Улучшение: сохранять последние N транзакций пользователя в FSM-памяти

---

### 🟡 Средний приоритет

#### v1.6 — Экспорт в Excel / CSV
- Команда `/export` — выгрузка транзакций за месяц/квартал
- Фильтры: период, категория, тип
- Формат: `.xlsx` с диаграммами по категориям

#### v1.6 — Напоминания о подписках
- За 3 дня до `billing_day` бот предупреждает: «Через 3 дня спишется Netflix 50$»
- Расширение планировщика: ежедневная проверка `subscriptions` для каждого пользователя

#### v1.6 — Детальная история с пагинацией
- Текущий `/history` показывает только 10 последних
- Кнопка «ещё 10» / inline-пагинация по страницам
- Фильтр по категории и типу (доходы / расходы)

#### v1.6 — Регулярные транзакции (шаблоны)
- Пользователь может сохранить шаблон: «ипотека 1.2 млн каждый месяц 5 числа»
- Планировщик создаёт транзакцию автоматически

---

### 🟢 Низкий приоритет

#### v1.7 — Аналитика и графики
- Сравнение расходов по месяцам (текущий vs прошлый)
- Топ-3 категорий за месяц
- Прогноз: «при текущем темпе бюджет закончится через X дней»
- Отправка изображений с matplotlib / quickchart.io

#### v1.7 — Семейный доступ
- Несколько пользователей в одном «пространстве» (семья, бизнес)
- Общий бюджет, общая статистика
- Роли: owner, member (может добавлять), viewer (только смотреть)

#### v1.7 — Мультивалютная статистика
- Сейчас всё конвертируется в UZS для агрегации
- Показывать статистику в исходных валютах (если пользователь работает в $)
- Курс на дату транзакции (сейчас берётся текущий)

#### v1.8 — Веб-интерфейс (dashboard)
- Supabase уже как бэкенд
- React/Next.js дашборд с графиками
- Аутентификация через Telegram Login Widget

#### v1.8 — Голосовые сообщения
- Транскрипция через Whisper API
- Передача текста в существующий NLP-парсер
- «Сказал — записалось»

---

## Команды и сценарии использования

### Пользовательские команды

| Команда / ввод | Действие |
|----------------|---------|
| Свободный текст | NLP-парсинг → запись транзакции |
| `"купил X, Y, Z"` | Несколько транзакций одним сообщением |
| `"покажи статистику"` | Интент → открывает `/stats` |
| `/stats` | Статистика за текущий месяц |
| `/week` | Итоги за 7 дней |
| `/history` | Последние 10 транзакций с ✏️/🗑 |
| `/goals` | Список целей с прогрессом |
| `/add_goal` | FSM создания новой цели |
| `/save` | Пополнение цели |
| `/subs` | Список подписок с ✏️/🗑 |
| `/add_sub` | FSM добавления подписки |
| `/rates` | Курсы USD/RUB к UZS |
| `/budget` | Месячный бюджет: статус, установка, удаление |

### Команды владельца

| Команда | Действие |
|---------|---------|
| `/genlink` | Генерирует одноразовую инвайт-ссылку (48 ч) |
| `/invite_id 123456789` | Добавить пользователя по Telegram ID |
| `/invite @username` | Добавить по username |
| `/ban @username` | Заблокировать пользователя |
| `/users` | Список всех бета-тестеров |

### Автоматические события

| Событие | Триггер |
|---------|---------|
| Ежедневное напоминание | Каждый день 10:00 Ташкент (05:00 UTC) |
| _(запланировано)_ Напоминание о подписке | За 3 дня до `billing_day` |

---

## Конфигурация Railway (env переменные)

| Переменная | Описание |
|------------|---------|
| `BOT_TOKEN` | Токен от @BotFather |
| `ANTHROPIC_API_KEY` | Ключ Anthropic API |
| `SUPABASE_URL` | URL Supabase проекта |
| `SUPABASE_KEY` | Anon/public key Supabase |
| `OWNER_TG_ID` | Telegram ID владельца (числом) |
| `BASE_CURRENCY` | `UZS` (по умолчанию) |
