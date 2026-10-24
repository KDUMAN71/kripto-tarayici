"""Spot discovery cannot generate user-facing Telegram without an ACTIVE gate."""
import pytest

from spot import config as C, main, report


@pytest.mark.parametrize("early_only", [True, False])
def test_spot_scans_and_persists_without_telegram_or_false_alert_ack(
    monkeypatch, early_only
):
    monkeypatch.setattr(C, "USER_SIGNAL_ACTIVE_ONLY", True)
    if early_only:
        monkeypatch.setenv("SPOT_EARLY_ONLY", "1")
    else:
        monkeypatch.delenv("SPOT_EARLY_ONLY", raising=False)
    state = {"health": {}, "early_seen": {}, "reports": [], "snapshots": {}, "outcomes": {}}
    saved = []
    monkeypatch.setattr(main, "_load", lambda: state)
    monkeypatch.setattr(main, "_save", lambda st: saved.append(st))
    monkeypatch.setattr(main.dexscreener, "boosts", lambda: set())
    monkeypatch.setattr(main.news_rss, "binance_announcements", lambda: ([], True))
    monkeypatch.setattr(main, "scan_early", lambda st, boosted: ([{"key": "solana:test", "early_stage": "EARLY_OPPORTUNITY"}], 1, 1))
    monkeypatch.setattr(main, "_run_growth", lambda *args: ([], [], [], []))

    def forbidden(*args, **kwargs):
        raise AssertionError("No spot Telegram send or notification acknowledgement in ACTIVE-only mode")

    monkeypatch.setattr(main.early, "should_alert", forbidden)
    monkeypatch.setattr(main.report, "send", forbidden)
    monkeypatch.setattr(main.report, "build", forbidden)
    monkeypatch.setattr(main.report, "build_early_alert", forbidden)

    main.run()
    assert len(saved) == 1
    assert saved[0]["early_seen"] == {}
    if early_only:
        assert saved[0]["early_meta"]["top"] == 1
    else:
        assert len(saved[0]["reports"]) == 1


def test_spot_transport_blocks_discovery_even_with_credentials(monkeypatch):
    monkeypatch.setattr(C, "USER_SIGNAL_ACTIVE_ONLY", True)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test")
    monkeypatch.setenv("TELEGRAM_DRY_RUN", "1")

    def forbidden(*args, **kwargs):
        raise AssertionError("No network call permitted")

    monkeypatch.setattr(report.urllib.request, "urlopen", forbidden)
    assert report.send("SEED WATCH / EARLY OPPORTUNITY") is False
