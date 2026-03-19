# Fuller Validation Report: Liquidity Sweep Reversal

## Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Active variants only: `redesign_fast_rejection_base`, `redesign_fast_rejection_reentry_relief`
- Deprioritized and excluded from execution: `redesign_deep_reclaim`, `redesign_fast_rejection_hour_extension`, `redesign_fast_rejection_sweep_relief`, and all prior breakout / mean-reversion families.
- Research policy: fixed-logic evaluation only, no broad family search, no redesign iteration inside this run.

## Window results
| Variant | Window | Start | End | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | train | 2018-01-01 | 2022-12-31 | 43 | -50.62 | -130.01 | 0.67 | 6812.54 | -0.82 | 79.39 |
| redesign_fast_rejection_base | validation | 2023-01-01 | 2023-12-31 | 11 | 273.29 | 211.81 | 1.84 | 1093.94 | 2.13 | 61.48 |
| redesign_fast_rejection_base | test | 2024-01-01 | 2024-12-31 | 8 | 900.94 | 789.53 | 12.11 | 568.66 | 11.11 | 111.41 |
| redesign_fast_rejection_base | holdout | 2025-01-01 | 2025-12-31 | 7 | -12.12 | -86.89 | 0.75 | 2387.19 | -0.25 | 74.77 |
| redesign_fast_rejection_reentry_relief | train | 2018-01-01 | 2022-12-31 | 50 | -80.37 | -156.89 | 0.61 | 8376.78 | -0.94 | 76.51 |
| redesign_fast_rejection_reentry_relief | validation | 2023-01-01 | 2023-12-31 | 12 | 207.78 | 147.11 | 1.53 | 1389.13 | 1.27 | 60.68 |
| redesign_fast_rejection_reentry_relief | test | 2024-01-01 | 2024-12-31 | 9 | 741.72 | 631.11 | 5.74 | 630.43 | 9.01 | 110.61 |
| redesign_fast_rejection_reentry_relief | holdout | 2025-01-01 | 2025-12-31 | 10 | -122.87 | -189.89 | 0.48 | 3497.78 | -0.54 | 67.02 |

## Aggregate slices
| Variant | Aggregate slice | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | combined_oos | 19 | 537.56 | 455.06 | 3.58 | 1093.94 | 7.90 | 82.51 |
| redesign_fast_rejection_base | oos_plus_holdout | 26 | 389.57 | 309.15 | 2.40 | 2387.19 | 3.37 | 80.42 |
| redesign_fast_rejection_base | full_sample | 69 | 115.25 | 35.47 | 1.11 | 6812.54 | 0.36 | 79.78 |
| redesign_fast_rejection_reentry_relief | combined_oos | 21 | 436.62 | 354.54 | 2.64 | 1389.13 | 5.36 | 82.08 |
| redesign_fast_rejection_reentry_relief | oos_plus_holdout | 31 | 256.14 | 178.92 | 1.68 | 3497.78 | 1.59 | 77.22 |
| redesign_fast_rejection_reentry_relief | full_sample | 81 | 48.42 | -28.37 | 0.92 | 8376.78 | -0.27 | 76.78 |

## Fixed-parameter walk-forward windows
| Variant | Test start | Test end | Train trades | Validation trades | Test trades | Test return | Test PF | Passed |
|---|---|---|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | 2020-07-01 | 2020-12-31 | 25 | 4 | 1 | 975.95 | inf | True |
| redesign_fast_rejection_base | 2020-10-01 | 2021-03-31 | 27 | 2 | 2 | 371.69 | 1.62 | True |
| redesign_fast_rejection_base | 2021-01-01 | 2021-06-30 | 27 | 1 | 3 | -1733.07 | 0.00 | False |
| redesign_fast_rejection_base | 2021-04-01 | 2021-09-30 | 22 | 2 | 5 | 212.27 | 1.12 | True |
| redesign_fast_rejection_reentry_relief | 2020-07-01 | 2020-12-31 | 28 | 5 | 2 | 387.12 | 1.66 | True |
| redesign_fast_rejection_reentry_relief | 2020-10-01 | 2021-03-31 | 30 | 4 | 2 | 371.69 | 1.62 | True |
| redesign_fast_rejection_reentry_relief | 2021-01-01 | 2021-06-30 | 31 | 2 | 4 | -2279.53 | 0.00 | False |
| redesign_fast_rejection_reentry_relief | 2021-04-01 | 2021-09-30 | 27 | 2 | 6 | -344.10 | 0.85 | False |

## Variant scorecard
| Variant | Total trades | Trades by split (train / validation / test / holdout) | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade | Walk-forward pass rate | Stress-test pass rate | Classification |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| redesign_fast_rejection_base | 69 | 43 / 11 / 8 / 7 | 115.25 | 35.47 | 1.11 | 6812.54 | 0.36 | 79.78 | 75.00% | 80.00% | Rejected |
| redesign_fast_rejection_reentry_relief | 81 | 50 / 12 / 9 / 10 | 48.42 | -28.37 | 0.92 | 8376.78 | -0.27 | 76.78 | 50.00% | 80.00% | Rejected |

## Conclusions
- redesign_fast_rejection_base: combined OOS trades=19, PF=3.58, return/maxDD=7.90, holdout trades=7, holdout PF=0.75, walk-forward pass rate=75.00%, stress pass rate=80.00%.
- redesign_fast_rejection_reentry_relief: combined OOS trades=21, PF=2.64, return/maxDD=5.36, holdout trades=10, holdout PF=0.48, walk-forward pass rate=50.00%, stress pass rate=80.00%.
- Base candidate verdict: rejected under the fuller fixed-logic pipeline, so the earlier promise does not survive a stricter evidence bar.
- Reentry relief verdict: drop it, because the fuller pipeline does not justify keeping it as an active shadow arm.
- Active-candidate verdict: neither variant deserves to remain active after this fuller validation run.
