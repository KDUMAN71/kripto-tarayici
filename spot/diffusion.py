from . import config as C
def evaluate(n24, domains, tier_score, hist_news, ch24, paid_promo, ann_hit):
    base = sum(hist_news[-3:]) / max(len(hist_news[-3:]), 1) if hist_news else 0
    velocity = n24 / (base + 1)
    import math
    raw = velocity * math.log1p(len(domains)) * (tier_score / max(n24, 1) if n24 else 0)
    if paid_promo: raw *= 0.5
    label = None
    if velocity >= C.ATTENTION_VEL and (ch24 is not None and ch24 < C.CALM_24H): label = "ilgi fiyatin onunde"
    elif ch24 is not None and ch24 > C.PRICED_IN_24H and velocity >= C.ATTENTION_VEL: label = "fiyatlanmis"
    elif velocity >= C.ATTENTION_VEL and n24 >= 3: label = "yayilim var"
    return {"velocity": round(velocity, 2), "breadth": len(domains), "tier_score": tier_score,
            "raw": raw, "label": label, "catalyst": ("cex_listing" if ann_hit else None), "n24": n24}
