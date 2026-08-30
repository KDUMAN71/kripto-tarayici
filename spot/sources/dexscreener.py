from ..http import get_json
def token_pairs(chain, token):
    d = get_json(f"https://api.dexscreener.com/latest/dex/tokens/{token}")
    pairs = (d or {}).get("pairs") or []
    pairs = [p for p in pairs if not chain or p.get("chainId") == _map(chain)]
    return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0) if pairs else None
def boosts():
    d = get_json("https://api.dexscreener.com/token-boosts/latest/v1")
    out = set()
    for it in (d if isinstance(d, list) else []):
        if it.get("tokenAddress"): out.add(it["tokenAddress"].lower())
    return out
def _map(n):
    return {"eth": "ethereum", "bsc": "bsc", "base": "base", "solana": "solana"}.get(n, n)
