"""Research-only grouping of recurring setups. Never gates ACTIVE decisions."""
from __future__ import annotations
import hashlib


def opportunity_identity(symbol, signal):
    """Stable identity for the same market thesis, without using future data."""
    side = signal.get("side", "UNKNOWN")
    family = signal.get("setup_type", "unknown")
    # Structural reference is only used when available; no arbitrary price rounding.
    thesis = signal.get("htf_support") if side == "LONG" else signal.get("htf_resistance")
    key = "|".join((str(symbol), str(side), str(family), str(thesis or "unknown")))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def duplicate_diagnostics(signals):
    """Offline visibility only: matching identities do NOT suppress alerts."""
    buckets = {}
    for symbol, signal in signals.items():
        if signal.get("status") != "ACTIVE":
            continue
        key = opportunity_identity(symbol, signal)
        buckets.setdefault(key, []).append(symbol)
    return {k: sorted(v) for k, v in buckets.items() if len(v) > 1}
