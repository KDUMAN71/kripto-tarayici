"""V3.5 opportunity ranking.

Discovery-only score. It prioritizes scarce deep-scan/API budget and MUST NOT
be interpreted as trade probability or added to ACTIVE confluence.
"""
from __future__ import annotations
import math


def _finite(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def return_pct(closed, bars):
    if closed is None or len(closed) <= bars:
        return 0.0
    a = float(closed["close"].iloc[-1-bars])
    b = float(closed["close"].iloc[-1])
    return (b / a - 1) * 100 if a else 0.0


def trajectory_features(a1, btc_a1=None):
    c = a1["closed"]
    r3 = return_pct(c, 3)
    r6 = return_pct(c, 6)
    btc3 = return_pct(btc_a1["closed"], 3) if btc_a1 else 0.0
    btc6 = return_pct(btc_a1["closed"], 6) if btc_a1 else 0.0
    return {
        "ret_3h": r3,
        "ret_6h": r6,
        "rel_btc_3h": r3 - btc3,
        "rel_btc_6h": r6 - btc6,
        "vol_ratio_1h": _finite(a1.get("vol_ratio")),
        "trend_1h": _finite(a1.get("tscore")),
    }


def opportunity_score(features):
    """Broad stable bands from replay findings; not fitted probabilities.

    Direction-agnostic magnitude is intentional at discovery stage. Direction
    remains the responsibility of pattern/HTF/execution engines.
    """
    r3 = abs(_finite(features.get("ret_3h")))
    r6 = abs(_finite(features.get("ret_6h")))
    rel3 = abs(_finite(features.get("rel_btc_3h")))
    rel6 = abs(_finite(features.get("rel_btc_6h")))
    vr = _finite(features.get("vol_ratio_1h"))

    score = 0.0
    # Replay separation was strongest into ~T-6h. Use broad bands rather than
    # exact sample medians to reduce overfit.
    score += min(r3 / 2.0, 2.0)
    score += min(r6 / 4.0, 2.0)
    score += min(rel3 / 1.5, 2.0)
    score += min(rel6 / 3.0, 1.5)
    if vr >= 1.2:
        score += min((vr - 1.0) / 0.5, 1.5)
    elif vr >= 0.9:
        score += 0.25
    return round(score, 3)


def rank_candidates(rows):
    return sorted(rows, key=lambda x: (-_finite(x.get("opportunity_score")),
                                       -_finite(x.get("quote_volume_24h")),
                                       x.get("symbol", "")))
