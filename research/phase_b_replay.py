"""Phase B3 replay cohort + point-in-time candle snapshot builder."""
from __future__ import annotations
import pandas as pd
from scanner.indicators import analyze
from scanner.opportunity import trajectory_features, opportunity_score
from research.build_runner_dataset_v2 import klines, idx_at

SNAPSHOT_H=[-168,-72,-24,-12,-6,-3,-1,0]


def select_cohort(opportunities, mid_cap=300, short_cap=200):
    # Keep every >=100% opportunity. Sample 25-100% deterministically by
    # economic magnitude, preserving SHORT representation.
    huge=[o for o in opportunities if float(o["max_excursion_pct"])>=100]
    mid=[o for o in opportunities if 25<=float(o["max_excursion_pct"])<100]
    mid=sorted(mid,key=lambda x:(-float(x["max_excursion_pct"]),x["start_ts"],x["symbol"]))
    shorts=[o for o in mid if o["side"]=="SHORT"][:short_cap]
    chosen={o["opportunity_id"]:o for o in huge}
    for o in shorts: chosen[o["opportunity_id"]]=o
    for o in mid:
        if len([x for x in chosen.values() if x["max_excursion_pct"]<100])>=mid_cap: break
        chosen[o["opportunity_id"]]=o
    return sorted(chosen.values(),key=lambda x:(x["start_ts"],x["symbol"],x["side"]))


def historical_quote_volume_24h(d,i):
    if i is None or i<24:return None
    return float(d.iloc[i-23:i+1].quoteVolume.sum())


def snapshot_at(symbol,d,btc,target):
    i=idx_at(d,target)
    bi=idx_at(btc,target)
    if i is None or i<30:return None
    a=analyze(d.iloc[:i+1].copy(),piv_lookback=50)
    ba=analyze(btc.iloc[:bi+1].copy(),piv_lookback=50) if bi is not None and bi>=30 else None
    feat=trajectory_features(a,ba)
    return {"ts":d.iloc[i].closeTime.isoformat(),"price":float(d.iloc[i].close),
            "quote_volume_24h":historical_quote_volume_24h(d,i),
            "features":feat,"opportunity_score":opportunity_score(feat),
            "historical_context_status":"CANDLES_ONLY"}


def build_snapshots(opportunities):
    if not opportunities:return []
    starts=[pd.Timestamp(o["start_ts"]) for o in opportunities]
    lo=min(starts)-pd.Timedelta(days=10); hi=max(starts)+pd.Timedelta(days=2)
    btc=klines("BTCUSDT","1h",int(lo.timestamp()*1000),int(hi.timestamp()*1000))
    by={}
    out=[]
    for n,o in enumerate(opportunities,1):
        s=o["symbol"]; t=pd.Timestamp(o["start_ts"])
        if s not in by:
            by[s]=klines(s,"1h",int((lo-pd.Timedelta(days=2)).timestamp()*1000),int(hi.timestamp()*1000))
        d=by[s]
        if d.empty:continue
        snaps=[]
        for h in SNAPSHOT_H:
            x=snapshot_at(s,d,btc,t+pd.Timedelta(hours=h))
            if x:x["hours_from_episode_start"]=h;snaps.append(x)
        out.append({**o,"snapshots":snaps})
        if n%25==0:print("snapshots",n,"/",len(opportunities))
    return out
