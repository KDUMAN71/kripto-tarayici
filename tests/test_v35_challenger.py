from research.challenger import evaluate_policy, compare


def _e(sym, score, mfe, **f):
    return {"symbol": sym, "mfe_pct": mfe, "closed_at": 1,
            "initial_features": {"price": 1, "opportunity_score": score, **f}}


def test_policy_metrics_measure_runner_recall_and_precision():
    eps = [_e("A", 9, 15), _e("B", 8, 1), _e("C", 1, 12), _e("D", 0, 0)]
    import research.challenger as CH
    CH.MIN_MATURE_EPISODES = 1
    out = evaluate_policy(eps, lambda e: e["initial_features"]["opportunity_score"], top_fraction=.5, now_ts=100000)
    assert out["runner_count"] == 2
    assert out["runner_recall"] == .5
    assert out["precision"] == .5


def test_challenger_can_beat_current_without_mutating_anything():
    eps = [
        _e("RUN", 1, 15, ret_3h=3.5, ret_6h=7, rel_btc_3h=3, rel_btc_6h=5, vol_ratio_1h=1.3),
        _e("FLAT", 9, 0, ret_3h=.1, ret_6h=.2, rel_btc_3h=.1, rel_btc_6h=.1, vol_ratio_1h=.8),
        _e("X", 0, 0), _e("Y", 0, 0),
    ]
    import research.challenger as CH
    CH.MIN_MATURE_EPISODES = 1
    out = compare({"episodes": eps}, top_fraction=.25, now_ts=100000)
    assert out["trajectory_balanced"]["runner_recall"] > out["current"]["runner_recall"]


def test_empty_ledger_is_safe():
    out = compare({"episodes": []}, now_ts=100000)
    assert out["current"]["n"] == 0
    assert out["trajectory_balanced"]["runner_recall"] is None


def test_immature_episode_is_excluded_from_challenger():
    import research.challenger as CH
    CH.MIN_MATURE_EPISODES = 1
    e = _e("YOUNG", 9, 15)
    e["closed_at"] = 99_000
    out = compare({"episodes": [e]}, now_ts=100_000)
    assert out["current"]["n"] == 0
    assert out["current"]["status"] == "INSUFFICIENT_MATURE_DATA"
