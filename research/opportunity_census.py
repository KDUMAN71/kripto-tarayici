"""Phase A: 60-day comprehensive opportunity census.

Labels opportunity magnitude/direction across multiple forward horizons.
Research labels may use future candles; no live scanner feature consumes this file.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from scanner import data
from research.build_runner_dataset_v2 import klines

HORIZONS_H = {"6h":6,"1d":24,"3d":72,"7d":168,"14d":336,"30d":720,"60d":1440}
UP_BINS = [(200,"GT_200"),(100,"100_200"),(50,"50_100"),(25,"25_50"),(10,"10_25")]
DOWN_BINS = [(70,"DOWN_GT_70"),(50,"DOWN_50_70"),(25,"DOWN_25_50"),(10,"DOWN_10_25")]


def _bin(v, bins):
    for threshold, name in bins:
        if v >= threshold: return name
    return None


def forward_excursion(d, i, bars):
    f=d.iloc[i+1:min(len(d),i+1+bars)]
    if f.empty: return None
    entry=float(d.iloc[i].close)
    up=(float(f.high.max())/entry-1)*100
    down=(1-float(f.low.min())/entry)*100
    return {"up_pct":up,"down_pct":down,
            "up_bin":_bin(up,UP_BINS),"down_bin":_bin(down,DOWN_BINS),
            "available_bars":len(f),"requested_bars":bars,"mature":len(f)>=bars}


def census_symbol(symbol,d):
    rows=[]
    # Daily anchors avoid pretending every hourly candle is an independent opportunity.
    for i in range(24,len(d),24):
        row={"symbol":symbol,"anchor_ts":d.iloc[i].closeTime.isoformat(),
             "anchor_price":float(d.iloc[i].close),
             "quote_volume_1h":float(d.iloc[i].quoteVolume or 0)}
        any_opp=False
        for name,bars in HORIZONS_H.items():
            x=forward_excursion(d,i,bars)
            row[name]=x
            if x and (x["up_bin"] or x["down_bin"]): any_opp=True
        if any_opp: rows.append(row)
    return rows


def build(days=60,max_symbols=None):
    now=pd.Timestamp.now(tz="UTC").floor("h")
    # Need full forward 60d only for older anchors; recent anchors naturally have shorter available horizons.
    start=now-pd.Timedelta(days=days+2)
    syms=data.exchange_perp_symbols() or []
    if max_symbols: syms=syms[:max_symbols]
    events=[]; failures=[]
    for n,s in enumerate(syms,1):
        d=klines(s,"1h",int(start.timestamp()*1000),int(now.timestamp()*1000))
        if d.empty: failures.append(s); continue
        events += census_symbol(s,d)
        if n%25==0: print(f"census {n}/{len(syms)} events={len(events)}")
    counts={}
    for h in HORIZONS_H:
        counts[h]={"all_available":{"up":{},"down":{}},"mature_only":{"up":{},"down":{}},"mature_anchors":0}
        for e in events:
            x=e.get(h)
            if not x: continue
            if x["up_bin"]: counts[h]["all_available"]["up"][x["up_bin"]]=counts[h]["all_available"]["up"].get(x["up_bin"],0)+1
            if x["down_bin"]: counts[h]["all_available"]["down"][x["down_bin"]]=counts[h]["all_available"]["down"].get(x["down_bin"],0)+1
            if x["mature"]:
                counts[h]["mature_anchors"]+=1
                if x["up_bin"]: counts[h]["mature_only"]["up"][x["up_bin"]]=counts[h]["mature_only"]["up"].get(x["up_bin"],0)+1
                if x["down_bin"]: counts[h]["mature_only"]["down"][x["down_bin"]]=counts[h]["mature_only"]["down"].get(x["down_bin"],0)+1
    return {"meta":{"schema_version":1,"generated_at":now.isoformat(),"lookback_days":days,
                    "symbols_scanned":len(syms),"failures":failures,
                    "anchor_rule":"one anchor per 24h per symbol; opportunity labels use future excursion",
                    "label_only_warning":"future excursion is hindsight label, never a live feature",
                    "survivorship_bias_warning":"current exchangeInfo omits delisted contracts"},
            "horizons_hours":HORIZONS_H,"counts":counts,"events":events}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--days",type=int,default=60)
    p.add_argument("--max-symbols",type=int); p.add_argument("--output",default="artifacts/opportunity_census_60d_v1.json")
    a=p.parse_args(); out=build(a.days,a.max_symbols)
    path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("wrote",path,"events",len(out["events"]))


if __name__=="__main__": main()
