"""Early Discovery V2 — microcap seed/watch scoring, independent from $1M+ radar."""
import time
from . import config as C, gates, identity


def eligible_pool(p):
    mc = p.get("mc") or p.get("fdv")
    liq = p.get("liq")
    vol = p.get("vol24")
    age_h = gates.age_hours(p.get("created_at"))
    if not mc or not (C.EARLY_MC_MIN <= mc < C.EARLY_MC_MAX): return False
    if not liq or liq < C.EARLY_MIN_LIQ: return False
    if not vol or vol < C.EARLY_MIN_VOL24: return False
    if age_h is None or age_h < C.EARLY_MIN_AGE_H or age_h > C.EARLY_MAX_AGE_D * 24: return False
    if liq / max(mc, 1) < C.EARLY_MIN_LIQ_MC: return False
    return True


def build_candidate(p):
    name = (p.get("name") or "").split("/")[0].strip()
    return {
        "layer": "DEX", "early_layer": True,
        "key": f"{p['network']}:{p['token']}",
        "symbol": name.upper() or "?",
        "ident": identity.build(name, name, chain=p["network"], contract=p["token"]),
        "network": p["network"], "token": p["token"], "pool": p.get("pool"),
        "price": p.get("price"), "mc": p.get("mc") or p.get("fdv"), "fdv": p.get("fdv"),
        "liq": p.get("liq"), "vol24": p.get("vol24"), "ch24": p.get("ch24"),
        "age_h": gates.age_hours(p.get("created_at")), "low7": None,
    }


def ensure_first_seen(state, c):
    book = state.setdefault("early_seen", {})
    rec = book.get(c["key"])
    if rec is None:
        rec = {"first_ts": time.time(), "first_mc": c.get("mc"), "first_price": c.get("price"),
               "best_stage": "SEEN", "last_alert_stage": None, "last_alert_ts": None}
        book[c["key"]] = rec
    c["first_seen_mc"] = rec.get("first_mc")
    c["first_seen_ts"] = rec.get("first_ts")
    return rec


def score(c, prev=None):
    """Return (score 0..10-ish, reasons, risks). Uses only observable microcap data."""
    s, reasons, risks = 0, [], []
    mc = c.get("mc") or 0
    liq = c.get("liq") or 0
    vol = c.get("vol24") or 0
    vm = vol / max(mc, 1)
    lm = liq / max(mc, 1)

    if vm >= 1.0:
        s += 2; reasons.append(f"24s hacim/deger {vm:.1f}x")
    elif vm >= 0.5:
        s += 1; reasons.append(f"24s hacim/deger {vm:.1f}x")
    if lm >= 0.20:
        s += 2; reasons.append(f"likidite/deger %{lm*100:.0f}")
    elif lm >= C.EARLY_MIN_LIQ_MC:
        s += 1; reasons.append(f"likidite/deger %{lm*100:.0f}")

    br = [x for x in (c.get("buy_ratios") or []) if x is not None]
    if br:
        avg = sum(br) / len(br)
        if avg >= 0.62:
            s += 2; reasons.append(f"alici baskisi %{avg*100:.0f}")
        elif avg >= 0.56:
            s += 1; reasons.append(f"alici baskisi %{avg*100:.0f}")

    txh1 = c.get("tx_h1") or 0
    if txh1 >= 50:
        s += 1; reasons.append(f"son 1s {txh1} islem")
    elif txh1 >= 20:
        s += 0.5; reasons.append(f"son 1s {txh1} islem")

    h1, h6 = c.get("ch1"), c.get("ch6")
    if h1 is not None and 2 <= h1 <= 25:
        s += 1; reasons.append(f"1s ivme +%{h1:.0f}")
    if h6 is not None and 5 <= h6 <= 80:
        s += 1; reasons.append(f"6s ivme +%{h6:.0f}")

    if prev:
        pmc = prev.get("mc") or 0
        pliq = prev.get("liq") or 0
        ph = prev.get("holders") or 0
        if pmc and mc > pmc * 1.20 and mc < pmc * 2.5:
            s += 1; reasons.append(f"deger onceki olcume gore +%{(mc/pmc-1)*100:.0f}")
        if pliq and liq > pliq * 1.15:
            s += 1; reasons.append(f"likidite +%{(liq/pliq-1)*100:.0f}")
        if ph and c.get("holders") and c["holders"] > ph * 1.05:
            s += 1; reasons.append(f"holder +%{(c['holders']/ph-1)*100:.0f}")

    n24 = c.get("news24") or 0
    if n24 >= 2:
        s += 1; reasons.append(f"haber/sohbet yayilimi {n24} kaynak")
    elif n24 == 1:
        s += 0.5; reasons.append("erken haber/sohbet izi")

    first = c.get("first_seen_mc") or mc
    mult = mc / max(first, 1)
    c["since_first_mult"] = mult
    if mult >= C.EARLY_CHASE_MULT:
        risks.append(f"ilk gorulenden {mult:.1f}x — chase riski")
    if (c.get("ch24") or 0) > C.EARLY_CH24_CHASE:
        risks.append(f"24s +%{c['ch24']:.0f} — asiri uzamis")
    if "paid_promo" in (c.get("flags") or []): risks.append("ucretli tanitim")
    if "wash_suspect" in (c.get("flags") or []): risks.append("wash ihtimali")
    return round(s, 2), reasons, risks


def classify(c, prev=None):
    s, reasons, risks = score(c, prev)
    c["early_score"], c["early_reasons"], c["early_risks"] = s, reasons, risks
    chase = any("chase" in r or "uzamis" in r for r in risks)
    if not chase and s >= C.EARLY_OPPORTUNITY_SCORE:
        stage = "EARLY_OPPORTUNITY"
    elif s >= C.EARLY_SEED_SCORE:
        stage = "SEED_WATCH"
    else:
        stage = "IGNORE"
    c["early_stage"] = stage
    return stage


def should_alert(state, c, min_hours=6):
    if c.get("early_stage") != "EARLY_OPPORTUNITY": return False
    rec = state.setdefault("early_seen", {}).setdefault(c["key"], {})
    last_stage = rec.get("last_alert_stage")
    last_ts = rec.get("last_alert_ts") or 0
    if last_stage == "EARLY_OPPORTUNITY" and time.time() - last_ts < min_hours * 3600:
        return False
    rec["last_alert_stage"] = "EARLY_OPPORTUNITY"
    rec["last_alert_ts"] = time.time()
    rec["best_stage"] = "EARLY_OPPORTUNITY"
    return True
