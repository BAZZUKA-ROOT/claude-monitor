import os
import requests
from datetime import datetime, timezone, timedelta


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BILLING_DAY = int(os.getenv("BILLING_DAY", "1"))

# Cost per million tokens (adjust if Anthropic updates pricing)
INPUT_COST_PER_M  = 3.00   # USD / 1M input tokens  (Sonnet 3.5 reference)
OUTPUT_COST_PER_M = 15.00  # USD / 1M output tokens


def _billing_period():
    """Return (start, end) ISO dates for the current billing period."""
    now = datetime.now(timezone.utc)
    if now.day >= BILLING_DAY:
        start = now.replace(day=BILLING_DAY, hour=0, minute=0, second=0, microsecond=0)
    else:
        # previous month
        first_of_month = now.replace(day=1)
        prev_month = first_of_month - timedelta(days=1)
        start = prev_month.replace(day=BILLING_DAY, hour=0, minute=0, second=0, microsecond=0)
    end = now
    return start.date().isoformat(), end.date().isoformat()


def fetch_usage() -> dict:
    """
    Fetch token usage from the Anthropic usage API.

    Endpoint: GET /v1/organizations/usage
    Requires: Organization Admin API key (console.anthropic.com → API Keys).

    Returns a dict with: input_tokens, output_tokens, total_tokens, cost_usd,
    period_start, period_end, raw_response (for debugging).
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    period_start, period_end = _billing_period()

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    params = {
        "start_date": period_start,
        "end_date":   period_end,
    }

    resp = requests.get(
        "https://api.anthropic.com/v1/organizations/usage",
        headers=headers,
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # Aggregate across all models/workspaces
    input_tokens  = 0
    output_tokens = 0
    for entry in data.get("data", []):
        input_tokens  += entry.get("input_tokens", 0)
        output_tokens += entry.get("output_tokens", 0)

    total_tokens = input_tokens + output_tokens
    cost_usd = (
        input_tokens  / 1_000_000 * INPUT_COST_PER_M +
        output_tokens / 1_000_000 * OUTPUT_COST_PER_M
    )

    return {
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "total_tokens":  total_tokens,
        "cost_usd":      round(cost_usd, 6),
        "period_start":  period_start,
        "period_end":    period_end,
        "raw":           data,
    }
