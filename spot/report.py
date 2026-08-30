import json, os, urllib.request
from . import config as C
from .outcomes import cohort_stats

def _fmt_coin(i, c):
    tag = "🅳" if c["layer"] == "DEX" else "🅲"
    mc = c.get("mc"); mcs = f"${mc/1e6:.1f}M" if mc else "?"
    d = c.get("diffusion") or {}
    lines = [f"{i}) {tag} {c.get('lifecycle','')} · {c['symbol']} — MC {mcs} · breadth {c['breadth']}/7 · medyan p{int(c['median_p']*100)}"]
    bits = []
    if c.get("f_volp") is not None: bits.append(f"hacim {c['f_volp']:.1f}x/taban")
    if c.get("f_volmc") is not None: bits.append(f"V/MC %{c['f_volmc']*100:.0f}")
    if c.get("f_liqg") is not None: bits.append(f"liq {c['f_liqg']*100:+.0f}%")
    if c.get("f_holder") is not None: bits.append(f"holder {c['f_holder']*100:+.1f}%/g")
    if c.get("f_struct") is not None: bits.append(f"yapi {c['f_struct']:.2f}")
    if bits: lines.append("   " + " · ".join(bits))
    if d.get("n24"):
        lab = f" · {d['label']}" if d.get("label") else ""
        lines.append(f"   yayilim: {d['velocity']}x · {d['breadth']} kaynak{lab}")
    if d.get("catalyst"): lines.append(f"   ⚡ katalizor: {d['catalyst']}")
    fl = c.get("flags") or []
    if fl: lines.append("   ⚠️ " + ", ".join(fl[:3]))
    return "\n".join(lines)

def build(top, meta, state):
    hdr = f"🧪 SPOT RADAR — SHADOW MODE · {meta['when']}"
    uni = f"Evren: CEX {meta['n_cex']} / DEX {meta['n_dex']} → kapilar → {meta['n_pass']} → TOP {len(top)}"
    body = [hdr, uni]
    if meta.get("news_degraded"): body.append("⚠️ duyuru kaynagi bozuk (health flag)")
    if not top: body.append("Bugun esik gecen aday yok — bu da rapordur.")
    for i, c in enumerate(top, 1): body.append(_fmt_coin(i, c))
    cs = cohort_stats(state)
    if cs:
        body.append("— KARNE (kumulatif, kohort bazli):")
        for k, v in sorted(cs.items()):
            t24 = (sum(v["t24s"]) / len(v["t24s"]) * 100) if v["t24s"] else None
            t24s = f"T24 ort {t24:+.1f}%" if t24 is not None else "T24 henuz yok"
            mfe = sum(v["mfe"]) / max(v["n"], 1) * 100
            body.append(f"  {k}: n={v['n']} · {t24s} · ortMFE {mfe:+.1f}% · hit50 {v['hit50']} · hit100 {v['hit100']}")
    body.append("⚠️ SHADOW: izleme listesidir; islem sinyali degildir. DYOR.")
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
