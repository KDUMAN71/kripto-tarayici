import pandas as pd

from scanner import config as C
from scanner.decision import (geometry_gate, htf_zones, location_gate,
                              decision_summary)
from scanner.main import pretrade_msg


def _a(price=100.0, atr=2.0, tscore=0, rsi=50.0, vol=1.0,
       lows=None, highs=None, ema50=100.0, ema100=100.0, ema200=100.0,
       div=None, fib=None):
    return {
        "price": price, "atr": atr, "tscore": tscore, "rsi": rsi,
        "vol_ratio": vol, "pivot_lows": lows or [], "pivot_highs": highs or [],
        "ema50": ema50, "ema100": ema100, "ema200": ema200,
        "ema50_slope": 0.0, "ema100_slope": 0.0, "ema200_slope": 0.0,
        "rsi_divergence": div,
        "fib": fib or {"levels": {}},
    }


def test_tp1_below_1_5r_is_hard_reject():
    ok, rr = geometry_gate(100.0, 98.0, 102.0)
    assert ok is False
    assert rr == 1.0
    ok, rr = geometry_gate(100.0, 98.0, 103.0)
    assert ok is True
    assert rr == 1.5


def test_dot_like_support_cluster_blocks_short_watch():
    a4 = _a(price=0.840, atr=0.012, tscore=-1,
            lows=[0.829, 0.831], highs=[0.860],
            ema50=0.855, ema100=0.831, ema200=0.805,
            fib={"levels": {"0.618": 0.8305}})
    a1d = _a(price=0.840, atr=0.025, tscore=1,
             lows=[0.826], highs=[0.92],
             ema50=0.850, ema100=0.82, ema200=0.76)
    zones = htf_zones(0.840, a4, a1d)
    assert zones["support"] is not None
    veto = location_gate("short", "WATCH", 0.8352, 0.840, zones, hold_count=0)
    assert veto is not None
    assert "HTF destek" in veto


def test_same_support_allows_short_only_after_break_and_hold():
    a4 = _a(price=0.824, atr=0.012, tscore=-1,
            lows=[0.829, 0.831], highs=[0.860],
            ema50=0.855, ema100=0.831, ema200=0.805,
            fib={"levels": {"0.618": 0.8305}})
    a1d = _a(price=0.824, atr=0.025, tscore=0,
             lows=[0.826], highs=[0.92], ema50=0.850, ema100=0.82, ema200=0.76)
    zones = htf_zones(0.824, a4, a1d)
    veto = location_gate("short", "ACTIVE", 0.823, 0.824, zones,
                         hold_count=C.ACTIVE_MIN_HOLD_CLOSES)
    assert veto is None


def test_decision_engine_can_favor_long_at_htf_support_despite_weak_1h():
    a15 = _a(price=0.840, atr=0.004, tscore=0, rsi=41, vol=1.4, div="bullish")
    a1h = _a(price=0.840, atr=0.008, tscore=-1, rsi=42, vol=1.1, div="bullish")
    a4 = _a(price=0.840, atr=0.012, tscore=1,
            lows=[0.829, 0.831], highs=[0.860], ema50=0.855,
            ema100=0.831, ema200=0.805,
            fib={"levels": {"0.618": 0.8305}})
    a1d = _a(price=0.840, atr=0.025, tscore=1,
             lows=[0.826], highs=[0.92], ema50=0.850, ema100=0.82, ema200=0.76)
    ctx = {"taker_15m": 0.53, "oi": {"1h": 0.8}}
    regime = {"trend": 1, "hard_break": None}
    d = decision_summary(a15, a1h, a4, a1d, regime, ctx)
    assert d["long_advantage"] > d["short_advantage"]
    assert d["bias"] == "LONG"


def test_message_calls_advantage_model_not_win_probability():
    sig = {
        "status": "WATCH", "side": "LONG", "trigger": 100.0, "alarm": 99.65,
        "dist_pct": 0.8, "entry_lo": 99.8, "entry_hi": 100.4, "sl": 98.0,
        "risk_pct": 2.0, "tp1": 103.0, "tp2": 105.0, "tp3": None,
        "rr1": 1.5, "rr2": 2.5, "rr3": None, "setup_type": "double_bottom",
        "score": 9, "score_max": 13, "oi": {}, "funding": 0.0,
        "score_parts": [], "decision_bias": "LONG", "decision_strength": "guclu",
        "long_advantage": 64, "short_advantage": 36, "priority_setup": True,
        "htf_support": 98.5, "htf_resistance": 106.0,
    }
    msg = pretrade_msg("TESTUSDT", sig, "")
    assert "model avantajı LONG %64 / SHORT %36" in msg
    assert "kazanma" not in msg.lower()
    assert "PRIORITY" in msg
