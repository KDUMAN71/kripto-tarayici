# Opportunity-to-Profit — Phase A Results

Source: GitHub Actions `opportunity-census-60d-v1` run #2 (37592186840), generated 2026-10-07.
Universe: 525 current Binance perpetual symbols, no fetch failures.
Raw research anchors: 28,614 daily symbol anchors. Future excursion is label-only.

## Executive conclusion
The market did **not** lack opportunity. The prior system failed to monetize an opportunity-rich regime.

Unique symbols with mature upside excursion:
| Horizon | >=50% | >=100% | >=200% |
|---|---:|---:|---:|
| 7d | 240 | 79 | 31 |
| 14d | 305 | 104 | 38 |
| 30d | 324 | 127 | 43 |

Unique symbols with mature downside excursion:
| Horizon | >=25% down | >=50% down | >=70% down |
|---|---:|---:|---:|
| 7d | 187 | 41 | 14 |
| 14d | 209 | 51 | 17 |
| 30d | 208 | 52 | 17 |

Examples of maximum mature upside excursion:
- LSKUSDT: ~2231%/7d, ~2308%/14d, ~3071%/30d.
- AKEUSDT: ~961%/7d, ~1027%/14d, ~2059%/30d.
- TUTUSDT: ~941%.
- USELESSUSDT: ~400%/7d, ~471%/14d, ~835%/30d.
- QNTUSDT: ~463%/7d, ~530%/14d, ~515%/30d.
- MARSCOINUSDT: ~284% on 7d/14d/30d best mature anchors.

These are hindsight opportunity labels, NOT claims that the full move was tradeable from the anchor.

## Important methodology caveat
Daily anchors overlap the same underlying trend. Anchor counts therefore must not be interpreted as independent trades. Phase B must deduplicate into opportunity episodes and replay the contemporaneous pipeline to determine the realistically tradeable portion.

Long-horizon right-censoring is explicitly tracked. Use mature-only counts for complete-horizon comparisons. Current exchangeInfo also creates survivorship bias because delisted contracts are absent.

## Phase A decision
The central failure question is now:
**Why did an ACTIVE-only trading system fail to convert a market containing dozens of distinct 100–200%+ moves, plus many large downside moves, into realized profit?**

The next analysis must not optimize only +10% runner recall.

## Phase B required replay
Build deduplicated opportunity episodes and replay:
UNSEEN -> DISCOVERED -> PRE_RUNNER -> RANKED -> SETUP -> VETO/WATCH -> ACTIVE -> MANAGEMENT -> EXIT.

Prioritize economic significance while retaining smaller high-R opportunities:
1. all unique >=200% mature 7d/14d/30d upside opportunities;
2. all unique >=100% mature opportunities;
3. representative 50–100% opportunities;
4. major downside/SHORT opportunities;
5. smaller moves that offered high realistic R;
6. historical system ACTIVE trades/stops for direct comparison.

For each episode record first detectable/tradeable time, every gate outcome, ACTIVE conversion, entry delay, remaining move, structural stop, spot/futures suitability, realized/hypothetical R and available-R capture.

Phase B must use time-slice information only. Future excursion may label outcomes but cannot enter decisions.
