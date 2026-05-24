-- Пользователи
CREATE TABLE users (
    id          BIGINT PRIMARY KEY,
    username    TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    base_currency TEXT DEFAULT 'UZS'
);

-- Транзакции
CREATE TABLE transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT REFERENCES users(id),
    type        TEXT CHECK (type IN ('income', 'expense')),
    amount      NUMERIC(15, 2),
    currency    TEXT DEFAULT 'UZS',
    amount_uzs  NUMERIC(15, 2),
    category    TEXT,
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Цели накопления
CREATE TABLE goals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       BIGINT REFERENCES users(id),
    name          TEXT,
    target_amount NUMERIC(15, 2),
    saved_amount  NUMERIC(15, 2) DEFAULT 0,
    currency      TEXT DEFAULT 'UZS',
    deadline      DATE,
    priority      INT,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Контроль доступа
CREATE TABLE access_control (
    user_id    BIGINT PRIMARY KEY,
    role       TEXT DEFAULT 'beta' CHECK (role IN ('owner', 'beta', 'banned')),
    invited_by BIGINT REFERENCES users(id),
    note       TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ежемесячные бюджеты
CREATE TABLE budgets (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   BIGINT REFERENCES users(id),
    category  TEXT,
    limit_uzs NUMERIC(15, 2),
    month     DATE
);

-- Подписки
CREATE TABLE subscriptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT REFERENCES users(id),
    name        TEXT NOT NULL,
    amount      NUMERIC(15, 2),
    currency    TEXT DEFAULT 'UZS',
    amount_uzs  NUMERIC(15, 2),
    billing_day INT,
    is_active   BOOLEAN DEFAULT TRUE,
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    last_charged DATE
);

-- Владелец добавляется вручную при первом деплое:
-- INSERT INTO access_control (user_id, role) VALUES (<твой_tg_id>, 'owner');
