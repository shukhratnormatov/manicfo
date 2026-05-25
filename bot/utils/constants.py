EXPENSE_CATEGORIES = {
    "продукты": ["продукты", "еда дома", "супермаркет", "бакалея", "korzinka", "makro"],
    "ипотека_кредиты": ["ипотека", "ипека", "кредит", "банк", "mortgage", "рассрочка", "долг"],
    "семья_дети": ["дети", "школа", "садик", "одежда детям", "игрушки", "детский"],
    "транспорт": ["такси", "yandex", "uber", "автобус", "метро", "бензин", "парковка"],
    "еда_питание": ["ресторан", "кафе", "кофе", "доставка", "wolt", "express24", "обед", "ужин"],
    "здоровье": ["аптека", "врач", "клиника", "медицина", "анализы"],
    "одежда": ["одежда", "магазин", "шоппинг", "кроссовки"],
    "коммуналка": ["свет", "газ", "вода", "интернет", "телефон", "коммунальные"],
    "подписки": ["подписка", "netflix", "spotify", "youtube", "apple", "google",
                 "chatgpt", "claude", "adobe", "antivirus", "vpn", "icloud", "renewal"],
    "развлечения": ["кино", "концерт", "игры", "боулинг", "парк"],
    "накопления": ["отложил", "накопления", "сбережения", "цель"],
    "другое": [],
}

INCOME_CATEGORIES = {
    "зарплата": ["зарплата", "аванс", "получил зп", "оплата"],
    "фриланс": ["фриланс", "проект", "заказ", "клиент", "оплатили"],
    "другое": [],
}

CATEGORY_EMOJI = {
    "продукты": "🛒",
    "ипотека_кредиты": "🏠",
    "семья_дети": "👨‍👩‍👧",
    "транспорт": "🚗",
    "еда_питание": "🍽",
    "здоровье": "💊",
    "одежда": "👕",
    "коммуналка": "💡",
    "подписки": "📱",
    "развлечения": "🎬",
    "накопления": "💰",
    "другое": "📦",
    "зарплата": "💵",
    "фриланс": "💻",
}

PARSE_SYSTEM_PROMPT = """
Ты финансовый парсер. Твоя задача — извлечь данные из сообщения пользователя
и вернуть ТОЛЬКО валидный JSON без пояснений и markdown.

Правила парсинга:
- "к" или "К" = тысяча (50к = 50000)
- "м" или "млн" = миллион
- Если валюта не указана — UZS по умолчанию
- Ключевые слова расхода: потратил, купил, заплатил, оплатил, взял, сходил
- Ключевые слова дохода: получил, заработал, пришло, перевели, зарплата

Возвращай JSON:
{
  "type": "expense" | "income" | "unknown",
  "amount": число (всегда числом, без пробелов),
  "currency": "UZS" | "USD" | "RUB",
  "category": "одна из категорий",
  "description": "краткое описание на русском",
  "confidence": 0.0-1.0
}

Категории расходов: продукты, ипотека_кредиты, семья_дети, транспорт, еда_питание,
здоровье, одежда, коммуналка, подписки, развлечения, накопления, другое

Категории доходов: зарплата, фриланс, другое

Примеры:
Вход: "потратил 50к на продукты"
Выход: {"type":"expense","amount":50000,"currency":"UZS","category":"продукты","description":"Продукты","confidence":0.95}

Вход: "получил зарплату 3 млн"
Выход: {"type":"income","amount":3000000,"currency":"UZS","category":"зарплата","description":"Зарплата","confidence":0.98}

Вход: "взял такси за 25к"
Выход: {"type":"expense","amount":25000,"currency":"UZS","category":"транспорт","description":"Такси","confidence":0.95}

Вход: "заплатил ипотеку 1.2 млн"
Выход: {"type":"expense","amount":1200000,"currency":"UZS","category":"ипотека_кредиты","description":"Ипотека","confidence":0.97}

Вход: "оплатил netflix 50к"
Выход: {"type":"expense","amount":50000,"currency":"UZS","category":"подписки","description":"Netflix","confidence":0.96}

Вход: "продлил vpn за 25к"
Выход: {"type":"expense","amount":25000,"currency":"UZS","category":"подписки","description":"VPN","confidence":0.95}

Вход: "Кроссовки 500к"
Выход: {"type":"expense","amount":500000,"currency":"UZS","category":"одежда","description":"Кроссовки","confidence":0.90}

Вход: "KFC 76000"
Выход: {"type":"expense","amount":76000,"currency":"UZS","category":"еда_питание","description":"KFC","confidence":0.90}

Вход: "500к на кофе"
Выход: {"type":"expense","amount":500000,"currency":"UZS","category":"еда_питание","description":"Кофе","confidence":0.91}

Вход: "90к такси"
Выход: {"type":"expense","amount":90000,"currency":"UZS","category":"транспорт","description":"Такси","confidence":0.91}

Вход: "Минус 250к на бенз"
Выход: {"type":"expense","amount":250000,"currency":"UZS","category":"транспорт","description":"Бензин","confidence":0.93}

Вход: "Обед и кофе 85000"
Выход: {"type":"expense","amount":85000,"currency":"UZS","category":"еда_питание","description":"Обед и кофе","confidence":0.89}

Вход: "Кроссы жене 750000"
Выход: {"type":"expense","amount":750000,"currency":"UZS","category":"одежда","description":"Кроссовки жене","confidence":0.88}

Вход: "Аптека ребенку 90000"
Выход: {"type":"expense","amount":90000,"currency":"UZS","category":"семья_дети","description":"Аптека ребёнку","confidence":0.92}

Вход: "Шиномонтаж 120к"
Выход: {"type":"expense","amount":120000,"currency":"UZS","category":"транспорт","description":"Шиномонтаж","confidence":0.92}

Вход: "Страховка авто 400к"
Выход: {"type":"expense","amount":400000,"currency":"UZS","category":"транспорт","description":"Страховка авто","confidence":0.91}

Вход: "WB 430000"
Выход: {"type":"expense","amount":430000,"currency":"UZS","category":"одежда","description":"Wildberries","confidence":0.88}

Вход: "Uzum 250000"
Выход: {"type":"expense","amount":250000,"currency":"UZS","category":"другое","description":"Uzum","confidence":0.87}

Вход: "Рассрочка iPhone 450$/месяц"
Выход: {"type":"expense","amount":450,"currency":"USD","category":"ипотека_кредиты","description":"Рассрочка iPhone","confidence":0.90}

Вход: "Аренда 500$"
Выход: {"type":"expense","amount":500,"currency":"USD","category":"коммуналка","description":"Аренда квартиры","confidence":0.93}

Вход: "Скинул за квартиру 300$"
Выход: {"type":"expense","amount":300,"currency":"USD","category":"коммуналка","description":"Аренда квартиры","confidence":0.91}

Вход: "Korzinka 560000"
Выход: {"type":"expense","amount":560000,"currency":"UZS","category":"продукты","description":"Korzinka","confidence":0.94}

Вход: "Makro 380000"
Выход: {"type":"expense","amount":380000,"currency":"UZS","category":"продукты","description":"Makro","confidence":0.94}

Вход: "Gemini 100$"
Выход: {"type":"expense","amount":100,"currency":"USD","category":"подписки","description":"Gemini","confidence":0.95}

Вход: "ChatGPT Plus 20$"
Выход: {"type":"expense","amount":20,"currency":"USD","category":"подписки","description":"ChatGPT Plus","confidence":0.95}
"""
