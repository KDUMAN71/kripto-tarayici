from tools.heartbeat_watchdog import evaluate, _fmt_epoch


def test_healthy_heartbeat_no_alert_when_alive_recent():
    d = evaluate({"last_ok_run": 9_900, "generated_at": 9_910, "fail_count": 0,
                  "open_signal_count": 5}, {"last_alive_at": 9_500}, 10_000,
                 stale_minutes=45, alive_interval_minutes=1440)
    assert d["stale"] is False
    assert d["action"] == "NONE"


def test_healthy_heartbeat_emits_alive_when_due():
    d = evaluate({"last_ok_run": 9_900, "generated_at": 9_910}, {}, 100_000,
                 stale_minutes=45, alive_interval_minutes=1440)
    # This summary is stale at now=100000, so stale alert wins over alive.
    assert d["action"] == "ALERT"

    d = evaluate({"last_ok_run": 99_900, "generated_at": 99_910}, {}, 100_000,
                 stale_minutes=45, alive_interval_minutes=1440)
    assert d["stale"] is False
    assert d["action"] == "ALIVE"


def test_alive_ping_does_not_repeat_before_interval():
    d = evaluate({"last_ok_run": 99_900, "generated_at": 99_910},
                 {"last_alive_at": 99_000}, 100_000,
                 stale_minutes=45, alive_interval_minutes=1440)
    assert d["action"] == "NONE"


def test_stale_heartbeat_alerts_once():
    d = evaluate({"last_ok_run": 7_000, "generated_at": 7_010}, {}, 10_000,
                 stale_minutes=45)
    assert d["stale"] is True
    assert d["action"] == "ALERT"


def test_stale_heartbeat_does_not_spam_before_reminder():
    d = evaluate({"last_ok_run": 7_000, "generated_at": 7_010},
                 {"alerted": True, "last_alert_at": 9_000}, 10_000,
                 stale_minutes=45, reminder_minutes=360)
    assert d["stale"] is True
    assert d["action"] == "NONE"


def test_stale_heartbeat_can_remind_after_window():
    d = evaluate({"last_ok_run": 7_000, "generated_at": 7_010},
                 {"alerted": True, "last_alert_at": 7_000}, 30_000,
                 stale_minutes=45, reminder_minutes=360)
    assert d["action"] == "ALERT"


def test_recovery_is_reported_once_before_alive():
    d = evaluate({"last_ok_run": 9_900, "generated_at": 9_910},
                 {"alerted": True, "last_alert_at": 8_000}, 10_000,
                 stale_minutes=45)
    assert d["stale"] is False
    assert d["action"] == "RECOVERED"


def test_epoch_is_formatted_for_turkey():
    assert _fmt_epoch(0) == "bilinmiyor"
    assert "TRT" in _fmt_epoch(1_788_860_128)
