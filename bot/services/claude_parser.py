import json
import os
from typing import Optional
import anthropic
from bot.utils.constants import PARSE_SYSTEM_PROMPT


_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def parse_transaction(text: str) -> Optional[dict]:
    client = get_client()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        if data.get("type") not in ("income", "expense", "unknown", "intent"):
            return None
        return data
    except (json.JSONDecodeError, Exception):
        return None


async def parse_subscription_nlp(text: str) -> Optional[dict]:
    client = get_client()
    system = """
Ты парсер подписок. Извлеки данные о подписке из сообщения пользователя.
Верни ТОЛЬКО валидный JSON без пояснений.

{
  "name": "название сервиса",
  "amount": число,
  "currency": "UZS" | "USD" | "RUB",
  "billing_day": число от 1 до 31 или null,
  "notes": "заметка или null"
}

Правила: "к" = 1000, "млн" = 1000000. Если валюта не указана — UZS.
"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return None
