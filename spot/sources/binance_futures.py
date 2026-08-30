from ..http import get_json
def futures_bases():
    """Binance USDT-M futures taban varliklar seti (BAGIMSIZ adaptor; scanner import YOK)."""
    d = get_json("https://www.binance.com/fapi/v1/exchangeInfo")
    out = set()
    for s in (d or {}).get("symbols", []):
        if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
            b = s.get("baseAsset", "")
            out.add(b[4:] if b.startswith("1000") else b)
    return out
