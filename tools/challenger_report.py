"""Build shadow challenger report. Does not modify production config."""
import json, os
from research.challenger import compare

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "state", "outcome_ledger.json")
REPORT = os.path.join(ROOT, "state", "challenger_report.json")


def main():
    try:
        with open(LEDGER, encoding="utf-8") as f: ledger = json.load(f)
    except Exception:
        ledger = {"episodes": []}
    out = {"mode": "SHADOW_ONLY", "production_mutation": False,
           "policies": compare(ledger)}
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("challenger:", out["policies"])


if __name__ == "__main__": main()
