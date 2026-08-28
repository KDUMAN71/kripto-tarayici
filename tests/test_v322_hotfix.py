import pandas as pd

from scanner.engine import _targets
from scanner.engine_v3 import (_candidate_from_pattern, _pattern_levels,
                               _pretrade_feasible)
from scanner.main import active_msg, pretrade_msg
from scanner.state import update_active


def _levels_analysis(*, atr=1.0, highs=None, lows=None, price=100.0,
                     tscore=1, stretch=0.0):
    return {
        "atr": atr,
        "pivot_highs": highs or [],
        "pivot_lows": lows or [],
        "price": price,
        "tscore": tscore,
        "stretch": stretch,
    }


def test_avax_like_long_targets_are_strictly_progressive():
    tp1, tp2, tp3 = _targets(
        "long", 100.0, 2.0, [104.0, 104.0, 108.0], [], [])

    assert (tp1, tp2, tp3) == (104.0, 108.0, None)
    assert tp1 < tp2


def test_xpl_like_short_does_not_repeat_tp2_as_tp3():
    tp1, tp2, tp3 = _targets(
        "short", 100.0, 5.0, [90.0, 85.0, 85.0], [], [])

    assert (tp1, tp2, tp3) == (90.0, 85.0, None)
    assert tp1 > tp2


def test_pattern_invalidation_over_three_percent_is_rejected_without_fallback():
    pattern = {
        "type": "flag", "dir": "long", "trigger": 100.0,
        "invalid": 96.0, "state": "forming", "quality": 1.0,
        "note": "test",
    }
    a15 = _levels_analysis(highs=[102.0, 106.0, 110.0])
    a1h = _levels_analysis(atr=1.0, highs=[104.0, 108.0, 112.0])
    a4h = _levels_analysis(highs=[114.0])

    plan, trigger = _pattern_levels("long", pattern, a15, a1h, a4h)

    assert trigger == 100.0
    assert plan is None


def test_early_watch_plan_over_three_percent_is_not_feasible():
    plan = {
        "risk_pct": 3.19, "rr2": 2.5,
        "tp1": 103.0, "tp2": 108.0, "tp3": None,
    }

    assert _pretrade_feasible(plan) is False

    pattern = {
        "type": "flag", "dir": "long", "trigger": 100.0,
        "invalid": 96.8, "state": "forming", "quality": 1.0,
        "note": "test",
    }
    a15 = _levels_analysis(price=98.5, highs=[104.0, 108.0, 112.0])
    a1h = _levels_analysis(atr=0.1, highs=[105.0, 109.0, 113.0])
    a4h = _levels_analysis(highs=[116.0])

    assert _candidate_from_pattern(pattern, a15, a1h, a4h) is None


def _telegram_signal(status):
    return {
        "status": status, "side": "LONG", "trigger": 100.0,
        "alarm": 99.65, "dist_pct": 0.8,
        "entry_lo": 99.8, "entry_hi": 100.4, "sl": 98.0,
        "risk_pct": 2.0, "tp1": 102.4, "tp2": 104.5, "tp3": None,
        "rr1": 1.2, "rr2": 2.25, "rr3": None,
        "setup_type": "flag", "score": 8, "score_max": 13,
        "oi": {}, "funding": 0.0, "score_parts": [],
    }


def test_tp3_none_telegram_uses_em_dash_without_exception():
    pretrade = pretrade_msg("TESTUSDT", _telegram_signal("WATCH"), "")
    active = active_msg("TESTUSDT", _telegram_signal("ACTIVE"), "")

    assert "TP3: —" in pretrade
    assert "R:R: 1.2 / 2.2 / —" in pretrade
    assert "TP3: —" in active
    assert "R:R: 1.2 / 2.2 / —" in active
    assert "HARD STOP" in active


class _Telegram:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)


def test_tp3_none_state_closes_at_tp2_without_duplicate_tp3_event():
    state = {
        "signals": {
            "TESTUSDT": {
                "status": "ACTIVE", "side": "LONG", "price": 100.0,
                "entry_ref": 100.0, "activated_at": 1, "last_update": 1,
                "sl": 90.0, "tp1": 110.0, "tp2": 120.0, "tp3": None,
                "final_tp": "tp2", "mfe_pct": 0, "mae_pct": 0,
            }
        },
        "log": [], "trades": [],
    }
    closed = pd.DataFrame({
        "high": [121.0] * 4, "low": [99.0] * 4, "close": [120.0] * 4,
    })
    analysis = {"price": 120.0, "closed": closed}
    telegram = _Telegram()

    update_active(state, "TESTUSDT", analysis, telegram)
    update_active(state, "TESTUSDT", analysis, telegram)

    signal = state["signals"]["TESTUSDT"]
    assert signal["status"] == "CLOSED"
    assert signal["tp1_hit"] is True and signal["tp2_hit"] is True
    assert "tp3_hit" not in signal
    assert [event["event"] for event in state["log"]] == ["TP1_HIT", "TP2_HIT"]
    assert len(state["trades"]) == 1
    assert state["trades"][0]["outcome"] == "TP2_HIT"
    assert state["trades"][0]["tp3"] is None


def test_negative_funding_warning_is_direction_aware():
    signal = _telegram_signal("ACTIVE")
    signal["funding"] = -0.001

    message = active_msg("TESTUSDT", signal, "")

    assert "short tarafı kalabalık" in message
    assert "satıcı baskın" not in message
