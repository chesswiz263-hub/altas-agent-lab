"""User-maintained token rate estimates (not a billing or spending guarantee)."""
import json
import math
import os


def token_rates(provider: str, model: str) -> tuple[float, float] | None:
    """USD per million input/output tokens, configured locally by the operator.

    Live prices are intentionally NOT hard-coded: vendors change them, and
    a model alias may point to a different tier over time.
    """
    if provider == "demo":
        return (0.0, 0.0)
    try:
        prices = json.loads(os.getenv("ATLAS_PRICING_JSON", "{}"))
        rate = prices.get(f"{provider}/{model}")
        if not isinstance(rate, (list, tuple)) or len(rate) != 2:
            return None
        x, y = float(rate[0]), float(rate[1])
        if any(not math.isfinite(v) or v < 0 or v > 10_000 for v in (x, y)):
            return None
        return x, y
    except (TypeError, ValueError, AttributeError):
        return None


def estimate_usd(provider: str, model: str, in_tokens: int, out_tokens: int) -> float | None:
    rates = token_rates(provider, model)
    if rates is None:
        return None
    return round((in_tokens * rates[0] + out_tokens * rates[1]) / 1_000_000, 9)
