"""Independent scanner heartbeat watchdog.

Reads the compact state summary from a fresh checkout and alerts Telegram when the
scanner heartbeat is stale. Keeps its own tiny state file so repeated checks do
not spam the user and sends a recovery message when scanning resumes.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from scanner.telegram import Telegram

SUMMARY_PATH = Path(os.environ.get("WATCHDOG_SUMMARY_PATH", "state/summary.json"))
STATE_PATH = Path(os.environ.get("WATCHDOG_STATE_PATH", ".watchdog-state/watchdog_state.json"))
STALE_MINUTES = int(os.environ.get("WATCHDOG_STALE_MINUTES", "45"))
REMINDER_MINUTES = int(os.environ.get("WATCHDOG_REMINDER_MINUTES", "360"))


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def evaluate(summary: dict, state: dict, now: int, stale_minutes: int = 45,
             reminder_minutes: int = 360) -> dict:
    """Pure decision function used by tests and the live runner."""
    last_ok = int(summary.get("last_ok_run") or 0)
    generated = int(summary.get("generated_at") or 0)
    fail_count = int(summary.get("fail_count") or 0)
    open_count = int(summary.get("open_signal_count") or 0)

    age_s = now - last_ok if last_ok > 0 else None
    stale = last_ok <= 0 or age_s > stale_minutes * 60
    was_alerted = bool(state.get("alerted"))
    last_alert = int(state.get("last_alert_at") or 0)

    action = "NONE"
    if stale:
        reminder_due = was_alerted and last_alert > 0 and now - last_alert >= reminder_minutes * 60
        if not was_alerted or reminder_due:
            action = "ALERT"
    elif was_alerted:
        action = "RECOVERED"

    return {
        "action": action,
        "stale": stale,
        "last_ok_run": last_ok,
        "generated_at": generated,
        "age_minutes": round(age_s / 60, 1) if age_s is not None else None,
        "fail_count": fail_count,
        "open_signal_count": open_count,
    }


def _message(decision: dict) -> str:
    if decision["action"] == "RECOVERED":
        return (
            "✅ <b>SCANNER HEARTBEAT RECOVERED</b>\n"
            f"Son başarılı tarama: {decision['last_ok_run']}\n"
            f"Fail count: {decision['fail_count']} · Açık plan: {decision['open_signal_count']}"
        )

    age = decision["age_minutes"]
    age_text = "bilinmiyor" if age is None else f"{age:.1f} dk"
    return (
        "⚠️ <b>SCANNER HEARTBEAT LOST</b>\n"
        f"Son başarılı taramadan beri: {age_text}\n"
        f"last_ok_run: {decision['last_ok_run']} · summary: {decision['generated_at']}\n"
        f"Fail count: {decision['fail_count']} · Açık plan: {decision['open_signal_count']}\n"
        "Tarayıcı 45+ dakikadır yeni başarılı heartbeat üretmiyor."
    )


def main() -> int:
    now = int(time.time())
    summary = _load(SUMMARY_PATH, {})
    wd_state = _load(STATE_PATH, {})
    decision = evaluate(summary, wd_state, now, STALE_MINUTES, REMINDER_MINUTES)

    send_ok = True
    if decision["action"] in ("ALERT", "RECOVERED"):
        send_ok = Telegram().send(_message(decision))

    next_state = dict(wd_state)
    next_state.update({
        "last_check_at": now,
        "last_seen_ok_run": decision["last_ok_run"],
        "status": "STALE" if decision["stale"] else "OK",
    })

    if decision["action"] == "ALERT" and send_ok:
        next_state["alerted"] = True
        next_state["last_alert_at"] = now
    elif decision["action"] == "RECOVERED" and send_ok:
        next_state["alerted"] = False
        next_state["last_recovered_at"] = now

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(next_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(decision, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
