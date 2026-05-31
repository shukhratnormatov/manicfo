# Changelog — maniCFO

## v1.3 — 26.05.2026

### Новые функции

#### 💰 Месячный бюджет (FEAT-1)
- Новый обработчик `/budget` и кнопка **💰 Бюджет** в главном меню
- FSM-флоу для установки лимита: `/budget` → «Установить бюджет» → ввод суммы
- После каждого расхода в подтверждении появляется строка остатка/превышения бюджета
- Новые методы БД: `set_monthly_budget`, `get_monthly_budget`, `get_total_expenses`
- Таблица Supabase: `monthly_budget (id, user_id, amount_uzs, month, created_at)`

#### 🧠 Интент-детекция (FEAT-2)
- `PARSE_SYSTEM_PROMPT` расширен: новый тип `"intent"` с полем `intent_action`
- Поддерживаемые интенты: `show_stats`, `show_goals`, `show_history`, `show_subs`, `show_rates`, `show_week`, `show_budget`
- `handle_free_text` диспетчеризует интенты в соответствующие обработчики
- `claude_parser.parse_transaction` теперь пропускает типы `"unknown"` и `"intent"` (раньше оба возвращали `None`)

---

### Исправления

#### BUG-1 — Дата в курсах валют
- `get_rates_text()` добавляет строку `_Обновлено: DD.MM.YYYY_` из `date.today()`

#### BUG-2 — Форматирование валюты в транзакциях
- Новая функция `format_amount_display(amount, currency, amount_uzs)` в `formatters.py`
- Для иностранных валют показывает обе суммы: `500 $ (6 350 000 сум)`
- UZS отображается как прежде: `50 000 сум`

#### BUG-3 — Защита от нулевых и неизвестных сумм
- `PARSE_SYSTEM_PROMPT`: правило «если сумма не ясна — `amount=0`, `type="unknown"`»
- `handle_free_text`: проверка `amount <= 0` перед сохранением, иначе просит уточнить

#### BUG-4 — Редактирование и удаление подписок и целей
- `inline.py`: добавлены `sub_item_kb(sub_id)` и `goal_item_kb(goal_id)` с кнопками ✏️/🗑
- `states.py`: добавлены `EditSubStates` (waiting_name, waiting_amount, waiting_day) и `EditGoalStates` (waiting_name, waiting_amount)
- `supabase_db.py`: добавлены `update_subscription`, `delete_subscription`, `update_goal`, `delete_goal` (soft delete через `is_active=False`)
- `edit.py`: полные FSM-флоу для редактирования подписок и целей
- `subscriptions.py`: список подписок теперь отправляет каждую отдельным сообщением с `sub_item_kb`
- `goals.py`: список целей теперь отправляет каждую отдельным сообщением с `goal_item_kb`

#### BUG-5 — Автозачисление в цель при категории «накопления»
- Новый метод `find_goal_by_keyword(user_id, keyword)`: ищет активную цель по подстроке в названии, при отсутствии совпадения берёт первую по приоритету
- Если `type="expense"` и `category="накопления"` — бот вызывает `update_goal_saved` и **не** записывает расход в транзакции
- Ответ пользователю: прогресс-бар цели с новым значением

#### BUG-6 — Валидация суммы в FSM целей
- `add_goal_amount`: если `amount <= 0` — «Сумма должна быть больше нуля. Введи заново:» без выхода из FSM

---

### Технический долг / инфраструктура

- `bot/handlers/budget.py` — новый файл
- `bot/main.py`: зарегистрирован `budget.router` (до `transactions.router`), добавлена команда `/budget` в `set_my_commands`
- `bot/keyboards/reply.py`: `MENU_BUTTONS` пополнен строкой `"💰 Бюджет"`, клавиатура получила четвёртый ряд
- Исправлено имя колонки: `budget_uzs` → `amount_uzs` (реальная схема таблицы `monthly_budget`)

---

### Тесты

| Файл | До | После |
|---|---|---|
| `test_db.py` | 30 тестов | 49 тестов (+19) |
| `test_parser.py` | 10 тестов | 11 тестов (+1 `intent`, изменён `unknown`) |
| Остальные | 53 теста | 52 теста (без изменений) |
| **Итого** | **93** | **112** ✅ |

Все 112 тестов проходят, реальных API-запросов нет.

---

## v1.2 — ранее

### Исправления

- **FSM escape**: нажатие кнопок главного меню из любого FSM-состояния теперь сбрасывает состояние и открывает нужный раздел
  - `MENU_BUTTONS` frozenset как единый источник истины
  - Все FSM-обработчики получили фильтр `~F.text.in_(MENU_BUTTONS)`
  - Меню-обработчики вызывают `state.clear()` перед переходом

- **`/genlink` не реагировал**: заменён `RoleFilter` на inline-проверку `user_role` + fallback `_is_owner(message)`; добавлено логирование

- **OWNER_TG_ID bypass**: middleware проверяет env-переменную до запроса к БД — гарантированная роль `owner` без DB lookup

### Тесты

- Создан полный pytest-suite: 93 теста, 5 файлов, нулевые реальные запросы
- `conftest.py`: фикстуры `event_loop`, `db_chain`
- `pytest.ini`: `asyncio_mode = auto`
