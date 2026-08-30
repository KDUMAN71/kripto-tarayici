"""Tamlik kapisi -> breadth (kac faktor >= p70) -> medyan percentile. Ortalama YOK."""
from . import config as C
FACTORS = ("f_volp", "f_volmc", "f_liqg", "f_buy", "f_holder", "f_struct", "f_diff")

def percentiles(cands):
    for f in FACTORS:
        vals = [c[f] for c in cands if c.get(f) is not None]
        n = len(vals)
        for c in cands:
            v = c.get(f)
            if v is None or n == 0: c[f + "_p"] = None; continue
            less = sum(1 for x in vals if x < v); eq = sum(1 for x in vals if x == v)
            c[f + "_p"] = (less + 0.5 * eq) / n   # midrank: esit degerler birbirini sisiremez

def rank(cands):
    for c in cands:
        ps = [c[f + "_p"] for f in FACTORS if c.get(f + "_p") is not None]
        c["n_factors"] = len(ps)
        need = C.MIN_FACTORS_CEX if c.get("layer") == "CEX" else C.MIN_FACTORS
        if len(ps) < need:
            c["rankable"] = False; c["breadth"] = 0; c["median_p"] = 0.0; continue
        c["rankable"] = True
        c["breadth"] = sum(1 for p in ps if p >= C.BREADTH_PCTL)
        s = sorted(ps); n = len(s)
        c["median_p"] = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    ok = [c for c in cands if c["rankable"]]
    return sorted(ok, key=lambda c: (-c["breadth"], -c["median_p"]))
