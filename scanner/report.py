"""Paper-performance raporu.

Kullanim (repo kokunde):  python -m scanner.report

state/state.json icindeki kapanmis sinyalleri (trades) okur ve strateji
kalitesini olcer: win rate, expectancy (R), profit factor, MFE/MAE.

Agirlikli R hesabi config'teki pozisyon yonetimine gore yapilir:
  TP1'de %25 kapat, TP2'de %35, TP3'te %40; TP1 sonrasi SL girise (BE) tasinir.
Yani TP1 sonrasi stop olan islem tam -1R degil, kismi kar + BE olarak sayilir.
"""
import json
from . import config as C


def weighted_r(t):
    """Tek islemin pozisyon-yonetimli yaklasik R sonucu."""
    entry, sl = t.get("entry"), t.get("sl")
    if not entry or not sl:
        return None
    risk = abs(entry - sl)
    if risk <= 0:
        return None

    def r_of(price):
        if price is None:
            return 0.0
        return ((price - entry) / risk) if t["side"] == "LONG" else ((entry - price) / risk)

    f1, f2, f3 = C.TP1_CLOSE_PCT / 100, C.TP2_CLOSE_PCT / 100, C.TP3_CLOSE_PCT / 100
    tp1_r, tp2_r, tp3_r = r_of(t.get("tp1")), r_of(t.get("tp2")), r_of(t.get("tp3"))

    if t.get("tp3_done"):
        return f1 * tp1_r + f2 * tp2_r + f3 * tp3_r
    if t.get("tp2_done"):
        # kalan %40, BE'ye tasinmis stop varsayimiyla 0R
        return f1 * tp1_r + f2 * tp2_r + f3 * 0.0
    if t.get("tp1_done"):
        # TP1 alindi, kalan %75 BE'den cikti varsayimi
        return f1 * tp1_r
    # hicbir TP yok -> tam stop
    return -1.0


def run():
    with open(C.STATE_PATH) as f:
        st = json.load(f)
    trades = st.get("trades", [])
    if not trades:
        print("Henuz kapanmis islem kaydi yok. (Sinyaller ACTIVE olup "
              "STOP/TP3 ile sonuclandikca burada birikir.)")
        return

    rs = [(t, weighted_r(t)) for t in trades]
    rs = [(t, r) for t, r in rs if r is not None]
    wins = [r for _, r in rs if r > 0]
    losses = [r for _, r in rs if r <= 0]
    total = len(rs)
    win_rate = len(wins) / total * 100
    expectancy = sum(r for _, r in rs) / total
    gross_win = sum(wins)
    gross_loss = abs(sum(losses)) or 1e-9
    pf = gross_win / gross_loss

    print(f"Islem sayisi     : {total}")
    print(f"Win rate         : %{win_rate:.1f}")
    print(f"Expectancy       : {expectancy:+.2f}R / islem")
    print(f"Profit factor    : {pf:.2f}")
    print(f"Ort. MFE / MAE   : %{sum(t.get('mfe_pct',0) for t,_ in rs)/total:.2f} / "
          f"%{sum(t.get('mae_pct',0) for t,_ in rs)/total:.2f}")
    print()
    print("Sembol bazinda son islemler:")
    for t, r in rs[-15:]:
        print(f"  {t['symbol']:<12} {t['side']:<5} {t['outcome']:<9} "
              f"R={r:+.2f}  MFE %{t.get('mfe_pct',0):.1f}  MAE %{t.get('mae_pct',0):.1f}")
    print()
    if total < 30:
        print(f"NOT: {total} islem istatistiksel olarak azdir; 50-100 islem "
              "birikmeden esik/kural degisikligi karari verme.")


if __name__ == "__main__":
    run()
