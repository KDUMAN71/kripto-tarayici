"""Telegram bildirim katmani. TELEGRAM_DRY_RUN=1 ile test modunda konsola yazar."""
import os
import requests


class Telegram:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.dry = os.environ.get("TELEGRAM_DRY_RUN", "") == "1" or not self.token

    def send(self, text):
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
