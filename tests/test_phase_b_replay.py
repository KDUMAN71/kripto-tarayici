from research.phase_b_replay import select_cohort


def _o(i,v,side="LONG"):
    return {"opportunity_id":str(i),"symbol":f"X{i}","side":side,
            "start_ts":f"2026-08-{(i%28)+1:02d}T00:00:00+00:00","max_excursion_pct":v}


def test_all_100pct_plus_opportunities_are_preserved():
    xs=[_o(1,220),_o(2,150),_o(3,80),_o(4,30)]
    out=select_cohort(xs,mid_cap=1)
    ids={x["opportunity_id"] for x in out}
    assert {"1","2"} <= ids


def test_mid_cohort_is_bounded():
    xs=[_o(i,50+i%40,"SHORT" if i%3==0 else "LONG") for i in range(50)]
    out=select_cohort(xs,mid_cap=10,short_cap=5)
    assert len(out)<=10
