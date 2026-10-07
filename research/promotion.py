"""Walk-forward / OOS promotion gate for shadow challengers.

Produces review eligibility only. It cannot mutate production policy.
"""
from __future__ import annotations
from research.challenger import evaluate_policy, POLICIES

MIN_CALIBRATION = 60
MIN_OOS = 40
OOS_DAYS = 30
MAX_RECALL_DROP = 0.00
MAX_PRECISION_DROP = 0.03
MAX_AVG_MFE_DROP = 0.50


def split_time(episodes, oos_days=OOS_DAYS, now_ts=None):
    import time
    now_ts = int(time.time() if now_ts is None else now_ts)
    # Exclude the still-evaluating final 24h before splitting.
    mature = sorted([e for e in episodes if e.get("closed_at")
                     and now_ts - int(e["closed_at"]) >= 24 * 3600],
                    key=lambda e: int(e["closed_at"]))
    if not mature:
        return [], []
    cutoff = int(mature[-1]["closed_at"]) - oos_days * 86400
    return ([e for e in mature if int(e["closed_at"]) < cutoff],
            [e for e in mature if int(e["closed_at"]) >= cutoff])


def _delta(ch, cur, key):
    a, b = ch.get(key), cur.get(key)
    return None if a is None or b is None else a - b


def promotion_gate(ledger, challenger="trajectory_balanced", now_ts=None):
    if challenger not in POLICIES or challenger == "current":
        return {"status": "BLOCKED", "reason": "invalid challenger"}
    cal, oos = split_time(ledger.get("episodes") or [], now_ts=now_ts)
    if len(cal) < MIN_CALIBRATION or len(oos) < MIN_OOS:
        return {"status": "BLOCKED", "reason": "insufficient split sample",
                "calibration_n": len(cal), "oos_n": len(oos)}

    # Selection budget is identical for incumbent/challenger.
    cur_cal = evaluate_policy(cal, POLICIES["current"], now_ts=now_ts)
    ch_cal = evaluate_policy(cal, POLICIES[challenger], now_ts=now_ts)
    cur_oos = evaluate_policy(oos, POLICIES["current"], now_ts=now_ts)
    ch_oos = evaluate_policy(oos, POLICIES[challenger], now_ts=now_ts)
    if any(x.get("status") != "EVALUATED" for x in (cur_cal, ch_cal, cur_oos, ch_oos)):
        return {"status": "BLOCKED", "reason": "insufficient mature evaluation data",
                "calibration_n": len(cal), "oos_n": len(oos)}

    d_recall = _delta(ch_oos, cur_oos, "runner_recall")
    d_precision = _delta(ch_oos, cur_oos, "precision")
    d_mfe = _delta(ch_oos, cur_oos, "avg_mfe_selected")
    checks = {
        "oos_recall_noninferior": d_recall is not None and d_recall >= -MAX_RECALL_DROP,
        "oos_precision_noninferior": d_precision is not None and d_precision >= -MAX_PRECISION_DROP,
        "oos_avg_mfe_noninferior": d_mfe is not None and d_mfe >= -MAX_AVG_MFE_DROP,
        "calibration_recall_not_worse": _delta(ch_cal, cur_cal, "runner_recall") is not None
                                          and _delta(ch_cal, cur_cal, "runner_recall") >= 0,
    }
    eligible = all(checks.values())
    return {
        "status": "ELIGIBLE_FOR_REVIEW" if eligible else "BLOCKED",
        "automatic_promotion": False,
        "challenger": challenger,
        "calibration_n": len(cal), "oos_n": len(oos),
        "checks": checks,
        "oos_delta": {"runner_recall": d_recall, "precision": d_precision,
                      "avg_mfe_selected": d_mfe},
        "current_oos": cur_oos, "challenger_oos": ch_oos,
    }
