# Trade lifecycle accounting audit — 2026-10-12

Inspected `scanner/state.py` in main, especially `_record_trade` and `update_active`.

## Verified behavior
- TP1/TP2 hits set boolean flags and send `TP GÖRÜLDÜ` messages.
- No actual order execution, fill quantity, partial close fraction, or realized partial PnL is recorded.
- `_record_trade` calculates `pnl_r` from one full entry-to-exit price difference, assuming the entire position closes at the final exit.
- If TP1 is touched and hard SL later hits, outcome is STOPPED/-1R even with `tp1_hit=true`. ICP is consistent with this *signal-plan* accounting, not proof of missing booked profit.
- Stop check precedes target checks in `update_active`; when the same sampled 15m range spans stop and target, stop wins by convention. This is conservative but not a reconstruction of true intrabar sequence.
- Telegram text `TP1 GÖRÜLDÜ` is an observed target-touch alert, **not proof of a filled partial take-profit order**.
- There is no evidence in this module of exchange order placement. Treat the system as advisory/simulated until a broker execution/fill ledger is separately verified.

## Required next engineering changes
1. Define execution modes explicitly: SIGNAL_ONLY vs PAPER_FILL vs VERIFIED_LIVE_FILL.
2. Record target touches separately from fills and from realized PnL.
3. For paper simulation, specify explicit position fractions and fee/slippage/funding assumptions, and apply deterministic candle-order rules or mark ambiguous.
4. For real trading, only compute realized PnL from actual exchange fills.
5. Add tests: TP1 touched then SL, partial TP1 fill then SL, same-candle TP1/SL ambiguity, final TP with no partials, SHORT parity.
6. Keep structural stop/risk checks intact. Do not claim profitable execution from target touches.

## Current status
Audit completed. Execution accounting redesign is NOT yet implemented or promoted. No production threshold changes.
