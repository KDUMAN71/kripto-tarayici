"""Phase B: deduplicate opportunity anchors into economic episodes.

This module only defines outcome episodes. Future data is label-only and must
not be passed to the live/replay decision engine.
"""
from __future__ import annotations
import pandas as pd

MAGNITUDE_RANK={"10_25":1,"25_50":2,"50_100":3,"100_200":4,"GT_200":5,
                "DOWN_10_25":1,"DOWN_25_50":2,"DOWN_50_70":3,"DOWN_GT_70":4}


def _side_value(e, horizon, side):
    x=e.get(horizon) or {}
    return float(x.get("up_pct" if side=="LONG" else "down_pct") or 0)


def _side_bin(e,horizon,side):
    x=e.get(horizon) or {}
    return x.get("up_bin" if side=="LONG" else "down_bin")


def dedupe(events,horizon="7d",side="LONG",min_pct=25.0,cooldown_days=3):
    """Merge overlapping daily anchors for the same symbol/direction.

    A new episode may start only after cooldown from the previous episode's
    last qualifying anchor. Representative anchor is the earliest qualifying
    anchor; peak label is max excursion among merged anchors.
    """
    qual=[e for e in events if (e.get(horizon) or {}).get("mature")
          and _side_value(e,horizon,side)>=min_pct]
    by={}
    for e in qual: by.setdefault(e["symbol"],[]).append(e)
    out=[]
    gap=pd.Timedelta(days=cooldown_days)
    for sym,rows in by.items():
        rows=sorted(rows,key=lambda x:x["anchor_ts"]); group=[]
        def flush(g):
            if not g:return
            first=g[0]; best=max(g,key=lambda x:_side_value(x,horizon,side))
            out.append({"symbol":sym,"side":side,"horizon":horizon,
                        "episode_start":first["anchor_ts"],"episode_end":g[-1]["anchor_ts"],
                        "anchor_price":first["anchor_price"],
                        "max_excursion_pct":_side_value(best,horizon,side),
                        "magnitude_bin":_side_bin(best,horizon,side),
                        "anchor_count":len(g)})
        for e in rows:
            if group and pd.Timestamp(e["anchor_ts"])-pd.Timestamp(group[-1]["anchor_ts"])>gap:
                flush(group); group=[]
            group.append(e)
        flush(group)
    return sorted(out,key=lambda x:(x["episode_start"],x["symbol"]))


def build_episode_set(census):
    events=census.get("events") or []
    specs=[("7d","LONG",25),("14d","LONG",50),("30d","LONG",100),
           ("7d","SHORT",25),("14d","SHORT",50)]
    episodes=[]
    for h,s,m in specs: episodes += dedupe(events,h,s,m)
    # exact identity can appear in several magnitude/horizon views; keep views
    # but assign deterministic episode key for downstream joins.
    for e in episodes:
        e["episode_key"]=f'{e["symbol"]}:{e["side"]}:{e["episode_start"]}'
    return episodes
