from scanner.engine_v3 import _apply_htf_thesis_sl, _pretrade_feasible


def _plan(entry=0.10309, sl=0.101668, tp1=0.10546, tp2=0.10710):
    risk = abs(entry - sl)
    return {
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": 0.1100,
        "risk_pct": risk / entry * 100,
        "rr1": abs(tp1-entry)/risk, "rr2": abs(tp2-entry)/risk,
        "rr3": abs(0.1100-entry)/risk,
    }


def test_hbar_long_stop_must_be_below_support_zone_with_buffer():
    plan = _plan()
    zones = {
        "support": {"level": 0.101535, "members": [0.10150, 0.10157], "evidence": 2},
        "resistance": {"level": 0.1310, "members": [0.1310], "evidence": 2},
    }
    adjusted, changed = _apply_htf_thesis_sl("long", plan, 0.10309, zones, 0.0010)
    assert changed is True
    assert adjusted["sl"] < min(zones["support"]["members"])
    assert adjusted["sl"] < plan["sl"]
    assert adjusted["rr1"] < plan["rr1"]


def test_short_stop_must_be_above_resistance_zone_with_buffer():
    plan = _plan(entry=100.0, sl=101.0, tp1=98.0, tp2=96.0)
    zones = {"resistance": {"level": 101.2, "members": [101.1, 101.3], "evidence": 3}}
    adjusted, changed = _apply_htf_thesis_sl("short", plan, 100.0, zones, 1.0)
    assert changed is True
    assert adjusted["sl"] > max(zones["resistance"]["members"])
    assert adjusted["rr1"] < plan["rr1"]


def test_distant_htf_zone_does_not_widen_execution_stop():
    plan = _plan()
    zones = {"support": {"level": 0.0900, "members": [0.0895, 0.0905], "evidence": 3}}
    adjusted, changed = _apply_htf_thesis_sl("long", plan, 0.10309, zones, 0.0010)
    assert changed is False
    assert adjusted["sl"] == plan["sl"]


def test_rr_is_recomputed_after_structural_stop_widens():
    plan = _plan(entry=100.0, sl=99.0, tp1=101.6, tp2=103.0)
    zones = {"support": {"level": 99.0, "members": [98.8, 99.2], "evidence": 3}}
    adjusted, changed = _apply_htf_thesis_sl("long", plan, 100.0, zones, 1.0)
    assert changed is True
    assert adjusted["rr1"] < 1.5
    assert _pretrade_feasible(adjusted) is False


def test_structural_stop_recompute_can_fail_tp2_even_if_tp1_looks_ok():
    plan = _plan(entry=100.0, sl=99.0, tp1=103.0, tp2=103.5)
    zones = {"support": {"level": 99.0, "members": [98.8, 99.2], "evidence": 3}}
    adjusted, changed = _apply_htf_thesis_sl("long", plan, 100.0, zones, 1.0)
    assert changed is True
    assert adjusted["rr1"] >= 1.5
    assert adjusted["rr2"] < 2.0
    assert _pretrade_feasible(adjusted) is False
