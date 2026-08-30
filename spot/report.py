"""Rapor: jargon yok — her madde 'neden listede' ve 'nelere dikkat' dilinde."""
import json, os, urllib.request
from . import config as C
from .outcomes import cohort_stats

COHORT_TR = {"CEX": "Borsa", "FRESH": "Yeni DEX", "EMERGING": "Buyuyen DEX", "MATURE": "Yerlesik DEX"}

def _mc(mc):
    if not mc: return "?"
    return f"${mc/1e9:.1f} milyar" if mc >= 1e9 else f"${mc/1e6:.0f}M deger"

def _kind(c):
    if c["layer"] == "CEX": return "Borsa coini"
    d = int((c.get("age_h") or 0) // 24)
    lc = c.get("lifecycle")
    if lc == "FRESH": return f"DEX, {d} gunluk YENI coin"
    if lc == "EMERGING": return f"DEX, buyume evresi ({d} gun)"
    return f"DEX, yerlesik ({d} gun)"

def _dots(c):
    b = c.get("breadth", 0)
    n = min(5, (2 if b <= 1 else b + 1) + (1 if c.get("median_p", 0) >= 0.85 else 0))
    return "\u25cf" * n + "\u25cb" * (5 - n)

def _why(c):
    out = []
    v = c.get("f_volp")
    if v is not None:
        if v >= 2: out.append(f"Hacim dunkunun {v:.1f} kati - ilgi hizla artiyor")
        elif v >= 1.3: out.append(f"Hacim canlaniyor (dunkunun {v:.1f} kati)")
    vm = c.get("f_volmc")
    if vm is not None and vm >= 0.3:
        out.append(f"Gunluk hacim piyasa degerinin {vm:.1f} KATI - sira disi yogunluk" if vm >= 1
                   else f"Gunluk hacim piyasa degerinin %{vm*100:.0f}'i - yuksek ilgi")
    lg = c.get("f_liqg")
    if lg is not None and lg >= 0.08: out.append(f"Likidite buyuyor (+%{lg*100:.0f}) - taze para giriyor")
    h = c.get("f_holder")
    if h is not None and h >= 0.03: out.append(f"Cuzdan sayisi artiyor (gunde +%{h*100:.1f})")
    st = c.get("f_struct")
    if st is not None:
        if st >= 0.7: out.append("Grafik saglam: dipler yukseliyor, kazanc korunuyor")
        elif st >= 0.45: out.append("Grafik toparlaniyor")
    fb = c.get("f_buy")
    if fb is not None and fb >= 0.67: out.append("Alicilar satıcılardan baskin")
    d = c.get("diffusion") or {}
    lab, br = d.get("label"), d.get("breadth", 0)
    if lab == "ilgi fiyatin onunde": out.append(f"HABER: {br} kaynakta konusuluyor ama fiyat henuz kosmadi - ERKEN ilgi")
    elif lab == "fiyatlanmis": out.append("HABER: yayilmis ama fiyat coktan kosmus - gec kalinmis olabilir")
    elif lab == "yayilim var": out.append(f"HABER: {br} kaynakta konusuluyor")
    if d.get("catalyst") == "cex_listing": out.append("KATALIZOR: Binance duyurusunda adi geciyor")
    return out

def _risks(c):
    out = []
    for f in c.get("flags") or []:
        if f == "wash_suspect": out.append("hacmin bir kismi yapay olabilir (alis-satis aynasi)")
        elif f == "paid_promo": out.append("ucretli tanitim tespit edildi")
        elif f == "vol_liq_divergence": out.append("hacim var ama likidite buyumuyor - cikis satisi olabilir")
        elif f == "security_unverified" and c["layer"] == "DEX": out.append("kontrat guvenligi dogrulanamadi")
    if c.get("no_trusted_cex"): out.append("buyuk borsada yok - alip satmasi zor olabilir")
    return out

def _name(c):
    nm = (c.get("ident") or {}).get("project_name") or ""
    sym = c.get("symbol") or "?"
    return f"{sym} ({nm})" if nm and nm.upper() != sym else sym

def _fmt(i, c):
    lines = [f"{i}) {_name(c)}  {_dots(c)}", f"   {_kind(c)} - {_mc(c.get('mc'))}"]
    why = _why(c)
    for w in why[:4]: lines.append(f"   + {w}")
    if not why: lines.append("   + esikleri gecti ama one cikan yonu zayif")
    rk = _risks(c)
    if rk: lines.append("   ! Dikkat: " + "; ".join(rk[:2]))
    return "\n".join(lines)

def build(top, meta, state):
    n_uni = meta["n_cex"] + meta["n_dex"]
    body = [f"SPOT RADAR - {meta['when']} - Gozlem modu",
            f"{n_uni} aday tarandi, elemeleri {meta['n_pass']} coin gecti, {len(top)} tanesi kayda deger.", ""]
    if meta.get("news_degraded"): body.append("! Binance duyuru kaynagina bugun ulasilamadi.")
    if not top:
        body.append("Bugun one cikan yok. Zorlama liste vermiyorum - bos gun de bilgidir.")
    strong = [c for c in top if c.get("breadth", 0) >= 2]
    weak = [c for c in top if c.get("breadth", 0) < 2]
    if strong:
        body.append("=== ONE CIKANLAR ===")
        for i, c in enumerate(strong, 1): body.append(_fmt(i, c)); body.append("")
    if weak:
        body.append("=== IZLEMEDE (daha zayif) ===")
        for j, c in enumerate(weak, len(strong) + 1):
            rk = _risks(c)
            body.append(f"{j}) {_name(c)} - {_kind(c)} - {_mc(c.get('mc'))}" + (f"  ! {rk[0]}" if rk else ""))
    cs = cohort_stats(state)
    body.append("")
    body.append("=== KARNE (sistemin gecmis secimleri nasil gitti?) ===")
    any_line = False
    for k, v in sorted(cs.items()):
        if not v["t24s"] and not v["hit50"]: continue
        any_line = True
        t24 = sum(v["t24s"]) / len(v["t24s"]) * 100 if v["t24s"] else 0
        body.append(f"{COHORT_TR.get(k, k)}: {v['n']} secim, 24 saat sonra ortalama %{t24:+.1f}"
                    + (f", {v['hit50']}'i +%50 gordu" if v['hit50'] else ""))
    if not any_line:
        body.append("Henuz not yok - secimler 24 saatini doldurunca ilk notlar gelecek.")
    body.append("")
    body.append("Bu bir IZLEME listesidir, al-sat sinyali degildir. 28 gunluk gozlem: "
                "sistem once karnesiyle kendini kanitlayacak.")
    return "\n".join(body)

def send(text):
    if os.environ.get("TELEGRAM_DRY_RUN"):
        print(text); return True
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print(text); return False
    try:
        data = json.dumps({"chat_id": chat, "text": text[:4000]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20)
        return True
    except Exception as e:
        print("telegram hata:", e); print(text); return False
