EXPENSE_CATEGORIES = {
    "продукты":        ["korzinka", "makro", "супермаркет", "бакалея", "еда дома"],
    "кафе_рестораны":  ["ресторан", "кафе", "обед", "ужин", "доставка", "wolt",
                        "express24", "пицца", "бургер", "sushi"],
    "кофе_снеки":      ["кофе", "кофейня", "starbucks", "snack", "перекус"],
    "транспорт":       ["такси", "yandex", "uber", "автобус", "метро",
                        "бензин", "парковка", "заправка"],
    "ипотека_кредиты": ["ипотека", "кредит", "банк", "рассрочка", "долг"],
    "коммуналка":      ["свет", "газ", "вода", "коммунальные", "жкх"],
    "моб_интернет":    ["интернет", "телефон", "ucell", "beeline",
                        "uzmobile", "sim"],
    "аптека":          ["аптека", "лекарство", "таблетки"],
    "медицина":        ["врач", "клиника", "анализы", "больница", "стоматолог"],
    "семья_дети":      ["дети", "школа", "садик", "игрушки", "детский"],
    "красота_уход":    ["барбершоп", "парикмахер", "косметика", "салон",
                        "маникюр", "уход"],
    "одежда":          ["одежда", "кроссовки", "магазин", "шоппинг"],
    "подписки":        ["netflix", "spotify", "youtube", "apple", "chatgpt",
                        "claude", "vpn", "icloud", "подписка"],
    "развлечения":     ["кино", "концерт", "игры", "боулинг", "парк", "мероприятие"],
    "подарки":         ["подарок", "праздник", "день рождения", "той",
                        "цветы", "букет"],
    "образование":     ["курсы", "обучение", "книги", "udemy", "учёба"],
    "путешествия":     ["отель", "билет", "авиа", "перелёт", "booking", "airbnb",
                        "виза", "туристический", "поездка", "отпуск", "тур"],
    "накопления":      ["отложил", "накопления", "сбережения", "цель"],
    "другое":          [],
}

INCOME_CATEGORIES = {
    "зарплата":   ["зарплата", "аванс", "оплата", "получил зп"],
    "фриланс":    ["фриланс", "проект", "заказ", "клиент", "оплатили"],
    "подработка": ["подработка", "халтура", "дополнительный"],
    "проценты":   ["проценты", "депозит", "дивиденды"],
    "другое":     [],
}

CATEGORY_EMOJI = {
    # расходы
    "продукты": "🛒",
    "кафе_рестораны": "🍽",
    "кофе_снеки": "☕",
    "транспорт": "🚗",
    "ипотека_кредиты": "🏠",
    "коммуналка": "💡",
    "моб_интернет": "📡",
    "аптека": "💊",
    "медицина": "🏥",
    "семья_дети": "👨‍👩‍👧",
    "красота_уход": "💇",
    "одежда": "👕",
    "подписки": "📱",
    "развлечения": "🎬",
    "подарки": "🎁",
    "образование": "📚",
    "путешествия": "✈️",
    "накопления": "💰",
    "другое": "📦",
    # доходы
    "зарплата": "💵",
    "фриланс": "💻",
    "подработка": "🔧",
    "проценты": "📈",
    # legacy (старые транзакции в БД)
    "еда_питание": "🍽",
    "здоровье": "💊",
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
- Если сумма явно не указана или не может быть определена — используй amount=0 и type="unknown"
- Нельзя придумывать сумму — только парсить то, что написано

Правило для интентов (запросы на просмотр):
- Если пользователь просит что-то показать/открыть — используй type="intent"
- "покажи статистику", "статистика", "мои расходы" → intent_action="show_stats"
- "мои цели", "накопления", "покажи цели" → intent_action="show_goals"
- "история", "последние операции", "что тратил" → intent_action="show_history"
- "подписки", "мои подписки" → intent_action="show_subs"
- "курс", "курсы валют", "доллар сегодня" → intent_action="show_rates"
- "неделя", "итоги недели" → intent_action="show_week"
- "бюджет", "мой бюджет", "сколько осталось" → intent_action="show_budget"

Если в сообщении несколько транзакций (через запятую, перенос строки или просто перечислением) — верни массив с несколькими объектами.

ВСЕГДА возвращай JSON-массив (даже для одной транзакции):
[
  {
    "type": "expense" | "income" | "unknown" | "intent",
    "amount": число (всегда числом, 0 если неизвестно),
    "currency": "UZS" | "USD" | "RUB",
    "category": "одна из категорий",
    "description": "краткое описание на русском",
    "intent_action": "show_stats" | "show_goals" | "show_history" | "show_subs" | "show_rates" | "show_week" | "show_budget" (только для type=intent),
    "confidence": 0.0-1.0
  }
]

Категории расходов: продукты, кафе_рестораны, кофе_снеки, транспорт, ипотека_кредиты,
коммуналка, моб_интернет, аптека, медицина, семья_дети, красота_уход, одежда,
подписки, развлечения, подарки, образование, путешествия, накопления, другое

Категории доходов: зарплата, фриланс, подработка, проценты, другое

Примеры:
Вход: "потратил 50к на продукты"
Выход: [{"type":"expense","amount":50000,"currency":"UZS","category":"продукты","description":"Продукты","confidence":0.95}]

Вход: "получил зарплату 3 млн"
Выход: [{"type":"income","amount":3000000,"currency":"UZS","category":"зарплата","description":"Зарплата","confidence":0.98}]

Вход: "взял такси за 25к"
Выход: [{"type":"expense","amount":25000,"currency":"UZS","category":"транспорт","description":"Такси","confidence":0.95}]

Вход: "заплатил ипотеку 1.2 млн"
Выход: [{"type":"expense","amount":1200000,"currency":"UZS","category":"ипотека_кредиты","description":"Ипотека","confidence":0.97}]

Вход: "оплатил netflix 50к"
Выход: [{"type":"expense","amount":50000,"currency":"UZS","category":"подписки","description":"Netflix","confidence":0.96}]

Вход: "продлил vpn за 25к"
Выход: [{"type":"expense","amount":25000,"currency":"UZS","category":"подписки","description":"VPN","confidence":0.95}]

Вход: "Кроссовки 500к"
Выход: [{"type":"expense","amount":500000,"currency":"UZS","category":"одежда","description":"Кроссовки","confidence":0.90}]

Вход: "KFC 76000"
Выход: [{"type":"expense","amount":76000,"currency":"UZS","category":"кафе_рестораны","description":"KFC","confidence":0.90}]

Вход: "500к на кофе"
Выход: [{"type":"expense","amount":500000,"currency":"UZS","category":"кофе_снеки","description":"Кофе","confidence":0.91}]

Вход: "90к такси"
Выход: [{"type":"expense","amount":90000,"currency":"UZS","category":"транспорт","description":"Такси","confidence":0.91}]

Вход: "Минус 250к на бенз"
Выход: [{"type":"expense","amount":250000,"currency":"UZS","category":"транспорт","description":"Бензин","confidence":0.93}]

Вход: "Обед и кофе 85000"
Выход: [{"type":"expense","amount":85000,"currency":"UZS","category":"кафе_рестораны","description":"Обед и кофе","confidence":0.89}]

Вход: "Кроссы жене 750000"
Выход: [{"type":"expense","amount":750000,"currency":"UZS","category":"одежда","description":"Кроссовки жене","confidence":0.88}]

Вход: "Аптека ребенку 90000"
Выход: [{"type":"expense","amount":90000,"currency":"UZS","category":"аптека","description":"Аптека ребёнку","confidence":0.92}]

Вход: "Шиномонтаж 120к"
Выход: [{"type":"expense","amount":120000,"currency":"UZS","category":"транспорт","description":"Шиномонтаж","confidence":0.92}]

Вход: "Страховка авто 400к"
Выход: [{"type":"expense","amount":400000,"currency":"UZS","category":"транспорт","description":"Страховка авто","confidence":0.91}]

Вход: "WB 430000"
Выход: [{"type":"expense","amount":430000,"currency":"UZS","category":"одежда","description":"Wildberries","confidence":0.88}]

Вход: "Uzum 250000"
Выход: [{"type":"expense","amount":250000,"currency":"UZS","category":"другое","description":"Uzum","confidence":0.87}]

Вход: "Рассрочка iPhone 450$/месяц"
Выход: [{"type":"expense","amount":450,"currency":"USD","category":"ипотека_кредиты","description":"Рассрочка iPhone","confidence":0.90}]

Вход: "Аренда 500$"
Выход: [{"type":"expense","amount":500,"currency":"USD","category":"коммуналка","description":"Аренда квартиры","confidence":0.93}]

Вход: "Скинул за квартиру 300$"
Выход: [{"type":"expense","amount":300,"currency":"USD","category":"коммуналка","description":"Аренда квартиры","confidence":0.91}]

Вход: "Korzinka 560000"
Выход: [{"type":"expense","amount":560000,"currency":"UZS","category":"продукты","description":"Korzinka","confidence":0.94}]

Вход: "Makro 380000"
Выход: [{"type":"expense","amount":380000,"currency":"UZS","category":"продукты","description":"Makro","confidence":0.94}]

Вход: "Gemini 100$"
Выход: [{"type":"expense","amount":100,"currency":"USD","category":"подписки","description":"Gemini","confidence":0.95}]

Вход: "ChatGPT Plus 20$"
Выход: [{"type":"expense","amount":20,"currency":"USD","category":"подписки","description":"ChatGPT Plus","confidence":0.95}]

Вход: "покажи статистику"
Выход: [{"type":"intent","intent_action":"show_stats","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "мои цели"
Выход: [{"type":"intent","intent_action":"show_goals","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "история"
Выход: [{"type":"intent","intent_action":"show_history","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "мои подписки"
Выход: [{"type":"intent","intent_action":"show_subs","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "курс доллара"
Выход: [{"type":"intent","intent_action":"show_rates","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "итоги недели"
Выход: [{"type":"intent","intent_action":"show_week","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "мой бюджет"
Выход: [{"type":"intent","intent_action":"show_budget","amount":0,"currency":"UZS","category":"другое","description":"","confidence":1.0}]

Вход: "купил что-то"
Выход: [{"type":"unknown","amount":0,"currency":"UZS","category":"другое","description":"","confidence":0.1}]

Вход: "купил одежду 120к, обед 50к, бензин за 200000"
Выход: [{"type":"expense","amount":120000,"currency":"UZS","category":"одежда","description":"Одежда","confidence":0.90},{"type":"expense","amount":50000,"currency":"UZS","category":"кафе_рестораны","description":"Обед","confidence":0.90},{"type":"expense","amount":200000,"currency":"UZS","category":"транспорт","description":"Бензин","confidence":0.93}]

Вход: "зарплата 5 млн\nтакси 80к"
Выход: [{"type":"income","amount":5000000,"currency":"UZS","category":"зарплата","description":"Зарплата","confidence":0.97},{"type":"expense","amount":80000,"currency":"UZS","category":"транспорт","description":"Такси","confidence":0.94}]
"""
