import pandas as pd
from research.independent_controls import matched_controls


def frame(start,base,volume=100):
    times=pd.date_range(start,periods=220,freq="h",tz="UTC")
    return pd.DataFrame({"closeTime":times,"close":[base]*220,
        "high":[base]*220,"low":[base]*220,"quoteVolume":[volume]*220})


def test_matched_control_same_time_and_no_future_move():
    a=frame("2026-01-01",100)
    b=frame("2026-01-01",10)
    opp={"opportunity_id":"a","symbol":"A","side":"LONG",
         "start_ts":a.iloc[30]["closeTime"].isoformat()}
    out=matched_controls(opp,{"A":a,"B":b},horizon_hours=24)
    assert len(out)==1
    assert out[0]["control_symbol"]=="B"


def test_immature_negative_cannot_be_used():
    a=frame("2026-01-01",100)
    b=frame("2026-01-01",10).iloc[:35].copy()
    opp={"opportunity_id":"a","symbol":"A","side":"LONG",
         "start_ts":a.iloc[30]["closeTime"].isoformat()}
    assert matched_controls(opp,{"A":a,"B":b},horizon_hours=24)==[]


def test_future_runner_is_not_negative_control():
    a=frame("2026-01-01",100)
    b=frame("2026-01-01",10)
    b.loc[35,"high"]=20
    opp={"opportunity_id":"a","symbol":"A","side":"LONG",
         "start_ts":a.iloc[30]["closeTime"].isoformat()}
    assert matched_controls(opp,{"A":a,"B":b},horizon_hours=24,threshold_pct=25)==[]
