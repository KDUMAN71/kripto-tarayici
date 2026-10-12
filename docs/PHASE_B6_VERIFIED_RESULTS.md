# Phase B6 — Verified matched-feature results

Source: successful GitHub Actions run 38153953459 (2026-10-11), artifact phase-b6-feature-results.

5,056 original pairs; 5,033 valid feature pairs; 1,679 unique opportunities; 524 symbol histories loaded, no missing symbols.

| Feature | Winner median | Matched control median | Fraction winner > control |
|---|---:|---:|---:|
| 3h return | -0.281% | -0.118% | 45.1% |
| 6h return | -0.325% | -0.026% | 46.0% |
| 24h return | -0.967% | -0.223% | 42.7% |
| BTC-relative 6h return | -0.194% | -0.006% | 46.0% |
| Relative volume 6h | 0.793x | 0.883x | 43.8% |
| 24h price range | 7.512% | 7.306% | 53.0% |
| Compression ratio | 0.744 | 0.776 | 47.5% |

## Interpretation
At the current hindsight-labeled opportunity anchors, simple positive momentum and volume expansion are not universal discriminators. Do not conclude that negative momentum is predictive: anchors may not represent the true move onset, controls are 7-day negatives, overlapping opportunities remain and features were not OOS validated. These are associations, not executable trade rules.

## Required follow-up
Phase B7 must compare *trajectories* at multiple pre-event timestamps for winners and matched controls, report missingness and first separation time, and use strict closed-candle data. Phase B8 must perform purged chronological OOS validation including precision/false positives and economic tradeability. Do not tune production on B6 alone.
