"""Profit-oriented performance metrics for ACTIVE trades."""
from __future__ import annotations


def trade_metrics(trades):
    rs = [float(t["pnl_r"]) for t in trades if t.get("pnl_r") is not None]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    captured = []
    for t in trades:
        pnl = t.get("pnl_r")
        mfe_pct = t.get("mfe_pct")
        entry, sl = t.get("entry"), t.get("sl")
        if pnl is None or not mfe_pct or not entry or sl is None:
            continue
        risk_pct = abs(float(entry)-float(sl))/float(entry)*100
        if risk_pct > 0:
            mfe_r = float(mfe_pct)/risk_pct
            if mfe_r > 0: captured.append(float(pnl)/mfe_r)
    return {
        "trades": len(rs),
        "expectancy_r": sum(rs)/len(rs) if rs else None,
        "profit_factor": gross_win/gross_loss if gross_loss else (None if not gross_win else float("inf")),
        "win_rate": len(wins)/len(rs) if rs else None,
        "max_drawdown_r": max_dd if rs else None,
        "net_r": sum(rs) if rs else None,
        "captured_mfe_ratio": sum(captured)/len(captured) if captured else None,
    }
