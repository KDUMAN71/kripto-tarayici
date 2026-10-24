"""Regression: watchdog remains observable without Telegram spam in ACTIVE-only mode."""
from tools import heartbeat_watchdog as wd


def test_hourly_scan_does_not_go_stale_after_57_minutes():
    decision = wd.evaluate({"last_ok_run": 100000, "generated_at": 100010}, {}, 100000 + 57 * 60)
    assert decision["stale"] is False
    assert wd.STALE_MINUTES >= 85


def test_missing_hourly_scans_still_tracked_internally():
    decision = wd.evaluate({"last_ok_run": 100000}, {}, 100000 + 90 * 60)
    assert decision["stale"] is True
    assert decision["action"] == "ALERT"


import json
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize(
    "initial_summary,initial_state,expected_action",
    [
        ({"last_ok_run": 90_000}, {}, "ALERT"),
        ({"last_ok_run": 99_950}, {"alerted": True, "last_alert_at": 95_000}, "RECOVERED"),
        ({"last_ok_run": 99_950}, {}, "ALIVE"),
    ],
)
def test_active_only_suppression_never_acknowledges_unsent_messages(
    monkeypatch, tmp_path, initial_summary, initial_state, expected_action
):
    summary_path = tmp_path / "summary.json"
    state_path = tmp_path / "watchdog_state.json"
    summary_path.write_text(json.dumps(initial_summary), encoding="utf-8")
    state_path.write_text(json.dumps(initial_state), encoding="utf-8")
    monkeypatch.setattr(wd, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(wd, "STATE_PATH", state_path)
    monkeypatch.setattr(wd, "time", SimpleNamespace(time=lambda: 100_000))
    monkeypatch.setattr(wd.C, "USER_SIGNAL_ACTIVE_ONLY", True)

    class ForbiddenTelegram:
        def __init__(self):
            raise AssertionError("Watchdog must not initialize Telegram in ACTIVE-only mode")

    monkeypatch.setattr(wd, "Telegram", ForbiddenTelegram)
    assert wd.evaluate(initial_summary, initial_state, 100_000)["action"] == expected_action
    assert wd.main() == 0
    stored = json.loads(state_path.read_text(encoding="utf-8"))
    assert stored["last_check_at"] == 100_000
    assert stored["status"] == ("STALE" if expected_action == "ALERT" else "OK")
    for field in ("alerted", "last_alert_at", "last_recovered_at", "last_alive_at"):
        assert stored.get(field) == initial_state.get(field)


@pytest.mark.parametrize("send_result", [True, False])
def test_watchdog_acknowledges_only_confirmed_telegram_send(
    monkeypatch, tmp_path, send_result
):
    summary_path = tmp_path / "summary.json"
    state_path = tmp_path / "watchdog_state.json"
    summary_path.write_text(json.dumps({"last_ok_run": 90_000}), encoding="utf-8")
    monkeypatch.setattr(wd, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(wd, "STATE_PATH", state_path)
    monkeypatch.setattr(wd, "time", SimpleNamespace(time=lambda: 100_000))
    monkeypatch.setattr(wd.C, "USER_SIGNAL_ACTIVE_ONLY", False)
    sent = []

    class FakeTelegram:
        def send(self, message):
            sent.append(message)
            return send_result

    monkeypatch.setattr(wd, "Telegram", FakeTelegram)
    assert wd.main() == 0
    assert len(sent) == 1
    stored = json.loads(state_path.read_text(encoding="utf-8"))
    assert stored["status"] == "STALE"
    assert stored.get("alerted", False) is send_result
    assert stored.get("last_alert_at") == (100_000 if send_result else None)
