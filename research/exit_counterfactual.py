"""Conservative historical exit policy counterfactuals, research only.

A 1h candle hitting both TP and SL is treated as SL-first. Not an exchange fill.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from research.build_runner_dataset_v2 import klines

def replay(t,d,partial_fraction=0.0,fee_r=0.0):
    side=t["side"].upper();long=side=="LONG"
    entry=float(t["entry"]);sl=float(t["sl"]);tp=float(t["tp1"])
    risk=abs(entry-sl)
    if risk<=0:return None
    start=pd.Timestamp(int(t["activated_at"]),unit="s",tz="UTC")
    end=pd.Timestamp(int(t["closed_at"]),unit="s",tz="UTC")+pd.Timedelta(days=7)
    candles=d[(d["openTime"]>=start)&(d["openTime"]<=end)]
    touched=False;partial=0.0
    for _,row in candles.iterrows():
        hi=float(row["high"]);lo=float(row["low"])
        stop=(lo<=sl if long else hi>=sl)
        hit=(hi>=tp if long else lo<=tp)
        if stop:
            return {"r":partial+(-1)*(1-partial_fraction if touched else 1)-fee_r,
                    "tp1_touched":touched,"exit":"SL"}
        if hit and not touched:
            touched=True;partial=partial_fraction*abs(tp-entry)/risk
            if partial_fraction==1:return {"r":partial-fee_r,"tp1_touched":True,"exit":"TP1"}
    return {"r":None,"tp1_touched":touched,"exit":"OPEN_OR_CENSORED"}

def run(source,output):
    st=json.loads(Path(source).read_text());trades=[x for x in st.get("trades",[]) if x.get("activated_at") and x.get("closed_at") and x.get("tp1")]
    results=[]
    for t in trades:
        start=int(t["activated_at"])-3600;end=int(t["closed_at"])+8*86400
        d=klines(t["symbol"],"1h",start*1000,end*1000)
        if d.empty:continue
        results.append({"symbol":t["symbol"],"side":t["side"],"historical_outcome":t["outcome"],
            "hold_full":replay(t,d,0),"tp1_25pct":replay(t,d,.25),
            "tp1_50pct":replay(t,d,.5),"tp1_full":replay(t,d,1)})
    summary={}
    for k in ("hold_full","tp1_25pct","tp1_50pct","tp1_full"):
        xs=[r[k]["r"] for r in results if r[k] and r[k]["r"] is not None]
        summary[k]={"completed":len(xs),"net_r":sum(xs),"expectancy_r":sum(xs)/len(xs) if xs else None}
    out={"meta":{"trade_count":len(trades),"evaluated":len(results),
        "warning":"research-only OHLC counterfactual; stop-first same candle; no fills/fees by default; reentry not modeled"},
        "summary":summary,"trades":results}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2))
    print("EXIT_COUNTERFACTUAL",json.dumps({"meta":out["meta"],"summary":summary}),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();run(a.source,a.output)
