"""Build bounded failure-attribution report from outcome ledger."""
import json, os
from research.failure_attribution import attribute_ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "state", "outcome_ledger.json")
REPORT = os.path.join(ROOT, "state", "failure_attribution.json")


def main():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception:
        ledger = {"episodes": []}
    out = attribute_ledger(ledger)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("failure attribution:", out["counts"])


if __name__ == "__main__":
    main()
