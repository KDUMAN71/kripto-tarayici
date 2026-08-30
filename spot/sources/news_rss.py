import re, time, email.utils
from ..http import get_text, get_json
from .. import config as C
def google_news(query):
    """(son24s_madde, benzersiz_domain_listesi, tier_agirlikli_puan)"""
    x = get_text("https://news.google.com/rss/search?q=" + query.replace(" ", "+") + "&hl=en-US&gl=US&ceid=US:en")
    if not x: return 0, [], 0.0
    items = re.findall(r"<item>(.*?)</item>", x, re.S)
    now = time.time(); n24 = 0; domains = set(); score = 0.0
    for it in items:
        src = re.search(r"<source url=\"?https?://(?:www\.)?([^\"/>]+)", it)
        dom = (src.group(1).lower() if src else "")
        pd = re.search(r"<pubDate>([^<]+)</pubDate>", it)
        fresh = False
        if pd:
            try:
                ts = email.utils.mktime_tz(email.utils.parsedate_tz(pd.group(1)))
                fresh = (now - ts) <= 86400
            except Exception: pass
        if not fresh: continue
        if any(b in dom for b in C.TIER_BLACKLIST): continue
        n24 += 1; domains.add(dom)
        score += 3 if any(t in dom for t in C.TIER1) else (2 if any(t in dom for t in C.TIER2) else 1)
    return n24, sorted(domains), score
def binance_announcements():
    """(basliklar, saglikli_mi)"""
    d = get_json("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20")
    try:
        arts = d["data"]["catalogs"][0]["articles"]
        return [a.get("title", "") for a in arts], True
    except Exception:
        return [], False
