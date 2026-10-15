"""Archive retention regression tests; no live-signal policy changes."""
import json
from scanner import outcomes as o
from tools import promotion_report


def test_mature_records_are_archived_and_open_records_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(o, "ARCHIVE_DIR", str(tmp_path / "archive"))
    monkeypatch.setattr(o, "MAX_EPISODES", 2)
    monkeypatch.setattr(o, "EVAL_HORIZON_H", 24)
    monkeypatch.setattr(o, "_now", lambda ts=None: 2000000000 if ts is None else ts)
    entries = [
        {"candidate_id": f"closed-{i}", "symbol": "BTCUSDT", "closed_at": 1900000000 + i,
         "status": "REJECTED"} for i in range(3)
    ]
    entries.append({"candidate_id": "open-1", "symbol": "ETHUSDT", "status": "ACTIVE"})
    monkeypatch.setattr(o, "_L", {"episodes": entries})
    o._archive_mature()
    archived = json.loads((tmp_path / "archive" / "2030-03.json").read_text())
    assert {e["candidate_id"] for e in archived["episodes"]} == {"closed-0", "closed-1"}
    assert {e["candidate_id"] for e in o._L["episodes"]} == {"closed-2", "open-1"}
    o._archive_mature()
    assert len(json.loads((tmp_path / "archive" / "2030-03.json").read_text())["episodes"]) == 2


def test_incomplete_evaluation_stays_in_live_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(o, "ARCHIVE_DIR", str(tmp_path / "archive"))
    monkeypatch.setattr(o, "MAX_EPISODES", 1)
    monkeypatch.setattr(o, "_now", lambda ts=None: 2000000000 if ts is None else ts)
    monkeypatch.setattr(o, "_L", {"episodes": [
        {"candidate_id": "young", "symbol": "A", "status": "REJECTED", "closed_at": 1999999900},
        {"candidate_id": "open", "symbol": "B", "status": "ACTIVE"}]})
    o._archive_mature()
    assert len(o._L["episodes"]) == 2
