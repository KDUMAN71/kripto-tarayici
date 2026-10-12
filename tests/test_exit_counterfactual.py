import pandas as pd
from research.exit_counterfactual import replay


def candles(rows):
    times=pd.date_range("2026-01-01",periods=len(rows),freq="h",tz="UTC")
    return pd.DataFrame({"openTime":times,"high":[x[0] for x in rows],"low":[x[1] for x in rows]})


def trade():
    return {"side":"LONG","entry":100,"sl":99,"tp1":102,"tp2":104,"tp3":106,
            "activated_at":int(pd.Timestamp("2026-01-01",tz="UTC").timestamp()),
            "closed_at":int(pd.Timestamp("2026-01-02",tz="UTC").timestamp())}


def test_full_tp1_exit_is_not_held_to_tp3():
    d=candles([(100.5,99.5),(102.5,100.0),(107,103)])
    result=replay(trade(),d,1)
    assert result["exit"]=="TP1"
    assert result["r"]==2


def test_partial_tp1_then_final_target():
    d=candles([(100.5,99.5),(102.5,100.0),(106.5,103)])
    result=replay(trade(),d,.25)
    assert result["exit"]=="FINAL_TP"
    assert result["r"]==5


def test_same_candle_stop_has_priority():
    d=candles([(102.5,98.5)])
    assert replay(trade(),d,1)["exit"]=="SL"
