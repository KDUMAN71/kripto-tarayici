# Kripto Tarayici — Project Master Instructions

> Living source of truth for KDUMAN71/kripto-tarayici.
> Current position: Profit-System Master Plan after V3.5 and PR #29.
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

## 1. Mission — the one objective that must not drift
**PRIMARY OBJECTIVE: MAKE MONEY.** Maximize robust, risk-adjusted realized profit by finding and correctly trading all types of actionable market opportunities, with extra priority to opportunities offering the greatest realistic profit potential.

No strategy, setup, timeframe, direction or instrument is the objective itself. Trend, reversal, breakout/retest, momentum, range, new-listing behavior, short-term trades, multi-week moves, spot, futures, LONG and SHORT are tools/opportunity families. We do not have to choose only one.

The system may be simple or complex. Complexity is justified only when evidence shows it materially improves profit capture, opportunity capture, risk control or execution quality. Simplicity is not a goal if it leaves money on the table; complexity is not a virtue if it does not improve results.

Discovery states are internal enabling machinery. PRE_RUNNER/EARLY/WATCH/rejected candidates exist to improve the quality and timing of actionable trades and learning. The user-facing product is an executable trade decision and subsequent position-management decision.

Primary production metrics: net R, expectancy R, profit factor, max drawdown R, captured available-R/MFE, profitable-opportunity capture, and stability across regimes/setup families. Discovery recall, detection lead time and runner capture are diagnostic metrics that explain why profit was made or missed.


## 1A. Opportunity philosophy and portfolio rule
The scanner must be **strategy-agnostic and opportunity-seeking**.

Examples of valid opportunities (not an exhaustive list):
- major multi-day / multi-week trend continuation;
- explosive momentum or breakout;
- breakout-retest continuation;
- reversal after genuine structural invalidation;
- range expansion;
- high-quality short opportunity;
- new/newly-listed coin with a tradeable entry;
- spot accumulation / longer-duration opportunity;
- futures swing or shorter-duration opportunity.

A +8% move that offers a clean 4R futures trade can be valuable. A +200% emerging trend can be far more valuable and must not be ignored merely because it does not fit a short-term pattern. Opportunity value, not category membership, determines priority.

**Concurrent ACTIVE cap: maximum 10 positions/recommendations.**
- The system never needs to fill 10 slots.
- If 1 valid opportunity exists, return 1.
- If 6 exist, return 6.
- If >10 exist simultaneously, rank all valid ACTIVE opportunities by realistic expected profitability/risk quality and return the best 10.
- Ranking must eventually incorporate expected return/available move, setup reliability, execution quality, structural risk, liquidity/cost, correlation/concentration and regime fit.
- The exact ranking formula must be calibrated from data; do not invent probability-like numbers without calibration.

Spot vs futures is an **execution/router decision after an opportunity is recognized**, not a discovery restriction. The same underlying opportunity may be suitable for spot, futures, both, or neither.

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
16. Never reduce the project objective to one opportunity family (e.g. +10% runners, mega-trends, double bottoms, futures-only).
17. Never optimize signal count. Optimize realized risk-adjusted profit and opportunity capture.
18. A stopped trade is not automatically a bad thesis: measure post-stop continuation before changing entry/SL logic.
19. A missed entry does not mean the coin/opportunity is dead; if the larger thesis remains valid, search for the next tradeable continuation/re-entry.
20. Maximum concurrent user-facing ACTIVE opportunities is 10; when more qualify, rank by profit/risk priority.

## 3. Target architecture
Broad Discovery -> PRE_RUNNER hidden watchlist -> Opportunity Ranking -> EARLY/WATCH -> Execution Gate -> RETEST_WAIT/ACTIVE -> Trade Management -> Outcome Ledger/Autopsy -> Offline Learning -> Challenger -> Calibration/OOS -> Explicit Promotion.

Architecture sub-goal: broad opportunity recall + selective, high-quality ACTIVE conversion. This serves the primary profit objective; it is not the objective itself.

## 4. Historical cases / lessons
- USELESSUSDT: valid double structure missed by narrow pivot logic. PR #5 expanded detect_double() with broader pivot search, ATR/% tolerance, separation and neckline-depth guards.
- BICOUSDT: false breakout/reclaim class. Treat breakout/reclaim as lifecycle with 15m confirmation, not a mechanical recent-candle label. Relevant PRs #2/#9/#10.
- LITUSDT: HTF obstacle/invalidation and R:R geometry can disagree. Thesis -> invalidation -> targets -> R:R must be one geometry.
- HBARUSDT: HTF support ~0.101535 while hard SL ~0.101668. A normal support test could stop a LONG whose thesis relied on that support. PR #17 binds nearby thesis S/R to structural SL boundary + ATR buffer and recomputes R:R; bad corrected geometry cannot remain ACTIVE by tightening SL.
- METISUSDT: autopsy recorded 18 liquidity rejections, ~3M 24h quote volume vs hard 8M discovery floor. It died before pattern/execution evaluation. Static absolute liquidity is wrong as the first opportunity gate.
- RECALLUSDT: initially no autopsy trace despite symbol presence. Missing trace is an observability failure. PR #18 adds missed-opportunity gate tracing without admitting research watchlist symbols to execution.


## 4A. Corrections to earlier project assumptions
These corrections are important because they prevent future sessions from repeating old mistakes.

1. **+10% runner is not the project objective.** It was a convenient research label for one reverse-engineering experiment. The market can produce +50%, +100%, +200%+ opportunities over longer horizons, and smaller moves can also be highly profitable with good futures execution.
2. **Mega-trend is also not the sole objective.** Large trends deserve high priority because of their profit potential, but the system must capture any robust profitable opportunity.
3. **Exit optimization alone is not the root problem.** During a market with many large moves, the system failed to convert enough opportunities into profitable ACTIVE trades. Discovery, ranking, entry, structural stop, re-entry and management all require end-to-end evaluation.
4. **Pre-stop MFE is insufficient for stop diagnosis.** DOGE/LIT/ZEN/HBAR examples show favorable movement before stop, but the key question is also what happened after stop. Post-stop +1h/+3h/+6h/+12h/+24h/+3d/+7d continuation must be measured.
5. **A fixed TP1/TP2/TP3 framework may leave major trends uncaptured.** It remains a valid execution model, but must be compared against partial realization + structural/volatility trailing and re-entry.
6. **Professional risk sequence:** thesis -> structural invalidation -> volatility buffer -> stop -> position size. Do not choose a convenient stop first and force the thesis around it.
7. **Strong movers must not be rejected simply because they already moved.** A large move can contain multiple continuation/retest entries.
8. **Spot and futures are both allowed.** Instrument choice follows opportunity and execution quality.
9. **User does not want internal watch states.** Telegram ordinary trade recommendations are ACTIVE-only; internal breadth may remain large.

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
- #20 MERGED de4ba0b — persistent project continuity/master instructions.
- #21 MERGED f5bfd8c — broad discovery universe.
- #22 MERGED 42877c1 — hidden PRE_RUNNER watchlist.
- #23 MERGED 0cd32cb — trajectory opportunity ranking.
- #24 MERGED 66214f6 — centralized thesis-aware execution geometry.
- #25 MERGED 8a4d8a2 — candidate outcome ledger.
- #26 MERGED 6c3e53f — failure attribution / missed-opportunity learner.
- #27 MERGED 68cd4c0 — shadow challenger learning.
- #28 MERGED 42fe6ee — OOS promotion review gate.
- #29 MERGED d616499 — profit-first objective and ACTIVE-only user signals.

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
**User-facing Telegram policy is ACTIVE-only.** PRE_RUNNER, EARLY, WATCH, early-pump and pump-radar observations are internal and must not create ordinary user alerts. Once ACTIVE, entry/SL/TP and subsequent TP/STOP/position-management messages remain user-facing because they are actionable. System/data-source health alerts may also remain.

Prefer actionable breakout/retest entries over post-pump reporting. Give structural invalidation, not arbitrary tight stops. Safer retest can beat chasing. Alternative direction plans require independent confirmation; no automatic flip.

## 13. Current status / next action
V3.5 roadmap #21-#28 is merged. Product objective was subsequently clarified: **profit first, ACTIVE-only user signals**.

Current implementation: Profit Objective & User Signal Policy.
- Telegram ordinary trade alerts: ACTIVE only.
- PRE_RUNNER/EARLY/WATCH/pump observations remain internal for discovery/learning.
- ACTIVE TP/STOP management and system health messages remain user-facing.
- Profit evaluation adds expectancy R, profit factor, net R, max drawdown R and captured-MFE ratio.
- Runner recall remains diagnostic, not the optimization objective.

Current work: **Phase A — 60-day comprehensive opportunity census**. Research branch adds multi-horizon LONG/SHORT excursion labels for 6h/1d/3d/7d/14d/30d/60d and magnitude bins through >200%, with explicit horizon-maturity/censoring metadata. After the real census artifact is generated and analyzed, proceed to Phase B full time-slice Opportunity-to-Profit replay. Do not narrow research back to +10% runners or one strategy family.


## 13A. Next research and development plan — Opportunity-to-Profit program

### Phase A — 60-day comprehensive opportunity census
Do not label only +10% events. Build a time-sliced census of meaningful money-making opportunities over the last 60 days, including both directions and multiple horizons.

At minimum segment forward moves by magnitude/horizon:
- meaningful short/swing opportunities;
- +10–25%;
- +25–50%;
- +50–100%;
- +100–200%;
- >200%;
- material downside/SHORT analogues.

Horizons should include intraday where useful plus 1d/3d/7d/14d/30d/60d. Include newly listed coins when data quality permits. The categories are analytical bins, not strategies.

For each opportunity determine whether it was realistically tradeable with information available at the time. Avoid hindsight-only entries.

### Phase B — full Opportunity-to-Profit replay
Replay the contemporaneous candidate universe through the real pipeline:

UNSEEN -> DISCOVERED -> PRE_RUNNER -> RANKED -> SETUP -> VETO/WATCH -> ACTIVE -> MANAGEMENT -> EXIT.

For every profitable opportunity record:
- first detectable timestamp;
- first tradeable timestamp;
- system detection timestamp;
- reason for every rejection/veto;
- whether ACTIVE was produced;
- entry delay and remaining move at entry;
- structural SL and normal volatility;
- spot/futures suitability;
- realized/hypothetical R under realistic execution;
- maximum available R and captured-R ratio.

Key metrics:
- Tradeable Opportunity Capture Rate;
- Profitable Capture Rate;
- high-value-opportunity weighted capture;
- ACTIVE conversion rate;
- entry delay / remaining-move-at-entry;
- net R, expectancy, PF, max DD;
- available-R vs realized-R.

Large opportunities should carry more economic importance than trivial moves, without allowing one hindsight outlier to dominate calibration.

### Phase C — complete stop autopsy
For every historical STOP, including DOGE/ENA-related cases where applicable, LIT, HBAR, ZEN and future stops, calculate post-stop path at:
+1h, +3h, +6h, +12h, +24h, +3d, +7d.

Classify:
- GOOD_STOP: thesis invalidated and continuation did not recover;
- PREMATURE_STOP: thesis remained broadly valid and price resumed strongly in trade direction;
- BAD_ENTRY: larger opportunity was correct but normal volatility/retest made the entry poor;
- WRONG_THESIS/DIRECTION;
- REENTRY_MISSED: first trade failed/expired but a later valid entry appeared and was not taken.

Do not widen stops blindly. Diagnose whether the solution is better entry, structural stop, volatility buffer, position sizing, re-entry, or rejection.

### Phase D — strategy/opportunity family evaluation
Use evidence to determine which opportunity families deserve dedicated detection/execution logic. Do not create a new engine merely because a pattern has a name. Add complexity only when it improves the profit objective.

Potential families may include trend continuation, breakout/retest, reversal, range expansion, momentum, new-listing behavior and spot accumulation, but this list is not binding.

### Phase E — ACTIVE ranking and max-10 portfolio selection
Once candidates pass execution quality, rank all simultaneously valid ACTIVE opportunities. Maximum concurrent ACTIVE recommendations/positions = 10. Do not force-fill.

The ranking model must be evaluated using realized/available R and portfolio risk, not raw opportunity score alone. Include correlation/concentration so ten highly correlated altcoin LONGs are not treated as ten independent bets.

### Phase F — position management / re-entry research
Compare current fixed-target behavior against realistic alternatives:
- partial profit;
- structural trailing;
- ATR/volatility trailing;
- trend persistence exits;
- re-entry after valid stop/failed first entry;
- spot hold vs futures swing where appropriate.

Choose management by OOS profit metrics, not by aesthetic preference.

### Phase G — promotion
Any production change follows time-slice replay, calibration/OOS separation, challenger comparison and explicit review. No automatic self-modification.

## 14. Maintenance rule
This file is a permanent part of the Definition of Done for all future architecture/research/production PRs. A PR is incomplete if it materially changes the objective, architecture, evidence, invariants, roadmap, opportunity taxonomy, execution policy or learning methodology without updating this document.
