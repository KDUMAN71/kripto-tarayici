"""V3.5 deterministic failure attribution.

Offline/measurement only. Classification never changes production policy.
"""
from __future__ import annotations
from collections import Counter

RUNNER_MFE_PCT = 10.0
LATE_RUN_PCT = 1.25
PREMATURE_STOP_MFE_PCT = 3.0


def _reason(e):
    return str(e.get("close_reason") or "").lower()


def classify_episode(e):
    """Return one primary diagnosis plus evidence.

    Uses only outcomes already recorded in the ledger. Future-looking MFE is
    explicitly an evaluation label, never a live feature.
    """
    outcome = e.get("outcome") or e.get("status")
    reason = _reason(e)
    mfe = float(e.get("mfe_pct") or 0)
    mae = float(e.get("mae_pct") or 0)
    initial = e.get("initial_features") or {}
    events = e.get("events") or []

    if outcome == "STOPPED":
        if mfe >= PREMATURE_STOP_MFE_PCT:
            return {"class": "PREMATURE_STOP", "evidence": {"mfe_pct": mfe, "mae_pct": mae}}
        return {"class": "VALID_LOSS", "evidence": {"mfe_pct": mfe, "mae_pct": mae}}

    if outcome in ("TP2_HIT", "TP3_HIT", "TP1_HIT", "CLOSED"):
        return {"class": "VALID_WIN", "evidence": {"mfe_pct": mfe, "mae_pct": mae}}

    if outcome == "MISSED":
        return {"class": "LATE_DETECTION", "evidence": {"reason": reason, "mfe_pct": mfe}}

    if outcome in ("REJECTED", "CANCELLED", "EXPIRED", "PRE_RUNNER_EXPIRED"):
        if mfe >= RUNNER_MFE_PCT:
            if "geometry" in reason or "r:r" in reason or "risk" in reason:
                cls = "BAD_RR"
            elif "reclaim" in reason or "hold" in reason or "breakout" in reason:
                cls = "FALSE_BREAKOUT" if outcome == "CANCELLED" else "MISSED_RUNNER"
            elif "liquid" in reason or "hacim" in reason:
                cls = "DISCOVERY_GATE_REJECT"
            else:
                cls = "MISSED_RUNNER"
            return {"class": cls, "evidence": {"outcome": outcome, "reason": reason, "mfe_pct": mfe}}
        return {"class": "VALID_REJECT", "evidence": {"outcome": outcome, "reason": reason, "mfe_pct": mfe}}

    # Historical/hand-labeled cases can carry explicit thesis/execution facts.
    if initial.get("thesis_correct") and initial.get("execution_bad"):
        return {"class": "CORRECT_THESIS_BAD_EXECUTION", "evidence": {"source": "explicit_label"}}

    if any("no_setup" in str(x.get("reason", "")).lower() for x in events) and mfe >= RUNNER_MFE_PCT:
        return {"class": "PATTERN_MISS", "evidence": {"mfe_pct": mfe}}

    return {"class": "UNCLASSIFIED", "evidence": {"outcome": outcome, "reason": reason, "mfe_pct": mfe}}


def attribute_ledger(ledger):
    rows = []
    for e in ledger.get("episodes", []):
        d = classify_episode(e)
        rows.append({"candidate_id": e.get("candidate_id"), "symbol": e.get("symbol"),
                     "status": e.get("status"), **d})
    counts = Counter(r["class"] for r in rows)
    return {"episodes": rows, "counts": dict(counts), "total": len(rows)}
