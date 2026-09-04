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

def ticker_details(coin_id):
    """CoinGecko ticker kayitlarini venue secimi icin normalize eder."""
    d = get_json(f"{BASE}/coins/{coin_id}/tickers?depth=false", pace=1.2) or {}
    out = []
    for t in d.get("tickers", []):
        market = (t.get("market", {}).get("identifier") or "").lower().strip()
        if not market:
            continue
        out.append({
            "market": market,
            "base": (t.get("base") or "").upper(),
            "target": (t.get("target") or "").upper(),
            "trust_score": t.get("trust_score"),
            "volume": t.get("volume"),
            "trade_url": t.get("trade_url"),
        })
    return out

def tickers(coin_id):
    """Geriye uyumluluk: yalniz market identifier listesi."""
    return [t["market"] for t in ticker_details(coin_id)]

def platforms(coin_id):
    """CoinGecko'nun bildirdigi ag -> kontrat eslesmeleri.

    Native coinlerde veya CoinGecko kontrat vermiyorsa bos sozluk doner. Bu durum
    kontrat uydurmak yerine raporda acikca 'native/veri yok' diye gosterilir.
    """
    url = (f"{BASE}/coins/{coin_id}?localization=false&tickers=false&market_data=false"
           "&community_data=false&developer_data=false&sparkline=false")
    d = get_json(url, pace=1.2) or {}
    p = d.get("platforms") or {}
    return {str(k): str(v).strip() for k, v in p.items() if v and str(v).strip()}

def ohlc(coin_id, days=7):
    d = get_json(f"{BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}", pace=1.5)
    if not isinstance(d, list): return None
    return [{"t": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": 0} for x in d]
