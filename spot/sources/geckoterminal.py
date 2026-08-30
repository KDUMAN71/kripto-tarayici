from ..http import get_json
from .. import config as C
BASE = "https://api.geckoterminal.com/api/v2"
def _pools(url):
    d = get_json(url, pace=C.HTTP_PACE_GT) or {}
    return d.get("data") or []
def discover(networks):
    seen, out = set(), []
    for n in networks:
        for kind in ("new_pools", "trending_pools"):
            for p in _pools(f"{BASE}/networks/{n}/{kind}?page=1"):
                a = p.get("attributes") or {}
                addr = (p.get("relationships", {}).get("base_token", {}).get("data", {}) or {}).get("id", "")
                token = addr.split("_", 1)[-1] if addr else None
                key = f"{n}:{token}"
                if not token or key in seen: continue
                seen.add(key)
                out.append({"network": n, "token": token, "pool": a.get("address"),
                            "name": a.get("name"), "created_at": a.get("pool_created_at"),
                            "fdv": _f(a.get("fdv_usd")), "mc": _f(a.get("market_cap_usd")),
                            "liq": _f(a.get("reserve_in_usd")),
                            "vol24": _f((a.get("volume_usd") or {}).get("h24")),
                            "ch24": _f((a.get("price_change_percentage") or {}).get("h24")),
                            "price": _f(a.get("base_token_price_usd"))})
    return out
def pool_ohlcv(network, pool, limit=72):
    d = get_json(f"{BASE}/networks/{network}/pools/{pool}/ohlcv/hour?limit={limit}", pace=C.HTTP_PACE_GT) or {}
    lst = (d.get("data") or {}).get("attributes", {}).get("ohlcv_list") or []
    return [{"t": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": x[5]} for x in lst][::-1] if lst and lst[0][0] > lst[-1][0] else [{"t": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": x[5]} for x in lst]
def _f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
