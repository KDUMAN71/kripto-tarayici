import time
from . import config as C
def update(state, price_of):
    now = time.time()
    for key, o in list((state.get("outcomes") or {}).items()):
        try:
            t0 = o["entered_ts"]
        except KeyError:
            continue
        age_h = (now - t0) / 3600
        if age_h > C.OUTCOME_TRACK_DAYS * 24: continue
        px = price_of(key)
        if not px or not o.get("p0"): continue
        r = px / o["p0"] - 1
        o["mfe"] = max(o.get("mfe", r), r); o["mae"] = min(o.get("mae", r), r)
        for h, f in ((24, "t24"), (72, "t72"), (168, "t7d")):
            if age_h >= h and o.get(f) is None: o[f] = round(r, 4)
        for th, f in ((0.20, "hit20"), (0.50, "hit50"), (1.00, "hit100")):
            if o["mfe"] >= th: o[f] = True
        o["last"] = round(r, 4)
def register(state, key, price, cohort):
    state.setdefault("outcomes", {})
    if key not in state["outcomes"]:
        state["outcomes"][key] = {"entered_ts": time.time(), "p0": price, "cohort": cohort,
                                  "t24": None, "t72": None, "t7d": None, "mfe": 0.0, "mae": 0.0}
def cohort_stats(state):
    out = {}
    for o in (state.get("outcomes") or {}).values():
        c = out.setdefault(o.get("cohort", "?"), {"n": 0, "t24s": [], "hit50": 0, "hit100": 0, "mfe": []})
        c["n"] += 1
        if o.get("t24") is not None: c["t24s"].append(o["t24"])
        c["mfe"].append(o.get("mfe", 0))
        c["hit50"] += 1 if o.get("hit50") else 0
        c["hit100"] += 1 if o.get("hit100") else 0
    return out
