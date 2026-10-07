import pandas as pd
from research.opportunity_census import forward_excursion, _bin, UP_BINS, DOWN_BINS


def _df():
    return pd.DataFrame({"close":[100,100,100],"high":[100,160,310],"low":[100,80,20]})


def test_forward_excursion_labels_large_up_and_down_moves():
    x=forward_excursion(_df(),0,2)
    assert round(x["up_pct"]) == 210
    assert round(x["down_pct"]) == 80
    assert x["up_bin"] == "GT_200"
    assert x["down_bin"] == "DOWN_GT_70"


def test_bins_preserve_smaller_profitable_opportunities():
    assert _bin(12,UP_BINS) == "10_25"
    assert _bin(30,UP_BINS) == "25_50"
    assert _bin(55,UP_BINS) == "50_100"
    assert _bin(120,UP_BINS) == "100_200"
    assert _bin(12,DOWN_BINS) == "DOWN_10_25"
