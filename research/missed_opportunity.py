"""Missed-opportunity gate trace for V3.5 research.

This module is measurement-only. It does not change live scanner thresholds.
It turns runner-autopsy rows into explicit first/last gate evidence and makes
"no trace" a first-class observability failure instead of silently guessing.
"""
from __future__ import annotations

from collections import Counter


def summarize_gate_trace(symbol: str, autopsy: dict) -> dict:
    rows = list((autopsy.get("symbols") or {}).get(symbol) or [])
    if not rows:
        return {
            "symbol": symbol,
            "observed": False,
            "first_gate": None,
            "last_gate": None,
            "dominant_gate": None,
            "observations": 0,
            "diagnosis": "NO_TRACE",
        }

    counts = Counter()
    total = 0
    for row in rows:
        n = int(row.get("n", 1))
        total += n
        counts[(row.get("stage"), row.get("reason"))] += n
    (stage, reason), n = counts.most_common(1)[0]
    return {
        "symbol": symbol,
        "observed": True,
        "first_gate": {"stage": rows[0].get("stage"), "reason": rows[0].get("reason")},
        "last_gate": {"stage": rows[-1].get("stage"), "reason": rows[-1].get("reason")},
        "dominant_gate": {"stage": stage, "reason": reason, "count": n},
        "observations": total,
        "diagnosis": "GATE_IDENTIFIED",
    }


def compare_cases(symbols: list[str], autopsy: dict) -> list[dict]:
    return [summarize_gate_trace(s, autopsy) for s in symbols]
