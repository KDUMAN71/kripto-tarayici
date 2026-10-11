# Phase B5 — Verified matched-control results

Source: GitHub Actions run 37736500511 (successful), artifact phase-b5-independent-results.

- 525 current perpetual symbols, no data-fetch failures.
- 1,688 canonical opportunities requested; 1,686 matched.
- 5,056 winner/non-winner pairs; two opportunities without a suitable match.
- Same-time, similar-volume matching; negative outcome defined on a fully observed seven-day window.

| Metric | Winner median | Control median | Winner greater in pairs |
|---|---:|---:|---:|
| 24h quote volume | $3,590,310.64 | $3,592,235.97 | 51.44% |
| 24h price return | -0.973% | -0.284% | 44.56% |
| History bars | 576 | 576 | 0.71% |

These descriptive results do not establish a profitable trading signal. Absolute volume was matched by design. Positive prior-24h momentum is not a universal precursor.

Limitations: current-listed-contract survivorship, overlapping economic episodes, 7-day controls not necessarily negatives at longer horizons, potential late anchors, common data-start effects, no time-slice OOS and no executable/realized-R evaluation.

Next: compare closed-candle 3h/6h trajectory, BTC-relative returns, volume participation, volatility and structure for BOTH groups; use purged time-slice OOS. Keep production unchanged until validated.
