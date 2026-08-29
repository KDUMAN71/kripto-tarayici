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


def _a(price=None, ph=(), pl=(), **kw):
    d = {"pivot_highs": list(ph), "pivot_lows": list(pl), "atr": (price or 1) * 0.008}
    if price is not None:
        d["price"] = price
    d.update(kw); return d


def test_dot_zone_sides_and_untested_short_blocked():
    from scanner.decision import htf_zones, location_gate
    price = 0.8372
    a4h = _a(ph=(0.8612, 0.8618, 0.8406, 0.84506), pl=(0.829, 0.8289), price=price,
             ema50=0.8612, ema100=0.8459, ema200=0.8289,
             fib={"levels": {"0.618": 0.84058}})
    z = htf_zones(price, a4h)
    assert z["support"] and z["support"]["level"] <= price
    assert z["resistance"] and z["resistance"]["level"] >= price
    # fiyat HTF destek bolgesindeyken teyitsiz SHORT WATCH cikamaz
    veto = location_gate("short", "WATCH", 0.836, price, z, hold_count=0)
    assert veto is not None


def test_zone_side_invariant_never_inverts():
    from scanner.decision import htf_zones
    for price in (0.5, 1.0, 87.3, 0.0042):
        lv = [price * m for m in (0.90, 0.955, 0.985, 1.015, 1.05, 1.10)]
        a4h = _a(ph=lv[3:], pl=lv[:3], price=price)
        z = htf_zones(price, a4h)
        if z["support"]:
            assert z["support"]["level"] <= price
        if z["resistance"]:
            assert z["resistance"]["level"] >= price


def test_flip_plan_triggers_on_correct_side():
    from scanner.decision import decision_summary, build_flip_plan
    price = 0.8372
    a15 = _a(price=price, pl=(0.80, 0.81), ph=(0.86, 0.88), rsi=44)
    a1h = _a(price=price, pl=(0.8289,), ph=(0.8442, 0.852), rsi=41, vol_ratio=0.9)
    a4h = _a(ph=(0.8612, 0.8618, 0.8406, 0.84506), pl=(0.829, 0.8289), price=price,
             ema50=0.8612, ema100=0.8459, ema200=0.8289, tscore=-1,
             fib={"levels": {"0.618": 0.84058}})
    dec = decision_summary(a15, a1h, a4h, None, {"trend": 1}, {"taker_15m": 0.456, "oi": {"1h": 0.57}})
    fp = build_flip_plan("short", price, a15, a1h, a4h, dec)
    if fp:  # alternatif LONG tetigi fiyatin ALTINDA olamaz
        assert fp["side"] == "LONG" and fp["trigger"] >= price


def test_prefilter_admits_neutral_htf():
    from scanner import config as C
    assert C.PREFILTER_MIN_TSCORE in (None, 0)


def test_fib_prefers_recent_swing_over_stale_spike():
    import pandas as pd
    from scanner.indicators import fibonacci_context
    n = 120
    close = [100.0] * n
    high = [101.0] * n; low = [99.0] * n
    high[5] = 160.0                      # bayat spike
    for i, px in enumerate(range(0, 30)):  # yakin bacak: 90 -> 120
        low[n - 35 + i] = 90 + px; high[n - 35 + i] = 92 + px
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                       "volume": [1] * n})
    fib = fibonacci_context(df)
    assert fib["swing_high"] is None or fib["swing_high"] < 150
