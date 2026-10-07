from research.opportunity_replay import dedupe, canonicalize


def _e(day,pct):
    return {"symbol":"XUSDT","anchor_ts":f"2026-08-{day:02d}T00:00:00+00:00",
            "anchor_price":1.0,"7d":{"mature":True,"up_pct":pct,"up_bin":"50_100",
                                   "down_pct":0,"down_bin":None}}


def test_overlapping_daily_anchors_become_one_episode():
    out=dedupe([_e(1,50),_e(2,80),_e(3,60)],"7d","LONG",25,cooldown_days=3)
    assert len(out)==1
    assert out[0]["episode_start"].startswith("2026-08-01")
    assert out[0]["max_excursion_pct"]==80
    assert out[0]["anchor_count"]==3


def test_separated_opportunities_remain_distinct():
    out=dedupe([_e(1,50),_e(10,70)],"7d","LONG",25,cooldown_days=3)
    assert len(out)==2


def test_same_move_across_horizons_becomes_one_canonical_opportunity():
    base={"symbol":"XUSDT","side":"LONG","episode_end":"2026-08-03T00:00:00+00:00",
          "anchor_price":1.0,"anchor_count":2,"magnitude_bin":"100_200"}
    rows=[
        {**base,"horizon":"7d","episode_start":"2026-08-01T00:00:00+00:00","max_excursion_pct":120},
        {**base,"horizon":"14d","episode_start":"2026-08-02T00:00:00+00:00","max_excursion_pct":180},
    ]
    out=canonicalize(rows)
    assert len(out)==1
    assert out[0]["max_excursion_pct"]==180
    assert len(out[0]["views"])==2
