"""B7: winner/control pre-anchor feature trajectories, research only."""
import argparse,json,statistics
from pathlib import Path
import pandas as pd
from research.build_runner_dataset_v2 import klines,idx_at
from research.phase_b6_features import features,FEATURES

OFFSETS_H=(-168,-72,-24,-12,-6,-3,-1,0)

def build(source,output):
    raw=json.loads(Path(source).read_text());pairs=raw["pairs"]
    symbols=sorted({p["symbol"] for p in pairs}|{p["control_symbol"] for p in pairs}|{"BTCUSDT"})
    stamps=[pd.Timestamp(p["anchor_ts"]) for p in pairs]
    start=min(stamps)-pd.Timedelta(days=13);end=max(stamps)+pd.Timedelta(days=1)
    frames={}
    for n,s in enumerate(symbols,1):
        d=klines(s,"1h",int(start.timestamp()*1000),int(end.timestamp()*1000))
        if not d.empty:frames[s]=d
        if n%50==0:print("loaded",n,len(symbols),flush=True)
    btc=frames.get("BTCUSDT")
    grouped={}
    for p in pairs:
        a=frames.get(p["symbol"]);b=frames.get(p["control_symbol"])
        if a is None or b is None:continue
        for offset in OFFSETS_H:
            t=pd.Timestamp(p["anchor_ts"])+pd.Timedelta(hours=offset)
            ai=idx_at(a,t);bi=idx_at(b,t);ci=idx_at(btc,t) if btc is not None else None
            af=features(a,ai,btc,ci);bf=features(b,bi,btc,ci)
            if af is None or bf is None:continue
            grouped.setdefault((p["opportunity_id"],offset),[]).append((af,bf))
    timeline=[]
    for offset in OFFSETS_H:
        row={"offset_hours":offset,"features":{}}
        for k in FEATURES:
            diffs=[];ws=[];cs=[]
            for (eid,h),values in grouped.items():
                if h!=offset:continue
                valid=[(a[k],b[k]) for a,b in values if a.get(k) is not None and b.get(k) is not None]
                if not valid:continue
                w=valid[0][0];c=statistics.mean(v for _,v in valid)
                ws.append(w);cs.append(c);diffs.append(w-c)
            row["features"][k]={"n":len(diffs),
                "winner_median":statistics.median(ws) if ws else None,
                "control_median":statistics.median(cs) if cs else None,
                "paired_median_difference":statistics.median(diffs) if diffs else None,
                "winner_higher_fraction":sum(v>0 for v in diffs)/len(diffs) if diffs else None}
        timeline.append(row)
    result={"meta":{"source_pairs":len(pairs),"symbols_loaded":len(frames),
        "offsets_hours":OFFSETS_H,"scope":"exploratory; no OOS and no trade profitability claim",
        "warning":"anchor may be late; point-in-time closed candles only"},
        "timeline":timeline}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2))
    print("TIMELINE_SUMMARY",json.dumps(result),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();build(a.source,a.output)
