"""Phase C: post-stop continuation audit from closed 1h candles.

Research-only. A post-stop recovery is NOT automatically a bad stop:
structural thesis invalidation and realistic re-entry must be evaluated separately.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from research.build_runner_dataset_v2 import klines

HORIZONS={"1h":1,"3h":3,"6h":6,"12h":12,"24h":24,"3d":72,"7d":168}

def analyze_trade(t,d):
    ts=pd.Timestamp(int(t["closed_at"]),unit="s",tz="UTC")
    entry=float(t["entry"]);stop=float(t["sl"]);side=str(t["side"]).upper()
    if entry<=0:return None
    # First candle strictly after the stop timestamp; conservative when intra-hour order unknown.
    future=d[d["openTime"]>ts]
    out={"symbol":t["symbol"],"side":side,"closed_at":ts.isoformat(),
         "entry":entry,"sl":stop,"outcome":t["outcome"],"pre_stop_mfe_pct":t.get("mfe_pct"),
         "post_stop":{}}
    for label,h in HORIZONS.items():
        w=future.iloc[:h]
        if len(w)<h:
            out["post_stop"][label]={"mature":False};continue
        hi=float(w.high.max());lo=float(w.low.min())
        favorable=(hi/entry-1)*100 if side=="LONG" else (1-lo/entry)*100
        adverse=(1-lo/entry)*100 if side=="LONG" else (hi/entry-1)*100
        out["post_stop"][label]={"mature":True,"favorable_from_entry_pct":favorable,
            "adverse_from_entry_pct":adverse,"recovered_entry":hi>=entry if side=="LONG" else lo<=entry,
            "reached_tp1":hi>=float(t["tp1"]) if side=="LONG" else lo<=float(t["tp1"])}
    return out

def run(source,output):
    state=json.loads(Path(source).read_text());trades=[t for t in state.get("trades",[]) if t.get("outcome")=="STOPPED"]
    results=[]
    for t in trades:
        ts=int(t["closed_at"])
        start=ts-3600*3;end=ts+3600*24*8
        d=klines(t["symbol"],"1h",start*1000,end*1000)
        if d.empty:results.append({"symbol":t["symbol"],"error":"missing historical candles"});continue
        x=analyze_trade(t,d)
        if x:results.append(x)
    summary={}
    for label in HORIZONS:
        mature=[r["post_stop"][label] for r in results if "post_stop" in r and r["post_stop"][label].get("mature")]
        summary[label]={"mature_stops":len(mature),"recovered_entry":sum(x["recovered_entry"] for x in mature),
                        "reached_tp1":sum(x["reached_tp1"] for x in mature)}
    output_data={"meta":{"stops":len(trades),"scope":"research-only; post-stop continuation not sufficient to prove stop invalidity",
        "candle_order_limit":"1h candles cannot establish intrabar TP/SL ordering"},"summary":summary,"trades":results}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output_data,indent=2))
    print("POST_STOP_SUMMARY",json.dumps({"meta":output_data["meta"],"summary":summary}),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();run(a.source,a.output)
