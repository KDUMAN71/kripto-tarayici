"""Post-scan state maintenance.

Runs after scanner.main. It prunes stale Binance perpetual symbols conservatively
and rewrites state.json + compact state/summary.json. No Telegram or trading logic.
"""
from scanner import data
from scanner import state as ST


def run():
    st = ST.load()
    symbols = data.exchange_perp_symbols()
    if symbols is not None:
        ST.prune_known_symbols(st, symbols)
    ST.save(st)
    print(
        "STATE_HEALTH:",
        f"known={len(st.get('known_symbols', {}))}",
        f"open={len([1 for s in st.get('signals', {}).values() if s.get('status') in ST.OPEN_STATUSES])}",
        f"last_ok={st.get('last_ok_run', 0)}",
    )


if __name__ == "__main__":
    run()
