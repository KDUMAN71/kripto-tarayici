from research.missed_opportunity import summarize_gate_trace


def test_metis_like_case_identifies_liquidity_as_dominant_gate():
    a = {"symbols": {"METISUSDT": [
        {"stage": "liquidity", "reason": "24s hacim 8M$ tabaninin altinda", "n": 18,
         "x": {"qv_musd": 3}},
    ]}}
    out = summarize_gate_trace("METISUSDT", a)
    assert out["observed"] is True
    assert out["dominant_gate"]["stage"] == "liquidity"
    assert out["dominant_gate"]["count"] == 18


def test_recall_like_missing_trace_is_observability_failure():
    out = summarize_gate_trace("RECALLUSDT", {"symbols": {}})
    assert out["observed"] is False
    assert out["diagnosis"] == "NO_TRACE"
    assert out["dominant_gate"] is None
