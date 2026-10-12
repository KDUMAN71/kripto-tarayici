# Phase C — Post-stop continuation results

Source: successful GitHub Actions run 38226866255, artifact phase-c-post-stop-results.

11 STOPPED trades evaluated using 1h historical candles after the stop.

| Horizon | Mature stops | Recovered original entry | Reached original TP1 |
|---|---:|---:|---:|
| 1h | 11 | 5 | 0 |
| 3h | 11 | 5 | 0 |
| 6h | 11 | 5 | 0 |
| 12h | 11 | 6 | 0 |
| 24h | 11 | 7 | 1 |
| 3d | 10 | 9 | 2 |
| 7d | 8 | 8 | 4 |

Interpretation: recovery after stop is common in this sample, but does not itself prove invalid structural stops or executable re-entry. This audit uses 1h OHLC and cannot resolve intrabar event ordering. Small sample and selection bias apply.

Follow-up: classify structural thesis invalidation and realistic re-entry; separately audit partial TP accounting (ICP TP1 reached but trade logged -1R). No automatic stop widening.
