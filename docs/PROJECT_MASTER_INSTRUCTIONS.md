# Kripto Tarayici — Project Master Instructions

> Living source of truth for KDUMAN71/kripto-tarayici.
> Current position: Broad Discovery implementation (actual GitHub PR #21; roadmap numbering shifted by continuity PR #20).
> Last research milestone: V3.5 30-day pre-runner replay V3 completed; 234 runners + 234 matched controls.

## 0. New ChatGPT session protocol
Before changing code:
1. Read this file completely.
2. Inspect current main, open PRs, recent merged PRs and relevant tests.
3. Repository state + this file are authoritative; chat memory is supporting context only.
4. Never redo merged work or revive superseded branches.
5. Report conflicts between this file and current code before production changes.
6. Every roadmap PR that changes architecture/evidence/status must update this file.

Suggested prompt:
"Read docs/PROJECT_MASTER_INSTRUCTIONS.md in KDUMAN71/kripto-tarayici, verify it against current main/open PRs, and continue from CURRENT ROADMAP POSITION. Do not redo merged work."

## 1. Mission
Build a Binance Futures opportunity system that detects high-value moves early enough to trade, avoids low-quality suggestion spam, separates discovery from execution, uses real structural invalidation/R:R, learns from false positives and false negatives, and promotes changes only after replay + out-of-sample evidence.

Success metrics: catchable runner recall; first-third detection rate; detection lead time; false-positive rate; ACTIVE expectancy (R); profit factor; MAE/MFE; stop-out-then-MFE; performance by setup family. Research target: >=50% of catchable Top-10 runners should reach EARLY/WATCH in the first third of the move. Production ACTIVE additionally requires positive OOS expectancy.

## 2. Non-negotiable rules
1. Discovery != execution.
2. Never tighten structural SL to manufacture R:R. Wait for better entry or reject.
3. If HTF support/resistance materially supports the thesis, hard SL must invalidate that thesis, not fire before it.
4. S/R are zones; use structural boundary + volatility/ATR buffer.
5. Recompute all R:R after entry/SL geometry changes.
6. Keep TP1 >=1.5R and TP2 >=2R unless later OOS evidence explicitly changes them.
7. Missed opportunity and losing trade are different failure classes.
8. Research labels may use future data; features at T may use only data available at/before T.
9. Never promote a threshold from one anecdotal coin.
10. Never call model advantage win probability unless calibrated.
11. Discovery improvements must not bypass execution safeguards.
12. Broad/hidden discovery must not automatically create Telegram alerts.
13. Production policy never silently self-modifies; learning produces challengers, promotion is explicit.
14. Verify current main before coding; do not duplicate merged work.
15. Every architecture/roadmap PR updates this document.

## 3. Target architecture
Broad Discovery -> PRE_RUNNER hidden watchlist -> Opportunity Ranking -> EARLY/WATCH -> Execution Gate -> RETEST_WAIT/ACTIVE -> Trade Management -> Outcome Ledger/Autopsy -> Offline Learning -> Challenger -> Calibration/OOS -> Explicit Promotion.

Goal: high discovery recall + low ACTIVE false-positive rate.

## 4. Historical cases / lessons
- USELESSUSDT: valid double structure missed by narrow pivot logic. PR #5 expanded detect_double() with broader pivot search, ATR/% tolerance, separation and neckline-depth guards.
- BICOUSDT: false breakout/reclaim class. Treat breakout/reclaim as lifecycle with 15m confirmation, not a mechanical recent-candle label. Relevant PRs #2/#9/#10.
- LITUSDT: HTF obstacle/invalidation and R:R geometry can disagree. Thesis -> invalidation -> targets -> R:R must be one geometry.
- HBARUSDT: HTF support ~0.101535 while hard SL ~0.101668. A normal support test could stop a LONG whose thesis relied on that support. PR #17 binds nearby thesis S/R to structural SL boundary + ATR buffer and recomputes R:R; bad corrected geometry cannot remain ACTIVE by tightening SL.
- METISUSDT: autopsy recorded 18 liquidity rejections, ~3M 24h quote volume vs hard 8M discovery floor. It died before pattern/execution evaluation. Static absolute liquidity is wrong as the first opportunity gate.
- RECALLUSDT: initially no autopsy trace despite symbol presence. Missing trace is an observability failure. PR #18 adds missed-opportunity gate tracing without admitting research watchlist symbols to execution.

## 5. Reverse-engineering evidence
Research chain:
- #14: label/feature separation, MAE/MFE, initial 30d lab.
- #15: episode-first V2; candle-close timing, dedupe, daily cap, 72h warmup, matched controls, BTC-relative, point-in-time OI/funding.
- #16: V3 methodology branch; later superseded due stale history.
- #19: clean V3 port onto current main; T-30m/T-15m and point-in-time derivatives at every snapshot.

Completed workflow: v3.5-reverse-engineering-v3, run #4, artifact v35-prerunner-replay-v3.
Sample: 234 runner + 234 matched control events.
Snapshots: T-24h, -12h, -6h, -3h, -1h, -30m, -15m, T0.
T0/+10% threshold-cross is an outcome/research anchor, NOT assumed true move start.

Accepted findings:
1. 8M is too strict as hard discovery floor: ~36.3% runners below it T-24h, ~25.6% around T-6h, ~17.9% even T0.
2. A ~2M research/discovery floor retains roughly 89.7% of runners around T-6h. This does NOT authorize trading every 2M-volume coin.
3. 1h vol-ratio >=1.8x is too strict for early discovery: T-6h runner median ~1.21x vs control ~0.96x.
4. Useful separation appears in trajectory into T-6h: runner median 3h return ~+3.38% vs control ~+0.57%; 6h ~+6.58% vs ~+1.51%; BTC-relative strength also separates.
5. Separation is not monotonic near T-3h/T-1h; use feature trajectories/state transitions, not only point thresholds.
6. Hard |24h change| >25% discovery rejection is suspect: legacy proxy passed ~54.7% runners vs ~80.3% controls. Large movers can still offer continuation/retest.
7. Taker/OI remain context/confirmation; dataset did not establish them as standalone discovery gates.

Research does NOT yet prove: loosening ACTIVE rules; 2M as final execution liquidity; one universal pump formula; positive ACTIVE expectancy for a new policy; automatic self-modification.

## 6. Production safeguards to preserve
Execution vetoes; breakout/retest/hold lifecycle; EMA/MA checks; 15m/1h taker context; OI collapse checks; live risk; HTF location; LONG/SHORT parallel decision; structural targets; real invalidation; TP1>=1.5R and TP2>=2R; obstacle checks; retest lifecycle; breakout-now + safer retest re-entry; HBAR/LIT thesis-SL integrity.

## 7. Relevant PR history
- #2 MERGED 5ce5d67 — V3.2 execution QA/veto.
- #4 MERGED 96defd3 — deterministic targets + real invalidation SL.
- #5 MERGED 8f3df95 — double pattern recall.
- #6 MERGED d8d251a — V3.3 HTF decision engine.
- #7 OBSOLETE OPEN — first state-health attempt; superseded by #8; close it.
- #8 MERGED edc9a24 — safe state summary/health.
- #9 MERGED ec4d14b — preserve retest watches.
- #10 MERGED 793f0ca — breakout entry + retest re-entry.
- #12 MERGED f8f6332 — heartbeat watchdog.
- #14 MERGED c407c7e — V3.5 reverse-engineering lab.
- #15 MERGED 27fb66d — episode-first replay V2.
- #16 CLOSED/SUPERSEDED — stale V3 branch, replaced by #19.
- #17 MERGED dd2805b — HTF thesis <-> structural SL integrity.
- #18 MERGED d90851b — METIS/RECALL gate trace.
- #19 MERGED 289b27a — pre-runner replay V3 current-main port.

## 8. CURRENT ROADMAP POSITION: implementation PR #21 -> #28

### #21 Broad Discovery / Opportunity Universe
Goal: stop killing runners before opportunity analysis.
Direction: separate discovery liquidity from execution liquidity; test ~2M discovery floor; 8M no longer first hard opportunity gate; trajectory inputs replace overly strict single-point prefilter; >25% movers not automatically discarded from discovery; preserve young-coin/API/execution safety.
Acceptance: replay recall improves; API/deep scan bounded; no automatic Telegram increase; ACTIVE rules unchanged; METIS-like regression; update this file.

### #22 Hidden PRE_RUNNER Watchlist
Goal: recall without spam. Internal PRE_RUNNER retains feature trajectory/gate history. No normal trade alert. Deterministic promotion/demotion/expiry and autopsy trace.

### #23 Opportunity Ranking
Allocate expensive analysis to highest-value candidates. Inputs: 3h/6h trajectory, BTC-relative strength, relative volume/participation acceleration, HTF structure/pattern/compression. OI/taker/funding are supporting features unless further evidence proves hard gates. Avoid overfitting exact medians.

### #24 Execution Gate V3.5
Centralize thesis -> structural invalidation -> buffered SL -> live entry -> targets -> R:R -> obstacle -> spread/liquidity/slippage -> retest/hold -> taker/OI/EMA. If correct SL destroys R:R: RETEST_WAIT or reject; never tighten SL to save trade.

### #25 Outcome Ledger
Track PRE_RUNNER/WATCH/REJECTED/ACTIVE: candidate_id, detection features, lifecycle, rejection reason, hypothetical entry, structural SL, MAE, MFE, max future move, time-to-run, final outcome.

### #26 Failure Attribution / Missed Opportunity Learner
Classes: MISSED_RUNNER, LATE_DETECTION, FALSE_BREAKOUT, WRONG_DIRECTION, BAD_RR, PREMATURE_STOP, CORRECT_THESIS_BAD_EXECUTION. METIS = discovery-gate miss; historical HBAR = correct thesis/bad execution.

### #27 Challenger Learning
Offline/nightly challenger vs current policy. Production does not self-edit. Suggestions must be reproducible and optimize decision quality, not signal count.

### #28 Walk-forward / OOS Promotion
Use ~30d calibration and separate 30-60d OOS where data permits. Promote only if recall/lead time improve without unacceptable false positives and ACTIVE expectancy/profit factor/MAE remain acceptable.

## 9. Failure taxonomy
UNSEEN_UNIVERSE; DISCOVERY_GATE_REJECT; BUDGET_CAP_REJECT; PATTERN_MISS; RANKING_MISS; LOCATION_VETO; EXECUTION_CONFIRMATION_FAIL; BAD_GEOMETRY; LATE_ENTRY; PREMATURE_STOP; WRONG_DIRECTION; VALID_LOSS; DATA_OBSERVABILITY_FAILURE.
Never solve a discovery failure by weakening execution safety.

## 10. Development workflow
For every roadmap PR:
1. Inspect current main/open PRs.
2. Define exact failure class.
3. Add/identify regression cases.
4. Isolate research-only changes if evidence is incomplete.
5. Do not change unrelated thresholds in same PR.
6. Verify tests honestly; never claim CI if none ran.
7. PR body includes evidence, scope, non-goals, regression coverage, rollback implications.
8. QA before merge.
9. Update this document with implementation/results, PR/merge commit and next position.
Prefer small reversible PRs over a large rewrite.

## 11. Anti-lookahead / data rules
Labels may use future price; features at T cannot. Respect candle-close alignment. OI/funding/news must be point-in-time. No future pivots. Controls matched by time/liquidity and verified non-runner in outcome horizon. Report missing-data availability. Disclose delisted-contract survivorship bias.

## 12. User-facing principles
The user wants fewer useless suggestions, not fewer discovered opportunities. Hidden discovery may be broad; Telegram/trade recommendations remain selective. Prefer actionable early breakout/retest entries over post-pump reporting. Give structural invalidation, not arbitrary tight stops. Safer retest can beat chasing. Alternative direction plans require independent confirmation; no automatic flip.

## 13. Current status / next action
Completed: research foundation (#14/#15/#19), execution-geometry safety (#17), missed-opportunity observability (#18), 30d V3 replay run and evidence synthesis.
Next implementation PR: **#20 Broad Discovery / Opportunity Universe**.
Before #20, close obsolete PR #7 (superseded by merged #8).
Do not loosen ACTIVE execution thresholds in #20.

## 14. Maintenance rule
This file is part of the Definition of Done for implementation PRs #21-#28. A roadmap PR is incomplete if it materially changes architecture, evidence, invariants, or roadmap status without updating this document.
