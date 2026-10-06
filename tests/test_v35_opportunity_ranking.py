import pandas as pd
from scanner.opportunity import opportunity_score, rank_candidates, return_pct


def _closed(vals):
    return pd.DataFrame({"close": vals})


def test_return_pct_uses_closed_history_only():
    c = _closed([100, 101, 102, 103, 104, 105, 106])
    assert round(return_pct(c, 3), 4) == round((106/103-1)*100, 4)


def test_runner_like_trajectory_ranks_above_flat_control():
    runner = {"ret_3h": 3.4, "ret_6h": 6.6, "rel_btc_3h": 3.5,
              "rel_btc_6h": 5.0, "vol_ratio_1h": 1.21}
    control = {"ret_3h": 0.6, "ret_6h": 1.5, "rel_btc_3h": 0.5,
               "rel_btc_6h": 1.0, "vol_ratio_1h": 0.96}
    assert opportunity_score(runner) > opportunity_score(control)


def test_ranking_is_direction_agnostic_at_discovery_stage():
    up = {"ret_3h": 3, "ret_6h": 6, "rel_btc_3h": 2, "rel_btc_6h": 4, "vol_ratio_1h": 1.2}
    down = {"ret_3h": -3, "ret_6h": -6, "rel_btc_3h": -2, "rel_btc_6h": -4, "vol_ratio_1h": 1.2}
    assert opportunity_score(up) == opportunity_score(down)


def test_score_is_bounded_against_extreme_movers():
    extreme = {"ret_3h": 100, "ret_6h": 200, "rel_btc_3h": 100,
               "rel_btc_6h": 200, "vol_ratio_1h": 20}
    assert opportunity_score(extreme) <= 9.0


def test_rank_uses_score_before_raw_liquidity():
    rows = [
        {"symbol": "BIGUSDT", "opportunity_score": 1.0, "quote_volume_24h": 100_000_000},
        {"symbol": "METISUSDT", "opportunity_score": 5.0, "quote_volume_24h": 3_000_000},
    ]
    assert rank_candidates(rows)[0]["symbol"] == "METISUSDT"
