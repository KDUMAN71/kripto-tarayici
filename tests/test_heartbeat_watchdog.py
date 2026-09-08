from tools.heartbeat_watchdog import evaluate


def test_healthy_heartbeat_no_alert():
    d = evaluate({"last_ok_run": 9_900, "generated_at": 9_910, "fail_count": 0,
                  "open_signal_count": 5}, {}, 10_000, stale_minutes=45)
    assert d["stale"] is False
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


def test_recovery_is_reported_once():
    d = evaluate({"last_ok_run": 9_900, "generated_at": 9_910},
                 {"alerted": True, "last_alert_at": 8_000}, 10_000,
                 stale_minutes=45)
    assert d["stale"] is False
    assert d["action"] == "RECOVERED"
