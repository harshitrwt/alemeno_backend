import os
import json
import time
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

CATEGORIES = [
    "Food", "Shopping", "Travel", "Transport",
    "Utilities", "Cash Withdrawal", "Entertainment", "Other",
]


def _call_with_retry(messages, max_retries=3):
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, then 2s
    raise last_error


def batch_classify(transactions: list[dict]):
    """
    transactions: [{"id": <row index>, "merchant": ..., "notes": ...}, ...]
    Returns {id: category} on success, or None if all retries failed.
    """
    if not transactions:
        return {}

    prompt = (
        f"Classify each transaction into exactly one of these categories: "
        f"{', '.join(CATEGORIES)}.\n"
        f'Return JSON like {{"results": [{{"id": <id>, "category": "<category>"}}]}}.\n'
        f"Transactions:\n{json.dumps(transactions)}"
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        raw = _call_with_retry(messages)
        parsed = json.loads(raw)
        return {item["id"]: item["category"] for item in parsed.get("results", [])}
    except Exception:
        return None


def generate_narrative(stats: dict):
    """
    stats: total_spend_inr, total_spend_usd, top_merchants, anomaly_count
    Returns {"narrative": ..., "risk_level": ...} on success, or None.
    """
    prompt = (
        f"Given this spending data: {json.dumps(stats)}\n"
        f'Return JSON: {{"narrative": "<2-3 sentence summary>", '
        f'"risk_level": "low|medium|high"}}.'
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        raw = _call_with_retry(messages)
        return json.loads(raw)
    except Exception:
        return None
