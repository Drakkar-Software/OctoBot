"""Unified data schema normalization for exchange responses."""
from __future__ import annotations

from typing import Any


def normalize_ticker(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw ticker response into a unified schema."""
    return {
        "symbol": raw.get("symbol"),
        "last": _to_float(raw.get("last")),
        "bid": _to_float(raw.get("bid")),
        "ask": _to_float(raw.get("ask")),
        "high": _to_float(raw.get("high")),
        "low": _to_float(raw.get("low")),
        "volume": _to_float(raw.get("baseVolume")),
        "timestamp": raw.get("timestamp"),
    }


def normalize_order(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw order response into a unified schema."""
    return {
        "id": raw.get("id"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "price": _to_float(raw.get("price")),
        "amount": _to_float(raw.get("amount")),
        "filled": _to_float(raw.get("filled")),
        "remaining": _to_float(raw.get("remaining")),
        "status": raw.get("status"),
        "timestamp": raw.get("timestamp"),
    }


def _to_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
