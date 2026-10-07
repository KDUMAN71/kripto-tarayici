# Opportunity-to-Profit Phase B3 — Point-in-Time Snapshot Findings

Source: workflow run 37642567379, artifact opportunity-phase-b3-snapshots-v1.
Canonical universe: 1,688 opportunities. Replay cohort: 574. All 274 >=100% and all 90 >=200% canonical labels were retained.

## Key finding 1 — giant opportunities are often NOT obvious momentum events before the move
For >=200% labels, median point-in-time features were modest around the episode start:
- T-72h opportunity-score median ~2.88; 1h volume ratio ~1.02x.
- T-24h score ~2.46; volume ratio ~0.87x.
- T-12h score ~1.50; volume ratio ~0.57x.
- T-6h score ~1.96; volume ratio ~0.76x.
- T-1h score ~2.52; volume ratio ~0.94x.
- T0 score ~2.90; volume ratio ~0.86x.
Median 3h/6h returns were generally near zero around T-24h..T0.

Implication: a scanner that waits for strong short-term momentum/volume expansion as the primary admission signal will systematically miss many large later moves. Trajectory ranking remains useful for some opportunity families, but it cannot be the only discovery path.

## Key finding 2 — absolute liquidity gates remain a major blind spot
For >=200% labels, fraction of snapshots above:
- $2M historical 24h quote volume: roughly 54–60% across T-12h..T0.
- $8M: only roughly 19–24% near T-12h..T0.

For >=100% labels, $2M coverage is roughly 61–64%, while $8M is only ~25–29% around the same period.

Implication: even the current $2M broad-discovery floor can exclude a material share of the highest-upside opportunities before they become obvious. This does NOT mean trading illiquid coins indiscriminately. It means discovery eligibility and execution/liquidity risk need different treatment, including a new/newly-liquid opportunity path.

## Key finding 3 — current opportunity score is not a sufficient universal detector
Among >=200% snapshots, score >=3 was present in only ~28–48% depending on snapshot; score >=5 in only ~10–29%.
Therefore opportunity_score should remain one ranking feature, not a universal opportunity gate.

## Methodology caveat
The B3 episode start is derived from hindsight census anchors, not necessarily the true market move start. Results describe visibility around the labeled economic opportunity window, not perfect entry timing. Future excursion labels never enter snapshot features.

## Phase B4 questions
1. Which opportunities fail current $2M discovery eligibility?
2. Among eligible opportunities, which would be starved by ranking/deep-scan capacity?
3. Which opportunity families have low momentum score but later large excursion?
4. Can structural/base/compression/new-listing features identify those earlier without flooding ACTIVE signals?
5. Which historical context fields can be reconstructed point-in-time for full engine replay?

Do not lower execution safety merely because discovery coverage is poor.
