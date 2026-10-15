"""Build OOS promotion eligibility report; never promotes automatically."""
import json, os, time, glob
from research.promotion import promotion_gate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "state", "outcome_ledger.json")
REPORT = os.path.join(ROOT, "state", "promotion_report.json")


def main():
    try:
        with open(LEDGER, encoding="utf-8") as f: ledger = json.load(f)
    except Exception:
        ledger = {"episodes": []}
    # Combine the live ledger with mature archival shards; dedupe by candidate_id.
    by_id = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "state", "outcome_archive", "*.json"))):
        with open(path, encoding="utf-8") as f:
            for episode in json.load(f).get("episodes", []):
                by_id[episode["candidate_id"]] = episode
    for episode in ledger.get("episodes", []):
        by_id[episode["candidate_id"]] = episode
    out = promotion_gate({"episodes": list(by_id.values())}, now_ts=int(time.time()))
    out["archive_episode_n"] = max(0, len(by_id) - len(ledger.get("episodes", [])))
    out["mode"] = "REVIEW_GATE_ONLY"
    out["production_mutation"] = False
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("promotion gate:", out["status"], out.get("reason", ""))


if __name__ == "__main__": main()
