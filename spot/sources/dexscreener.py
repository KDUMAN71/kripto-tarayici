from ..http import get_json

def _addr_eq(chain, a, b):
    if not a or not b: return False
    # Solana base58 case-sensitive; EVM addresses are case-insensitive.
    return str(a) == str(b) if _map(chain) == "solana" else str(a).lower() == str(b).lower()

def token_pairs(chain, token):
    d = get_json(f"https://api.dexscreener.com/latest/dex/tokens/{token}")
    pairs = (d or {}).get("pairs") or []
    mapped = _map(chain)
    pairs = [p for p in pairs if (not chain or p.get("chainId") == mapped)
             and _addr_eq(chain, (p.get("baseToken") or {}).get("address"), token)]
    return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0) if pairs else None

def boosts():
    d = get_json("https://api.dexscreener.com/token-boosts/latest/v1")
    out = set()
    for it in (d if isinstance(d, list) else []):
        if it.get("tokenAddress"): out.add(it["tokenAddress"].lower())
    return out

def latest_profiles():
    d = get_json("https://api.dexscreener.com/token-profiles/latest/v1")
    return d if isinstance(d, list) else []

def _map(n):
    return {"eth": "ethereum", "bsc": "bsc", "base": "base", "solana": "solana"}.get(n, n)
