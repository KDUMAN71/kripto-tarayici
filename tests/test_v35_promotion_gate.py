import research.promotion as P


def _e(i, score, mfe, days_ago, **f):
    now = 10_000_000
    return {"symbol": f"X{i}", "mfe_pct": mfe, "closed_at": now-days_ago*86400,
            "initial_features": {"price": 1, "opportunity_score": score, **f}}


def test_small_sample_is_blocked(monkeypatch):
    monkeypatch.setattr(P, "MIN_CALIBRATION", 2)
    monkeypatch.setattr(P, "MIN_OOS", 2)
    out = P.promotion_gate({"episodes": []}, now_ts=10_000_000)
    assert out["status"] == "BLOCKED"


def test_gate_never_automatically_promotes(monkeypatch):
    monkeypatch.setattr(P, "MIN_CALIBRATION", 2)
    monkeypatch.setattr(P, "MIN_OOS", 2)
    import research.challenger as CH
    monkeypatch.setattr(CH, "MIN_MATURE_EPISODES", 1)
    # calibration older than 30d; OOS recent. Challenger ranks runners first.
    eps = [
        _e(1, 1, 15, 60, ret_3h=4, ret_6h=7, rel_btc_3h=3, rel_btc_6h=5, vol_ratio_1h=1.3),
        _e(2, 9, 0, 50),
        _e(3, 1, 15, 20, ret_3h=4, ret_6h=7, rel_btc_3h=3, rel_btc_6h=5, vol_ratio_1h=1.3),
        _e(4, 9, 0, 10),
    ]
    out = P.promotion_gate({"episodes": eps}, now_ts=10_000_000)
    assert out.get("automatic_promotion") is False
    if out.get("status") == "ELIGIBLE_FOR_REVIEW":
        assert out["requires_time_slice_replay_before_production"] is True


def test_invalid_challenger_is_blocked():
    assert P.promotion_gate({"episodes": []}, challenger="current")["status"] == "BLOCKED"
