"""Phase B6: paired, point-in-time feature discrimination (research only)."""
import argparse, json, math, statistics
from pathlib import Path
import pandas as pd
from research.build_runner_dataset_v2 import klines, idx_at

FEATURES=("ret_3h","ret_6h","ret_24h","btc_relative_6h","volume_ratio_6h","range_pct_24h","compression_ratio")

def features(d,i,btc=None,bi=None):
    if i is None or i<72:return None
    c=d["close"]; v=d["quoteVolume"]; hi=d["high"];lo=d["low"]
    price=float(c.iloc[i])
    if price<=0:return None
    def ret(n):
        x=float(c.iloc[i-n]);return (price/x-1)*100 if x>0 else None
    recent=float(v.iloc[i-5:i+1].mean())
    previous=float(v.iloc[i-29:i-5].mean())
    r24=(float(hi.iloc[i-23:i+1].max())-float(lo.iloc[i-23:i+1].min()))/price*100
    rprev=(float(hi.iloc[i-71:i-23].max())-float(lo.iloc[i-71:i-23].min()))/price*100
    btc6=None
    if btc is not None and bi is not None and bi>=6:
        a=float(btc["close"].iloc[bi-6]);b=float(btc["close"].iloc[bi])
        if a>0:btc6=(b/a-1)*100
    r6=ret(6)
    return {"ret_3h":ret(3),"ret_6h":r6,"ret_24h":ret(24),
        "btc_relative_6h":r6-btc6 if btc6 is not None and r6 is not None else None,
        "volume_ratio_6h":recent/previous if previous>0 else None,
        "range_pct_24h":r24,"compression_ratio":r24/rprev if rprev>0 else None}

def summarize(rows):
    # One equal-weight comparison per opportunity; controls averaged within it.
    by={}
    for r in rows:by.setdefault(r["opportunity_id"],[]).append(r)
    output={}
    for feature in FEATURES:
        pairs=[]
        for group in by.values():
            values=[(x["winner_features"].get(feature),x["control_features"].get(feature)) for x in group]
            values=[(a,b) for a,b in values if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
            if values:pairs.append((values[0][0],statistics.mean(b for _,b in values)))
        diff=[a-b for a,b in pairs]
        output[feature]={"opportunities":len(pairs),
            "winner_median":statistics.median(a for a,b in pairs) if pairs else None,
            "control_median":statistics.median(b for a,b in pairs) if pairs else None,
            "paired_median_difference":statistics.median(diff) if diff else None,
            "winner_higher_fraction":sum(x>0 for x in diff)/len(diff) if diff else None}
    return output

def run(source,output):
    raw=json.loads(Path(source).read_text());pairs=raw["pairs"]
    times=[pd.Timestamp(x["anchor_ts"]) for x in pairs]
    lo=min(times)-pd.Timedelta(days=5);hi=max(times)+pd.Timedelta(days=1)
    symbols=sorted({x["symbol"] for x in pairs}|{x["control_symbol"] for x in pairs}|{"BTCUSDT"})
    frames={};missing=[]
    for n,s in enumerate(symbols,1):
        d=klines(s,"1h",int(lo.timestamp()*1000),int(hi.timestamp()*1000))
        if d.empty:missing.append(s)
        else:frames[s]=d
        if n%50==0:print("history",n,len(symbols),flush=True)
    btc=frames.get("BTCUSDT");out=[]
    for p in pairs:
        a=frames.get(p["symbol"]);b=frames.get(p["control_symbol"])
        if a is None or b is None:continue
        ts=pd.Timestamp(p["anchor_ts"]); ai=idx_at(a,ts);bi=idx_at(b,ts)
        btci=idx_at(btc,ts) if btc is not None else None
        af=features(a,ai,btc,btci);bf=features(b,bi,btc,btci)
        if af is None or bf is None:continue
        out.append({"opportunity_id":p["opportunity_id"],"symbol":p["symbol"],
            "control_symbol":p["control_symbol"],"anchor_ts":p["anchor_ts"],
            "winner_features":af,"control_features":bf})
    result={"meta":{"source_pairs":len(pairs),"feature_pairs":len(out),
        "unique_opportunities":len({x["opportunity_id"] for x in out}),
        "symbols_loaded":len(frames),"missing_symbols":missing,
        "limitations":"exploratory matched historical features; no OOS or executable profitability claim",
        "anti_lookahead":"only closed candles at or before anchor; outcome labels never used as features"},
        "comparison":summarize(out),"pairs":out}
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({k:v for k,v in result.items() if k!="pairs"}),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();run(a.source,a.output)
