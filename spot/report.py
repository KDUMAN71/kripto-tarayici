"""Spot raporu: normal growth radar + mikrocap early discovery."""
import json, os, urllib.request
from . import config as C
from .outcomes import cohort_stats

COHORT_TR={"CEX":"Borsa","FRESH":"Yeni DEX","EMERGING":"Buyuyen DEX","MATURE":"Yerlesik DEX"}
VENUE_TR={"binance":"Binance","okex":"OKX","okx":"OKX","bybit":"Bybit","bybit_spot":"Bybit","gdax":"Coinbase","coinbase":"Coinbase","kraken":"Kraken","gate":"Gate","mexc":"MEXC","kucoin":"KuCoin"}
NETWORK_TR={"solana":"Solana","eth":"Ethereum","ethereum":"Ethereum","base":"Base","bsc":"BNB Chain","arbitrum":"Arbitrum","arbitrum-one":"Arbitrum","binance-smart-chain":"BNB Chain"}

def _mc(mc):
    if not mc:return "?"
    if mc>=1e9:return f"${mc/1e9:.1f}B"
    if mc>=1e6:return f"${mc/1e6:.1f}M"
    return f"${mc/1e3:.0f}K"

def _kind(c):
    if c["layer"]=="CEX":return "Borsa coini"
    d=int((c.get("age_h") or 0)//24); lc=c.get("lifecycle")
    if lc=="FRESH":return f"DEX, {d} gunluk YENI coin"
    if lc=="EMERGING":return f"DEX, buyume evresi ({d} gun)"
    return f"DEX, yerlesik ({d} gun)"

def _dots(c):
    b=c.get("breadth",0); n=min(5,(2 if b<=1 else b+1)+(1 if c.get("median_p",0)>=0.85 else 0)); return "●"*n+"○"*(5-n)

def _why(c):
    out=[]; v=c.get("f_volp")
    if v is not None:
        if v>=2:out.append(f"Hacim dunkunun {v:.1f} kati")
        elif v>=1.3:out.append(f"Hacim canlaniyor ({v:.1f}x)")
    vm=c.get("f_volmc")
    if vm is not None and vm>=0.3:out.append(f"Gunluk hacim/deger {vm:.1f}x" if vm>=1 else f"Gunluk hacim/deger %{vm*100:.0f}")
    lg=c.get("f_liqg")
    if lg is not None and lg>=0.08:out.append(f"Likidite +%{lg*100:.0f}")
    h=c.get("f_holder")
    if h is not None and h>=0.03:out.append(f"Holder +%{h*100:.1f}")
    st=c.get("f_struct")
    if st is not None:
        if st>=0.7:out.append("Grafik saglam: dipler yukseliyor")
        elif st>=0.45:out.append("Grafik toparlaniyor")
    fb=c.get("f_buy")
    if fb is not None and fb>=0.67:out.append("Alicilar baskin")
    d=c.get("diffusion") or {}; lab,br=d.get("label"),d.get("breadth",0)
    if lab=="ilgi fiyatin onunde":out.append(f"HABER: {br} kaynak, fiyat henuz kosmadi")
    elif lab=="fiyatlanmis":out.append("HABER yayilmis ama fiyat kosmus")
    elif lab=="yayilim var":out.append(f"HABER: {br} kaynak")
    if d.get("catalyst")=="cex_listing":out.append("KATALIZOR: Binance duyurusu")
    return out

def _risks(c):
    out=[]
    for f in c.get("flags") or []:
        if f=="wash_suspect":out.append("wash ihtimali")
        elif f=="paid_promo":out.append("ucretli tanitim")
        elif f=="vol_liq_divergence":out.append("hacim-likidite uyumsuz")
        elif f=="security_unverified" and c["layer"]=="DEX":out.append("kontrat guvenligi dogrulanamadi")
    if c.get("no_trusted_cex"):out.append("buyuk borsada dogrulanmadi")
    return out

def _name(c):
    nm=(c.get("ident") or {}).get("project_name") or ""; sym=c.get("symbol") or "?"; return f"{sym} ({nm})" if nm and nm.upper()!=sym else sym

def _network(n):return NETWORK_TR.get(str(n).lower(),str(n)) if n else "?"
def _venue(v):return VENUE_TR.get(str(v).lower(),str(v)) if v else "?"

def _identity_lines(c):
    lines=[]
    if c.get("layer")=="DEX":
        chain=_network(c.get("network") or (c.get("ident") or {}).get("chain")); contract=c.get("token") or (c.get("ident") or {}).get("contract"); dex=_venue(c.get("dex_id"))
        lines.append(f"   AG/KONTRAT: {chain} | {contract or 'DOGRULANAMADI'}")
        lines.append(f"   NEREDEN: {dex} DEX"+(f" | Pair: {c['pair_address']}" if c.get("pair_address") else "")); return lines
    venue=_venue(c.get("buy_venue")); pair=c.get("buy_pair"); lines.append(f"   NEREDEN: {venue}"+(f" | {pair}" if pair else "")); plats=c.get("platforms") or {}
    if len(plats)==1:
        chain,contract=next(iter(plats.items())); lines.append(f"   AG/KONTRAT: {_network(chain)} | {contract}")
    elif len(plats)>1:
        items=list(plats.items())[:3]; lines.append("   KONTRATLAR: "+" ; ".join(f"{_network(ch)}: {addr}" for ch,addr in items)+(" ; ..." if len(plats)>3 else ""))
    else:lines.append("   AG/KONTRAT: CoinGecko kontrat bildirmiyor")
    return lines

def _fmt(i,c):
    lines=[f"{i}) {_name(c)}  {_dots(c)}",f"   {_kind(c)} - {_mc(c.get('mc'))}"]+_identity_lines(c)
    why=_why(c)
    for w in why[:4]:lines.append(f"   + {w}")
    if not why:lines.append("   + esikleri gecti ama one cikan yonu zayif")
    rk=_risks(c)
    if rk:lines.append("   ! Dikkat: "+"; ".join(rk[:2]))
    return "\n".join(lines)

def _fmt_early(i,c):
    stage="🔥 EARLY OPPORTUNITY" if c.get("early_stage")=="EARLY_OPPORTUNITY" else "🟣 SEED WATCH"
    lines=[f"{i}) {stage} — {_name(c)}",f"   MC: {_mc(c.get('mc'))} | ilk gorulen: {_mc(c.get('first_seen_mc'))} | skor {c.get('early_score')}/10"]+_identity_lines(c)
    for r in (c.get("early_reasons") or [])[:5]:lines.append(f"   + {r}")
    risks=(c.get("early_risks") or [])+_risks(c)
    if risks:lines.append("   ! Risk: "+"; ".join(risks[:3]))
    return "\n".join(lines)

def build_early_alert(alerts):
    body=["🚨 SPOT EARLY DISCOVERY — YENI ERKEN FIRSAT","Bu liste $1M+ radarindan onceki mikrocap katmanidir. Guvenlik filtresi gecti; yine de yuksek risklidir.",""]
    for i,c in enumerate(alerts,1):body.append(_fmt_early(i,c)); body.append("")
    return "\n".join(body)

def build(top,meta,state,early_top=None):
    n_uni=meta["n_cex"]+meta["n_dex"]
    body=[f"SPOT RADAR - {meta['when']} - Gozlem modu",f"{n_uni} aday tarandi, elemeleri {meta['n_pass']} coin gecti, {len(top)} tanesi kayda deger.",""]
    if early_top:
        body.append(f"=== EARLY DISCOVERY ({meta.get('early_eligible',0)} mikrocap adaydan) ===")
        for i,c in enumerate(early_top,1):body.append(_fmt_early(i,c)); body.append("")
    if meta.get("news_degraded"):body.append("! Binance duyuru kaynagina bugun ulasilamadi.")
    if not top:body.append("Bugun normal radarda one cikan yok.")
    strong=[c for c in top if c.get("breadth",0)>=2]; weak=[c for c in top if c.get("breadth",0)<2]
    if strong:
        body.append("=== ONE CIKANLAR ===")
        for i,c in enumerate(strong,1):body.append(_fmt(i,c)); body.append("")
    if weak:
        body.append("=== IZLEMEDE ===")
        for j,c in enumerate(weak,len(strong)+1):body.append(_fmt(j,c)); body.append("")
    cs=cohort_stats(state); body.append(""); body.append("=== KARNE ==="); any_line=False
    for k,v in sorted(cs.items()):
        if not v["t24s"] and not v["hit50"]:continue
        any_line=True; t24=sum(v["t24s"])/len(v["t24s"])*100 if v["t24s"] else 0
        body.append(f"{COHORT_TR.get(k,k)}: {v['n']} secim, 24s ort %{t24:+.1f}"+(f", {v['hit50']}'i +%50 gordu" if v['hit50'] else ""))
    if not any_line:body.append("Henuz yeterli sonuc yok.")
    body.append(""); body.append("DEX'te isim/ticker kimlik degildir: AG + KONTRAT adresini birebir kontrol edin.")
    return "\n".join(body)

def _chunks(text,limit=3900):
    if len(text)<=limit:return [text]
    out=[]; cur=[]; n=0
    for block in text.split("\n\n"):
        add=("\n\n" if cur else "")+block
        if cur and n+len(add)>limit:
            out.append("\n\n".join(cur)); cur=[block]; n=len(block)
        else:
            cur.append(block); n+=len(add)
    if cur:out.append("\n\n".join(cur))
    return out

def send(text):
    if os.environ.get("TELEGRAM_DRY_RUN"):
        print(text); return True
    tok,chat=os.environ.get("TELEGRAM_BOT_TOKEN"),os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:print(text); return False
    try:
        for part in _chunks(text):
            data=json.dumps({"chat_id":chat,"text":part}).encode(); req=urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",data=data,headers={"Content-Type":"application/json"}); urllib.request.urlopen(req,timeout=20)
        return True
    except Exception as e:
        print("telegram hata:",e); print(text); return False
