import time
from ..http import get_json
from .. import config as C
CHAIN_ID = {"eth": "1", "bsc": "56", "base": "8453", "arbitrum": "42161", "polygon": "137"}
def security(network, contract):
    """dict | None (None = DOGRULANAMADI; guven URETILMEZ)."""
    if not contract: return None
    if network == "solana":
        d = get_json(f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={contract}", pace=C.HTTP_PACE_GOPLUS)
    else:
        cid = CHAIN_ID.get(network)
        if not cid: return None
        d = get_json(f"https://api.gopluslabs.io/api/v1/token_security/{cid}?contract_addresses={contract}", pace=C.HTTP_PACE_GOPLUS)
    res = (d or {}).get("result") or {}
    for k, v in res.items():
        if k.lower() == contract.lower(): return v
    return next(iter(res.values()), None)
