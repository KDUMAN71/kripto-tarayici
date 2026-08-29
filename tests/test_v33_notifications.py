from scanner.telegram import _notification_policy


def test_early_and_watch_are_suppressed():
    for msg in (
        "🔵 <b>ERKEN UYARI — DOTUSDT LONG</b>",
        "🟡 <b>YAKIN TAKİP — DOTUSDT SHORT</b>",
    ):
        send, _ = _notification_policy(msg)
        assert send is False


def test_pretrade_cancel_is_suppressed():
    send, _ = _notification_policy("🛑 <b>İPTAL — DOTUSDT LONG</b>\nKurulum bozuldu")
    assert send is False


def test_active_message_kept_but_uncalibrated_percentages_removed():
    msg = ("🟢 <b>İŞLEM BÖLGESİ AKTİF — DOTUSDT SHORT</b>\n"
           "Karar: SHORT (guclu) · model avantajı LONG %17 / SHORT %83\n"
           "Giriş: 0.8200–0.8220 | SL: 0.8400 — HARD STOP")
    send, out = _notification_policy(msg)
    assert send is True
    assert "Yönsel baskı: SHORT — guclu" in out
    assert "%83" not in out
    assert "model avantajı" not in out


def test_stop_tp_and_operational_alerts_are_preserved():
    for msg in (
        "🔴 <b>STOP — DOTUSDT LONG</b>",
        "🎯 <b>TP1 GÖRÜLDÜ — DOTUSDT LONG</b>",
        "🚨 <b>VERİ KAYNAĞI SORUNU</b>",
    ):
        send, _ = _notification_policy(msg)
        assert send is True
