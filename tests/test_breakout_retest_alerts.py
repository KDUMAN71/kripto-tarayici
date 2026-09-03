import pandas as pd

from scanner import config as C
from scanner import runtime_policy as RP
from scanner import state as ST


def _a15(price=101.0, low1=100.8, low2=100.05, close1=101.0, close2=100.6,
         vol=1.1, rsi=55.0):
    df = pd.DataFrame([
        {"open": 100.7, "high": 101.3, "low": low1, "close": close1,
         "ema20": 100.4, "ma7": 100.5},
        {"open": 100.7, "high": 100.9, "low": low2, "close": close2,
         "ema20": 100.3, "ma7": 100.4},
    ])
    return {"price": price, "atr": 1.0, "closed": df, "vol_ratio": vol, "rsi": rsi}


def _sig():
    return {
        "status": "ACTIVE", "side": "LONG", "setup_type": "breakout_retest",
        "trigger": 100.0, "activated_at": 1000, "sl": 98.0,
        "tp1": 104.0, "tp2": 106.0, "tp3": 109.0,
    }


def test_breakout_uses_first_confirmed_15m_hold():
    assert C.RETEST_MIN_HOLD_CLOSES == 1


def test_retest_must_be_armed_before_second_alert(monkeypatch):
    monkeypatch.setattr(ST, "now", lambda: 2000)
    s = _sig()
    ok, _, _ = RP._retest_confirmed(s, _a15(price=101.0))
    assert ok is False
    assert s.get("retest_armed") is True


def test_armed_retest_with_ema_volume_rsi_confirms(monkeypatch):
    monkeypatch.setattr(ST, "now", lambda: 2000)
    s = _sig()
    s["retest_armed"] = True
    ok, lo, hi = RP._retest_confirmed(s, _a15(price=100.6))
    assert ok is True
    assert lo <= 100.0 <= hi


def test_retest_rejected_without_volume(monkeypatch):
    monkeypatch.setattr(ST, "now", lambda: 2000)
    s = _sig()
    s["retest_armed"] = True
    ok, _, _ = RP._retest_confirmed(s, _a15(price=100.6, vol=0.5))
    assert ok is False


def test_structural_setup_does_not_emit_formational_retest(monkeypatch):
    monkeypatch.setattr(ST, "now", lambda: 2000)
    s = _sig()
    s["setup_type"] = "structural"
    s["retest_armed"] = True
    ok, _, _ = RP._retest_confirmed(s, _a15(price=100.6))
    assert ok is False
