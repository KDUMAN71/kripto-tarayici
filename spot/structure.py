"""Finalist OHLCV yapisi -> 0..1 kademeli puan."""
def score(ohlcv):
    if not ohlcv or len(ohlcv) < 24: return None
    closes = [x["c"] for x in ohlcv]; lows = [x["l"] for x in ohlcv]; highs = [x["h"] for x in ohlcv]
    s = 0.0
    thirds = [lows[i:i+len(lows)//3] for i in (0, len(lows)//3, 2*len(lows)//3)]
    mins = [min(t) for t in thirds if t]
    if len(mins) == 3 and mins[0] < mins[1] < mins[2]: s += 0.35            # yukselen dipler
    peak, trough = max(highs), min(lows)
    if peak > trough:
        retr = (peak - closes[-1]) / (peak - trough)
        if retr <= 0.5: s += 0.35                                           # ilk bacak korunuyor
    rng_recent = max(highs[-12:]) - min(lows[-12:])
    rng_prior = max(highs[-36:-12]) - min(lows[-36:-12]) if len(highs) >= 36 else None
    if rng_prior and rng_prior > 0 and rng_recent / rng_prior < 0.6: s += 0.15   # sikisma
    if closes[-1] >= sorted(closes)[len(closes)//2]: s += 0.15              # medyan ustu
    return min(s, 1.0)
