from ..http import get_json
BASE = "https://api.coingecko.com/api/v3"
def markets(pages=3):
    out = []
    for p in range(1, pages + 1):
        d = get_json(f"{BASE}/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page={p}&price_change_percentage=24h,7d", pace=1.2)
        if isinstance(d, list): out += d
    return out
def trending():
    d = get_json(f"{BASE}/search/trending") or {}
    return {c["item"]["symbol"].upper() for c in d.get("coins", []) if c.get("item")}
def tickers(coin_id):
    d = get_json(f"{BASE}/coins/{coin_id}/tickers?depth=false", pace=1.2) or {}
    return [t.get("market", {}).get("identifier", "") for t in d.get("tickers", [])]
def ohlc(coin_id, days=7):
    d = get_json(f"{BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}", pace=1.5)
    if not isinstance(d, list): return None
    return [{"t": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": 0} for x in d]
