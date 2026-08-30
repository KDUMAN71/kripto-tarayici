from . import config as C
def build(name, ticker, chain=None, contract=None, coin_id=None, domain=None):
    return {"coin_id": coin_id, "project_name": (name or "").strip(),
            "ticker": (ticker or "").upper().strip(), "chain": chain,
            "contract": contract, "official_domain": domain}
def news_query(ident):
    """Jenerik ticker + isimsiz -> None (haber atlanir; yanlis eslesme eksikten kotu)."""
    name = ident.get("project_name") or ""
    tick = ident.get("ticker") or ""
    if name and name.upper() != tick:
        return f'"{name}" crypto'
    if tick and tick not in C.GENERIC_TICKERS and len(tick) >= 3:
        return f'"{tick}" crypto coin'
    return None
