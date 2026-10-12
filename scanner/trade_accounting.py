"""Trade accounting modes: distinguish price touches from realized fills.

Does not place exchange orders. Never infer a real fill from a candle touch.
"""
from __future__ import annotations

SIGNAL_ONLY="SIGNAL_ONLY"
PAPER_FILL="PAPER_FILL"
VERIFIED_LIVE_FILL="VERIFIED_LIVE_FILL"
MODES={SIGNAL_ONLY,PAPER_FILL,VERIFIED_LIVE_FILL}


def target_touch(symbol,side,target,price,ts):
    return {"type":"TARGET_TOUCH","symbol":symbol,"side":side,
            "target":target,"price":price,"timestamp":ts,
            "executed":False,"realized_r":None}


def realized_r_from_fills(entry,sl,side,fills,fee_r=0.0):
    """Each fill: {price, fraction}. Fractions must sum to exactly 1."""
    if not fills:return None
    risk=abs(float(entry)-float(sl))
    if risk<=0:raise ValueError("invalid risk")
    total=0.0;weighted=0.0
    for f in fills:
        fraction=float(f["fraction"])
        if fraction<=0:raise ValueError("invalid fill fraction")
        total+=fraction
        move=(float(f["price"])-float(entry)) if side=="LONG" else (float(entry)-float(f["price"]))
        weighted+=fraction*move/risk
    if abs(total-1)>1e-8:raise ValueError("fills must close exactly 100% of position")
    return weighted-float(fee_r)


def account_trade(mode,entry,sl,side,fills=None,fee_r=0.0):
    if mode not in MODES:raise ValueError("unknown execution mode")
    if mode==SIGNAL_ONLY:
        return {"mode":mode,"realized_r":None,"verified":False}
    if mode==VERIFIED_LIVE_FILL:
        if not fills or not all(f.get("exchange_fill_id") for f in fills):
            raise ValueError("live accounting requires verified exchange fill IDs")
    if not fills:
        return {"mode":mode,"realized_r":None,"verified":False}
    return {"mode":mode,"realized_r":realized_r_from_fills(entry,sl,side,fills,fee_r),
            "verified":mode==VERIFIED_LIVE_FILL}
