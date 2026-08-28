import pandas as pd

from scanner.patterns import (
    DETECTORS_TR,
    detect_breakout_retest,
    detect_double,
    detect_flag,
    detect_range,
    detect_sweep,
    detect_trendline_break,
    detect_triangle_wedge,
)


def _sub(n=70, last=0.0589, prev=0.0605, base=0.065, volume=100.0, last_volume=220.0):
    closes = [base] * n
    closes[-2] = prev
    closes[-1] = last
    return pd.DataFrame({
        "open": closes,
        "high": [c + 0.001 for c in closes],
        "low": [c - 0.001 for c in closes],
        "close": closes,
        "volume": [volume] * (n - 1) + [last_volume],
    })


def test_uselessusdt_double_top_regression_triggers_short():
    """~0.074-0.075 tepeler / ~0.059-0.060 neckline artik kacmamalı."""
    piv = [
        (5, 0.0680, "H"),
        (10, 0.0620, "L"),
        (18, 0.0742, "H"),
        (27, 0.0595, "L"),
        (37, 0.0750, "H"),
        (46, 0.0660, "L"),
        (54, 0.0690, "H"),
    ]
    sub = _sub()

    result = detect_double(piv, sub, atr=0.0010, price=0.0589)

    assert result is not None
    assert result["type"] == "double_top"
    assert result["dir"] == "short"
    assert result["state"] == "triggered"
    assert abs(result["trigger"] - 0.0595) < 1e-12
    # 0.0008 tepe farki eski 0.5 ATR (=0.0005) filtresini asiyordu.
    assert "0.0742/0.075" in result["note"]
    assert result["quality"] > 0.80


def test_double_bottom_can_form_before_neckline_break():
    piv = [
        (5, 1.10, "H"),
        (12, 1.000, "L"),
        (22, 1.080, "H"),
        (34, 0.985, "L"),
        (43, 1.045, "H"),
    ]
    sub = _sub(n=55, base=1.02, prev=1.025, last=1.030, last_volume=100.0)

    result = detect_double(piv, sub, atr=0.010, price=1.030)

    assert result is not None
    assert result["type"] == "double_bottom"
    assert result["dir"] == "long"
    assert result["state"] == "forming"
    assert abs(result["trigger"] - 1.080) < 1e-12


def test_close_random_pivots_are_rejected_by_minimum_bar_spacing():
    piv = [(10, 1.00, "H"), (11, 0.92, "L"), (13, 1.01, "H")]
    sub = _sub(n=30, base=0.97, prev=0.96, last=0.94)

    assert detect_double(piv, sub, atr=0.01, price=0.94) is None


def test_clear_trend_continuation_is_not_mislabeled_double_top():
    piv = [
        (5, 1.000, "H"),
        (12, 0.980, "L"),
        (20, 1.025, "H"),
        (28, 1.005, "L"),
        (36, 1.050, "H"),
    ]
    sub = _sub(n=50, base=1.03, prev=1.035, last=1.040)

    assert detect_double(piv, sub, atr=0.010, price=1.040) is None


def test_shallow_neckline_is_rejected():
    piv = [(10, 0.0750, "H"), (20, 0.0730, "L"), (30, 0.0745, "H")]
    sub = _sub(n=45, base=0.0740, prev=0.0738, last=0.0734)

    assert detect_double(piv, sub, atr=0.0010, price=0.0734) is None


def test_existing_detector_surface_is_preserved():
    # V3.0'da onaylanan detector gruplari korunmali. Triangle/wedge tek
    # fonksiyonda iki geometri ailesini kapsar; registry alt tipleri tutar.
    for fn in (
        detect_range,
        detect_double,
        detect_triangle_wedge,
        detect_flag,
        detect_trendline_break,
        detect_sweep,
        detect_breakout_retest,
    ):
        assert callable(fn)

    expected = {
        "range", "double_top", "double_bottom",
        "falling_wedge", "rising_wedge",
        "asc_triangle", "desc_triangle", "sym_triangle",
        "flag", "trendline_break", "liquidity_sweep", "breakout_retest",
    }
    assert expected.issubset(DETECTORS_TR)
