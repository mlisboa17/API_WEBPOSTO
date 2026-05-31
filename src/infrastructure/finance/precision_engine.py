from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import Dict

from src.infrastructure.config.settings import settings

# Set a conservative global context for financial precision
getcontext().prec = 28


QUANT = Decimal("0.0001")


def quantize(v: Decimal) -> Decimal:
    return v.quantize(QUANT, rounding=ROUND_HALF_UP)


def compute_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """Compute tax for a given amount using Decimal(12,4) precision."""
    if amount is None:
        amount = Decimal("0.0000")
    if tax_rate is None:
        tax_rate = Decimal("0.0000")
    tax = amount * (tax_rate / Decimal(100))
    return quantize(tax)


def compute_net_margin(revenue: Decimal, cost: Decimal, tax_rate: Decimal) -> Decimal:
    """Compute net margin after cost and tax, using Decimal precision."""
    revenue = revenue or Decimal("0.0000")
    cost = cost or Decimal("0.0000")
    tax = compute_tax(revenue, tax_rate)
    margin = revenue - cost - tax
    return quantize(margin)


async def cached_dashboard_aggregate(cache_client, key: str, compute_fn, ttl: int = 30):
    """Helper to attempt cache get, run compute_fn on miss, and set TTL (Valkey/Redis compatible)."""
    try:
        raw = await cache_client.get(key)
        if raw:
            return raw
    except Exception:
        raw = None

    result = await compute_fn()
    try:
        await cache_client.set(key, result, ex=ttl)
    except Exception:
        pass
    return result


def ip_blacklist_check(ip: str, blacklist: set[str]) -> bool:
    """Return True if IP is blacklisted."""
    return ip in blacklist
