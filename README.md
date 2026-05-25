# Личный финансовый ассистент (Telegram Bot)

MVP v1.1 — Ташкент / СНГ

## Быстрый старт

### 1. Клонируй и настрой окружение

```bash
cd finance-bot
cp .env.example .env
```

Заполни `.env`:
```
BOT_TOKEN=         # от @BotFather
ANTHROPIC_API_KEY= # с console.anthropic.com
SUPABASE_URL=      # из Supabase Settings → API
SUPABASE_KEY=      # anon/public key
OWNER_TG_ID=       # свой Telegram ID (@userinfobot)
OWNER_USERNAME=    # свой @username (без @)
```

### 2. Создай БД в Supabase

Выполни `schema.sql` в Supabase SQL Editor, затем добавь себя как владельца:

```sql
INSERT INTO access_control (user_id, role)
VALUES (<твой_tg_id>, 'owner');
```

### 3. Установи зависимости и запусти

```bash
pip install -r requirements.txt
python -m bot.main
```

### 4. Деплой на Railway / Render

1. Push на GitHub
2. Создай новый проект в Railway/Render → Connect GitHub repo
3. Добавь переменные из `.env` в Settings → Environment
4. Deploy

---

## Использование

Просто пиши боту на русском:

| Сообщение | Что происходит |
|-----------|----------------|
| `потратил 50к на продукты` | Записывает расход 50 000 сум |
| `получил зарплату 3 млн` | Записывает доход 3 000 000 сум |
| `взял такси за 25к` | Расход, категория транспорт |
| `заплатил ипотеку 1.2 млн` | Расход, категория ипотека |
| `оплатил netflix 50к` | Расход, категория подписки |

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и онбординг |
| `/goals` | Цели накопления с прогресс-барами |
| `/stats` | Статистика за текущий месяц |
| `/week` | Итоги за неделю |
| `/history` | Последние 10 транзакций |
| `/add_goal` | Добавить цель накопления |
| `/save` | Пополнить цель |
| `/subs` | Список подписок |
| `/add_sub` | Добавить подписку |
| `/rates` | Курсы USD и RUB к UZS |
| `/help` | Список команд |

### Команды для owner

| Команда | Описание |
|---------|----------|
| `/invite_id 123456789` | Добавить пользователя по ID |
| `/invite @username` | Добавить по username |
| `/ban @username` | Заблокировать |
| `/users` | Список бета-тестеров |

## Стек

- Python 3.11
- aiogram 3.4
- Supabase (PostgreSQL)
- Claude API (NLP парсинг)
- httpx (курсы валют через cbu.uz)
