"""Conservative portfolio admission gate for advisory ACTIVE signals."""
MAX_ACTIVE=10

def active_count(signals):
    return sum(1 for s in signals.values() if s.get("status")=="ACTIVE")

def can_activate(signals,limit=MAX_ACTIVE):
    return active_count(signals)<limit

def priority(sig):
    """Deterministic provisional ranking, NOT a calibrated expected-profit model."""
    return (float(sig.get("rr2") or sig.get("rr1") or 0),
            float(sig.get("score") or 0))

def rank_active(candidates):
    return sorted(candidates,key=lambda pair:(-priority(pair[1])[0],-priority(pair[1])[1],pair[0]))
