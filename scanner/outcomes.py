"""V3.5 bounded candidate outcome ledger.

Learning data only. It never changes scanner policy or sends alerts.
"""
from __future__ import annotations
import json, os, time, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "state", "outcome_ledger.json")
MAX_EPISODES = 600
MAX_EVENTS = 16
EVAL_HORIZON_H = 24
_OPEN = {"PRE_RUNNER", "EARLY", "WATCH", "ACTIVE"}
_L = None


def load():
    global _L
    try:
        with open(PATH, encoding="utf-8") as f:
            _L = json.load(f)
    except Exception:
        _L = {}
    _L.setdefault("episodes", [])
    return _L


def _now(ts=None):
    return int(time.time() if ts is None else ts)


def _current(sym):
    if _L is None:
        return None
    for e in reversed(_L["episodes"]):
        if e["symbol"] == sym and e.get("status") in _OPEN:
            return e
    return None


def start(sym, status, features=None, ts=None):
    if _L is None:
        return None
    t = _now(ts)
    e = _current(sym)
    if e:
        transition(sym, status, features=features, ts=t)
        return e
    e = {
        "candidate_id": f"{sym}-{t}-{uuid.uuid4().hex[:6]}",
        "symbol": sym, "created": t, "last_update": t, "status": status,
        "initial_features": dict(features or {}), "events": [],
        "mfe_pct": 0.0, "mae_pct": 0.0,
    }
    _L["episodes"].append(e)
    transition(sym, status, features=features, ts=t)
    if len(_L["episodes"]) > MAX_EPISODES:
        del _L["episodes"][:len(_L["episodes"]) - MAX_EPISODES]
    return e


def transition(sym, status, reason=None, features=None, ts=None):
    e = _current(sym)
    if e is None:
        return start(sym, status, features=features, ts=ts)
    t = _now(ts)
    prev = e.get("status")
    e["status"] = status
    e["last_update"] = t
    if features:
        e["latest_features"] = dict(features)
    if prev != status or reason:
        e["events"].append({"ts": t, "from": prev, "to": status, "reason": reason})
        e["events"] = e["events"][-MAX_EVENTS:]
    return e


def update_excursion(sym, price, ts=None):
    e = _current(sym)
    if not e or not price:
        return
    ref = e.get("reference_price") or e.get("initial_features", {}).get("price")
    side = e.get("side")
    if not ref:
        return
    move = (float(price) - float(ref)) / float(ref) * 100
    fav = move if side != "SHORT" else -move
    e["mfe_pct"] = max(float(e.get("mfe_pct", 0)), fav)
    e["mae_pct"] = max(float(e.get("mae_pct", 0)), -fav)
    e["last_update"] = _now(ts)


def set_trade_geometry(sym, sig, ts=None):
    e = _current(sym)
    if not e:
        e = start(sym, sig.get("status", "WATCH"), ts=ts)
    e["side"] = sig.get("side")
    e["reference_price"] = sig.get("entry_ref") or sig.get("price")
    for k in ("trigger", "sl", "tp1", "tp2", "tp3", "rr1", "rr2", "rr3",
              "setup_type", "score", "decision_bias"):
        if k in sig:
            e[k] = sig.get(k)
    return e


def close(sym, outcome, reason=None, ts=None):
    e = _current(sym)
    if not e:
        return None
    t = _now(ts)
    prev = e.get("status")
    e["status"] = outcome
    e["closed_at"] = t
    e["last_update"] = t
    e["outcome"] = outcome
    e["close_reason"] = reason
    e["events"].append({"ts": t, "from": prev, "to": outcome, "reason": reason})
    e["events"] = e["events"][-MAX_EVENTS:]
    return e



def update_evaluation_prices(price_by_symbol, ts=None):
    """Terminal/rejected episode'lar icin 24s outcome-label MFE/MAE.

    Bu gelecek veri yalniz evaluation labelidir; live karar motoruna geri
    beslenmez. Episode kapanisindan sonra horizon dolana kadar guncellenir.
    """
    if _L is None:
        return 0
    t = _now(ts)
    n = 0
    for e in _L["episodes"]:
        if e.get("status") in _OPEN:
            continue
        closed = e.get("closed_at")
        ref = e.get("reference_price") or e.get("initial_features", {}).get("price")
        px = price_by_symbol.get(e.get("symbol"))
        if not closed or t - closed > EVAL_HORIZON_H * 3600 or not ref or not px:
            continue
        move = (float(px) - float(ref)) / float(ref) * 100
        side = e.get("side")
        # Discovery/rejected adaylarda yon henuz yoksa mutlak move runner-label
        # icin tutulur; direction-specific trade attribution yapilmaz.
        if side == "SHORT":
            fav, adv = -move, move
        elif side == "LONG":
            fav, adv = move, -move
        else:
            fav, adv = abs(move), 0.0
        e["mfe_pct"] = max(float(e.get("mfe_pct", 0)), fav)
        e["mae_pct"] = max(float(e.get("mae_pct", 0)), adv)
        e["evaluation_last_ts"] = t
        n += 1
    return n


def save():
    if _L is None:
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_L, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, PATH)
