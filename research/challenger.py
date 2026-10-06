"""Offline challenger evaluation for V3.5.

Never mutates scanner config. Policies are pure scoring/selection functions.
"""
from __future__ import annotations
import time

RUNNER_MFE = 10.0
EVAL_HORIZON_H = 24
MIN_MATURE_EPISODES = 20


def _f(e, key, default=0.0):
    src = e.get("initial_features") or {}
    try: return float(src.get(key, default))
    except (TypeError, ValueError): return default


def policy_current(e):
    # Approximation of current discovery ranking from immutable initial features.
    return float(_f(e, "opportunity_score"))


def policy_trajectory_balanced(e):
    r3, r6 = abs(_f(e, "ret_3h")), abs(_f(e, "ret_6h"))
    rel3, rel6 = abs(_f(e, "rel_btc_3h")), abs(_f(e, "rel_btc_6h"))
    vr = _f(e, "vol_ratio_1h")
    # Challenger deliberately reduces single-feature saturation and rewards
    # simultaneous trajectory + relative-strength participation.
    score = min(r3 / 2.5, 1.5) + min(r6 / 5.0, 1.5)
    score += min(rel3 / 2.0, 1.5) + min(rel6 / 4.0, 1.0)
    if vr >= 1.1: score += min((vr - 1.0) / 0.6, 1.25)
    if r3 >= 1.5 and r6 >= 3.0 and rel3 >= 1.0: score += 1.0
    return round(score, 3)


POLICIES = {"current": policy_current, "trajectory_balanced": policy_trajectory_balanced}


def evaluate_policy(episodes, fn, top_fraction=0.25, now_ts=None):
    now_ts = int(time.time() if now_ts is None else now_ts)
    eligible = [e for e in episodes
                if (e.get("initial_features") or {}).get("price")
                and e.get("closed_at")
                and now_ts - int(e["closed_at"]) >= EVAL_HORIZON_H * 3600]
    if len(eligible) < MIN_MATURE_EPISODES:
        return {"n": len(eligible), "selected": 0, "runner_recall": None, "precision": None,
                "avg_mfe_selected": None, "status": "INSUFFICIENT_MATURE_DATA"}
    ranked = sorted(eligible, key=fn, reverse=True)
    k = max(1, int(round(len(ranked) * top_fraction)))
    selected = ranked[:k]
    runners = [e for e in eligible if float(e.get("mfe_pct") or 0) >= RUNNER_MFE]
    caught = [e for e in selected if float(e.get("mfe_pct") or 0) >= RUNNER_MFE]
    return {
        "n": len(eligible), "selected": len(selected),
        "runner_count": len(runners),
        "runner_recall": len(caught) / len(runners) if runners else None,
        "precision": len(caught) / len(selected) if selected else None,
        "avg_mfe_selected": sum(float(e.get("mfe_pct") or 0) for e in selected) / len(selected),
        "status": "EVALUATED",
    }


def compare(ledger, top_fraction=0.25, now_ts=None):
    eps = ledger.get("episodes") or []
    return {name: evaluate_policy(eps, fn, top_fraction, now_ts=now_ts)
            for name, fn in POLICIES.items()}
