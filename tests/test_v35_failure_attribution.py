from research.failure_attribution import classify_episode, attribute_ledger
import scanner.outcomes as OUT


def test_stop_with_large_post_entry_mfe_is_premature_stop():
    d = classify_episode({"outcome": "STOPPED", "mfe_pct": 4.2, "mae_pct": 2.0})
    assert d["class"] == "PREMATURE_STOP"


def test_normal_stopped_trade_is_valid_loss():
    assert classify_episode({"outcome": "STOPPED", "mfe_pct": 0.8})["class"] == "VALID_LOSS"


def test_missed_entry_is_late_detection():
    assert classify_episode({"outcome": "MISSED", "close_reason": "entry ran beyond allowed distance"})["class"] == "LATE_DETECTION"


def test_runner_after_geometry_reject_is_bad_rr():
    e = {"outcome": "REJECTED", "close_reason": "structural geometry minimum risk/R:R",
         "mfe_pct": 12}
    assert classify_episode(e)["class"] == "BAD_RR"


def test_runner_after_generic_reject_is_missed_runner():
    e = {"outcome": "REJECTED", "close_reason": "score below threshold", "mfe_pct": 15}
    assert classify_episode(e)["class"] == "MISSED_RUNNER"


def test_explicit_hbar_style_label_is_correct_thesis_bad_execution():
    e = {"status": "HISTORICAL", "initial_features": {"thesis_correct": True, "execution_bad": True}}
    assert classify_episode(e)["class"] == "CORRECT_THESIS_BAD_EXECUTION"


def test_summary_counts_classes():
    ledger = {"episodes": [
        {"candidate_id": "a", "symbol": "A", "outcome": "STOPPED", "mfe_pct": 0},
        {"candidate_id": "b", "symbol": "B", "outcome": "MISSED"},
    ]}
    out = attribute_ledger(ledger)
    assert out["total"] == 2
    assert out["counts"]["VALID_LOSS"] == 1
    assert out["counts"]["LATE_DETECTION"] == 1


def test_rejected_candidate_gets_future_evaluation_mfe(monkeypatch):
    monkeypatch.setattr(OUT, "_L", {"episodes": [{
        "candidate_id": "x", "symbol": "XUSDT", "status": "REJECTED",
        "closed_at": 100, "initial_features": {"price": 10.0},
        "mfe_pct": 0.0, "mae_pct": 0.0, "events": []
    }]})
    OUT.update_evaluation_prices({"XUSDT": 11.2}, ts=200)
    assert round(OUT._L["episodes"][0]["mfe_pct"], 1) == 12.0


def test_evaluation_horizon_prevents_indefinite_future_leakage(monkeypatch):
    monkeypatch.setattr(OUT, "_L", {"episodes": [{
        "candidate_id": "x", "symbol": "XUSDT", "status": "REJECTED",
        "closed_at": 100, "initial_features": {"price": 10.0},
        "mfe_pct": 0.0, "mae_pct": 0.0, "events": []
    }]})
    OUT.update_evaluation_prices({"XUSDT": 20.0}, ts=101 + OUT.EVAL_HORIZON_H * 3600)
    assert OUT._L["episodes"][0]["mfe_pct"] == 0.0


def test_failed_breakout_trade_is_false_breakout_not_missed_runner():
    e = {"outcome": "STOPPED", "setup_type": "breakout_retest", "mfe_pct": 0.5, "mae_pct": 2.0}
    assert classify_episode(e)["class"] == "FALSE_BREAKOUT"
