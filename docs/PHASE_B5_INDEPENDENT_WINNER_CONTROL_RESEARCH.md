# Phase B5 — Independent Winner vs Matched Non-Winner Research

## Objective
Discover which *point-in-time* characteristics distinguish profitable future opportunities from otherwise comparable non-winners. Do not presume the existing scanner's indicators, thresholds, patterns, or score are correct. Run this in parallel with the current engine gate-attribution audit.

## Cohort construction
- Positive labels: mature upside and downside episodes across 6h/1d/3d/7d/14d/30d/60d, with magnitude bins, including >=100% and >=200% events.
- Controls: same UTC timestamp (or nearest fully closed candle), similar pre-event quote-volume band, contract age and data availability; no qualifying directional outcome within the same fully mature horizon.
- Include hard negatives: similar early momentum/volume/structure but no subsequent major move.
- One event per underlying overlapping symbol/direction episode per fold; avoid repeated anchors leaking between train/test.
- Controls must be sampled from the contemporaneous *entire tradeable universe*, not only candidates already admitted by our scanner.
- Treat spot listings separately from perpetual listings; delisted/newly-listed coverage must be audited.
- Unknown historical derivatives/news data remain missing, never filled from today's API.

## Independent feature families
Price structure (HH/HL, LL/LH, breakout, consolidation); multi-horizon return and acceleration; BTC/sector relative strength; quote-volume and relative-volume trajectories; volatility compression/expansion, ATR, ADX/DMI; moving-average slopes; distance to HTF support/resistance; futures OI/funding/taker where point-in-time available; spot participation; listing age; regime and cross-sectional breadth. Include null/availability indicators.

## Evaluation
For each timestamp and horizon, compare distributions, missingness, base rates, standardized effect sizes and conditional lift vs matched controls. Fit simple interpretable baselines before complex models. Compare logistic/regularized and tree models only if OOS evidence justifies complexity. Feature importance must be checked for stability and correlation; do not interpret association as causality.

Use purged, embargoed chronological walk-forward splits; group overlapping episodes and symbols to prevent leakage. Select thresholds on training/calibration only; keep untouched OOS. Evaluate precision@10 per contemporaneous slice, opportunity-weighted recall, false-positive rate, lead time, executable entry conversion, simulated realized R after fees/slippage/funding, drawdown and portfolio correlation. Evaluate both directions and different horizons separately before aggregation.

## Falsification checks
- If an indicator appears equally often in controls, reject it as a useful standalone discriminator.
- Test whether apparent signals are merely market-wide BTC/sector moves.
- Test whether features work only after the move is already underway.
- Report non-tradeable hindsight opportunities separately.
- Do not automatically relax discovery/ACTIVE gates or deploy a model based on these results.

## Deliverables
1. Matched cohort manifest with selection reasons and maturity checks.
2. Snapshot-level winner/control feature table and missingness audit.
3. Distribution/effect-size/lift and trajectory report.
4. OOS interpretable model comparison.
5. Actionable proposals to current discovery/ranking/entry/exit system, each tied to a quantified failure and test.
6. Update PROJECT_MASTER_INSTRUCTIONS.md after verified results.

**Status: research design recorded; dataset, comparisons, and OOS results not yet produced.**
