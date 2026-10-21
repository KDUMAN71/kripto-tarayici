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


def test_active_only_watchdog_never_calls_telegram_even_for_stale_or_recovery(monkeypatch, tmp_path):
    """A health check must update internal state but never send a user message."""
    import json

    summary_path = tmp_path / "summary.json"
    state_path = tmp_path / "watchdog_state.json"
    monkeypatch.setattr(wd, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(wd, "STATE_PATH", state_path)
    monkeypatch.setattr(wd.C, "USER_SIGNAL_ACTIVE_ONLY", True)
    monkeypatch.setattr(wd.time, "time", lambda: 200_000)

    def forbidden_telegram():
        raise AssertionError("ACTIVE-only watchdog must not initialize Telegram")

    monkeypatch.setattr(wd, "Telegram", forbidden_telegram)
    summary_path.write_text(json.dumps({"last_ok_run": 100_000, "fail_count": 0}))
    assert wd.main() == 0
    stale_state = json.loads(state_path.read_text())
    assert stale_state["status"] == "STALE"
    assert stale_state.get("alerted") is not True

    # A legacy alerted state must not produce a RECOVERED Telegram message.
    state_path.write_text(json.dumps({"alerted": True, "last_alert_at": 150_000}))
    summary_path.write_text(json.dumps({"last_ok_run": 199_900, "fail_count": 0}))
    assert wd.main() == 0
    recovered_state = json.loads(state_path.read_text())
    assert recovered_state["status"] == "OK"
