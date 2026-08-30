"""Eleme kapilari — puan degil gecti/kaldi; her karar sebep yazar."""
import time
from . import config as C

def age_hours(created_iso):
    if not created_iso: return None
    try:
        import datetime as dt
        t = dt.datetime.fromisoformat(created_iso.replace("Z", "+00:00")).timestamp()
        return (time.time() - t) / 3600.0
    except Exception:
        return None

def lifecycle(age_h):
    if age_h is None: return "UNKNOWN"
    d = age_h / 24.0
    if age_h < 12: return "PRE"
    if age_h < 24: return "DISCOVERY"
    if d <= C.FRESH_MAX_D: return "FRESH"
    if d <= C.EMERGING_MAX_D: return "EMERGING"
    return "MATURE"

def security_gate(sec):
    """(elenir_mi, sebepler). sec=None -> DOGRULANAMADI (ayrica ele alinir)."""
    if sec is None: return False, []
    rs = []
    def one(v): return str(v) == "1"
    if one(sec.get("is_honeypot")): rs.append("honeypot")
    if one(sec.get("is_blacklisted")): rs.append("blacklist")
    if one(sec.get("is_mintable")) and (sec.get("owner_address") or "") not in ("", "0x0000000000000000000000000000000000000000"):
        rs.append("mintable+owner")
    if one(sec.get("can_take_back_ownership")): rs.append("ownership_geri_alinabilir")
    for k in ("buy_tax", "sell_tax"):
        try:
            if float(sec.get(k) or 0) * 100 > C.MAX_TAX_PCT: rs.append(f"{k}>%{C.MAX_TAX_PCT}")
        except ValueError: pass
    return bool(rs), rs

def concentration_gate(sec):
    if sec is None: return False, []
    rs = []
    try:
        holders = sec.get("holders") or []
        top10 = sum(float(h.get("percent", 0)) for h in holders[:10] if not str(h.get("is_locked")) == "1") * 100
        if top10 > C.TOP10_MAX_PCT: rs.append(f"top10 %{top10:.0f}")
    except Exception: pass
    try:
        if float(sec.get("creator_percent") or 0) * 100 > C.CREATOR_MAX_PCT: rs.append("creator>%10")
    except ValueError: pass
    return bool(rs), rs

def liquidity_gate(liq_now, liq_prev):
    if liq_now is None or not liq_prev: return False, []
    if liq_now < liq_prev * C.LIQ_DROP_RATIO:
        return True, [f"likidite dusuyor {liq_prev:.0f}->{liq_now:.0f}"]
    return False, []

def manipulation_flags(cand, boosted):
    fl = []
    b, s = cand.get("buys24"), cand.get("sells24")
    if b and s and (b + s) > 400:
        r = b / max(s, 1)
        if C.WASH_BS_LO <= r <= C.WASH_BS_HI: fl.append("wash_suspect")
    if boosted: fl.append("paid_promo")
    ch, lg = cand.get("ch24"), cand.get("liq_growth")
    if ch is not None and lg is not None and ch > 40 and abs(lg) < 0.02:
        fl.append("vol_liq_divergence")
    return fl

def extended_gate(ch24, price, low7):
    if ch24 is not None and ch24 > C.EXT_24H_PCT: return True, [f"24s +%{ch24:.0f}"]
    if price and low7 and low7 > 0 and price / low7 > C.EXT_7D_MULT: return True, ["7g dibinin >4x"]
    return False, []

def apply(cand, prev_snap, sec, boosted):
    """-> (kabul, sebepler, bayraklar). DEX icin sec dogrulanmadan Top10 YOK."""
    reasons, flags = [], []
    layer = cand["layer"]
    if layer == "DEX":
        lc = lifecycle(cand.get("age_h"))
        cand["lifecycle"] = lc
        if lc in ("PRE", "DISCOVERY", "UNKNOWN"):
            return False, [f"yas siniri ({lc})"], flags
        if sec is None:
            flags.append("security_unverified")
            return False, ["guvenlik dogrulanamadi (GoPlus sessiz)"], flags
        bad, rs = security_gate(sec)
        if bad: return False, rs, flags
        bad, rs = concentration_gate(sec)
        if bad: return False, rs, flags
    else:
        cand["lifecycle"] = "CEX"
        if sec is None: flags.append("security_unverified")
    bad, rs = liquidity_gate(cand.get("liq"), (prev_snap or {}).get("liq"))
    if bad:
        flags.append("exit_liquidity") if (cand.get("ch24") or 0) > 0 else None
        return False, rs, flags
    mf = manipulation_flags(cand, boosted)
    flags += mf
    if len(mf) >= C.MANIP_FLAGS_VETO: return False, [f"manipulasyon bayraklari: {mf}"], flags
    bad, rs = extended_gate(cand.get("ch24"), cand.get("price"), cand.get("low7"))
    if bad:
        cand["extended"] = True
        return False, ["EXTENDED"] + rs, flags
    return True, [], flags
