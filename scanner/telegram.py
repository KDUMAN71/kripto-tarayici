"""Telegram bildirim katmani.

V3.3 bildirim politikasi:
- EARLY/WATCH/teyitsiz karar bolgesi sistem icinde sessiz izlenir.
- Kullaniciya yalniz gercekten islem alinabilir ACTIVE setup + aktif islemin
  STOP/TP yonetimi ve operasyonel sistem uyarilari gider.
- Kalibre edilmemis LONG/SHORT yuzdeleri kullanici mesajindan temizlenir.

TELEGRAM_DRY_RUN=1 ile test modunda konsola yazar.
"""
import os
import re
import requests


_PRETRADE_MARKERS = (
    "<b>ERKEN UYARI",
    "<b>YAKIN TAKİP",
    "<b>YAKIN TAKIP",
)


def _notification_policy(text):
    """(send?, sanitized_text) dondurur.

    EARLY/WATCH ve bunlara ait iptal mesajlari kullaniciya gitmez. Bunlar state/log
    icinde izlenmeye devam eder. ACTIVE/STOP/TP ve operasyonel mesajlar korunur.
    """
    if any(marker in text for marker in _PRETRADE_MARKERS):
        return False, text

    # Kullanici hic gormedigi pretrade planin iptalini de gormemeli.
    if text.startswith("🛑 <b>İPTAL —") or text.startswith("🛑 <b>IPTAL —"):
        return False, text
    if text.startswith("🛑 <b>İPTAL (HABER VETOSU)") or text.startswith("🛑 <b>IPTAL (HABER VETOSU)"):
        return False, text

    # Decision Engine yuzdeleri calibration tamamlanana kadar win-probability gibi
    # algilanmasin. Yon baskisi bandini tut, yapay hassasiyeti Telegram'dan kaldir.
    pattern = re.compile(
        r"Karar:\s*(LONG|SHORT|WAIT)\s*\(([^)]+)\)\s*·\s*"
        r"model avantajı LONG %\d+ / SHORT %\d+\n"
    )

    def repl(match):
        bias, strength = match.group(1), match.group(2)
        if bias == "WAIT":
            return "Yönsel baskı: karışık/zayıf\n"
        return f"Yönsel baskı: {bias} — {strength}\n"

    return True, pattern.sub(repl, text)


class Telegram:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.dry = os.environ.get("TELEGRAM_DRY_RUN", "") == "1" or not self.token

    def send(self, text):
        should_send, text = _notification_policy(text)
        if not should_send:
            if self.dry:
                print("\n===== TELEGRAM SUPPRESSED (dry-run) =====")
                print(text)
                print("=========================================\n")
            return True

        if self.dry:
            print("\n===== TELEGRAM (dry-run) =====")
            print(text)
            print("==============================\n")
            return True
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text,
                      "parse_mode": "HTML", "disable_web_page_preview": True},
                timeout=15)
            return r.status_code == 200
        except requests.RequestException:
            return False
