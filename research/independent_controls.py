"""Point-in-time matched controls for independent opportunity research.

Use complete historical symbol frames, not scanner-selected candidates.
Outcome labels are strictly separated from pre-anchor matching features.
"""
from __future__ import annotations
import math
import pandas as pd


def _index_at(frame, timestamp):
    ix=frame.index[frame["closeTime"]<=pd.Timestamp(timestamp)]
    return int(ix[-1]) if len(ix) else None


def _pre_features(frame, i):
    if i is None or i<24:
        return None
    q=float(frame.iloc[i-23:i+1]["quoteVolume"].sum())
    p=float(frame.iloc[i]["close"])
    old=float(frame.iloc[i-24]["close"])
    return {"quote_volume_24h":q,"return_24h":(p/old-1)*100 if old else None,
            "history_bars":i+1}


def _future_excursion(frame,i,horizon,side):
    if i is None or i+horizon>=len(frame):
        return None  # fully mature horizon only
    future=frame.iloc[i+1:i+1+horizon]
    p=float(frame.iloc[i]["close"])
    if p<=0:return None
    return ((float(future["high"].max())/p-1)*100 if side=="LONG"
            else (1-float(future["low"].min())/p)*100)


def matched_controls(opportunity,frames,horizon_hours=168,threshold_pct=25,
                     count=3,volume_ratio_limit=5):
    """Same closed-hour matched negatives with similar pre-anchor volume.

    Future prices are used ONLY to verify control labels, never for ranking.
    """
    sym=opportunity["symbol"]; side=opportunity["side"]
    ts=pd.Timestamp(opportunity["start_ts"])
    ref=frames.get(sym)
    if ref is None or ref.empty:return []
    ri=_index_at(ref,ts)
    rf=_pre_features(ref,ri)
    if not rf or rf["quote_volume_24h"]<=0:return []
    candidates=[]
    for s,frame in frames.items():
        if s==sym or frame is None or frame.empty:continue
        i=_index_at(frame,ts)
        if i is None or abs((frame.iloc[i]["closeTime"]-ts).total_seconds())>3600:continue
        f=_pre_features(frame,i)
        if not f or f["quote_volume_24h"]<=0:continue
        ratio=f["quote_volume_24h"]/rf["quote_volume_24h"]
        if not 1/volume_ratio_limit<=ratio<=volume_ratio_limit:continue
        outcome=_future_excursion(frame,i,horizon_hours,side)
        if outcome is None or outcome>=threshold_pct:continue
        dist=abs(math.log(ratio))
        candidates.append((dist,s,i,f,outcome))
    out=[]
    for dist,s,i,f,outcome in sorted(candidates,key=lambda x:(x[0],x[1]))[:count]:
        out.append({"opportunity_id":opportunity["opportunity_id"],
                    "control_symbol":s,"anchor_ts":frames[s].iloc[i]["closeTime"].isoformat(),
                    "side":side,"match_distance":dist,"pre_anchor":f,
                    "future_excursion_pct_LABEL_ONLY":outcome,
                    "horizon_hours":horizon_hours})
    return out
