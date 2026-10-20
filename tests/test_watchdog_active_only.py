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
