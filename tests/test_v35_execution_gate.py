from scanner.engine_v3 import _execution_geometry, _geometry_at, _geometry_feasible


def _cand(stage="ACTIVE", trigger=100.0, sl=99.0, tp1=102.0, tp2=103.0):
    return {"stage": stage, "side": "long", "trigger": trigger,
            "pattern": {"type": "breakout_retest", "note": ""},
            "plan": {"entry": trigger, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": None,
                     "risk_pct": abs(trigger-sl)/trigger*100,
                     "rr1": abs(tp1-trigger)/abs(trigger-sl),
                     "rr2": abs(tp2-trigger)/abs(trigger-sl), "rr3": None}}


def test_geometry_requires_tp1_and_tp2_not_only_tp1():
    g = _geometry_at(100.0, {"sl": 99.0, "tp1": 101.6, "tp2": 101.9, "tp3": None})
    assert g["rr1"] >= 1.5
    assert g["rr2"] < 2.0
    assert _geometry_feasible(g) is False


def test_active_bad_live_geometry_downgrades_to_retest_when_trigger_is_valid():
    c = _cand(trigger=100.0, sl=99.0, tp1=102.0, tp2=103.0)
    out = _execution_geometry("long", c, 100.5, {}, 1.0)
    assert out["decision"] == "RETEST_WAIT"
    assert out["candidate"]["stage"] == "WATCH"
    assert out["candidate"]["retest"] is True


def test_candidate_rejected_when_live_and_trigger_geometry_both_fail():
    c = _cand(trigger=100.0, sl=98.0, tp1=102.0, tp2=103.0)
    out = _execution_geometry("long", c, 101.0, {}, 1.0)
    assert out["decision"] == "REJECT"


def test_hbar_style_support_adjustment_cannot_leave_stale_rr():
    c = _cand(trigger=0.1028, sl=0.1017, tp1=0.1055, tp2=0.1071)
    zones = {"support": {"level": 0.101535, "members": [0.10150, 0.10157]}}
    out = _execution_geometry("long", c, 0.1031, zones, 0.001)
    assert out["candidate"]["plan"]["sl"] < 0.10150
    g = out.get("geometry")
    assert g is not None
    risk = abs(g["entry"] - out["candidate"]["plan"]["sl"])
    assert abs(g["rr1"] - abs(0.1055-g["entry"])/risk) < 1e-9


def test_forming_candidate_never_promoted_by_geometry_gate():
    c = _cand(stage="WATCH", trigger=100.0, sl=99.0, tp1=102.0, tp2=103.0)
    out = _execution_geometry("long", c, 100.2, {}, 1.0)
    assert out["decision"] == "PASS"
    assert out["candidate"]["stage"] == "WATCH"
