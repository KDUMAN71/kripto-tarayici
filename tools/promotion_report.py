"""Build OOS promotion eligibility report; never promotes automatically."""
import json, os, time
from research.promotion import promotion_gate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "state", "outcome_ledger.json")
REPORT = os.path.join(ROOT, "state", "promotion_report.json")


def main():
    try:
        with open(LEDGER, encoding="utf-8") as f: ledger = json.load(f)
    except Exception:
        ledger = {"episodes": []}
    out = promotion_gate(ledger, now_ts=int(time.time()))
    out["mode"] = "REVIEW_GATE_ONLY"
    out["production_mutation"] = False
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("promotion gate:", out["status"], out.get("reason", ""))


if __name__ == "__main__": main()
