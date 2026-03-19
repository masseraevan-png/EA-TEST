# Liquidity Sweep Reversal Validation Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Active candidate family: liquidity_sweep_reversal / redesign_fast_rejection only
- Validation style: bounded, fixed-logic multi-window check
- Optimization/search policy: no broad parameter search; only a small controlled neighborhood around fast_rejection
- Deprioritized: redesign_deep_reclaim and prior breakout/mean-reversion families

## 2. Window-by-window results
| Variant | Window | Start | End | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 2 | 1079.91 | 1032.91 | inf | 0.00 | 47.00 |
| redesign_fast_rejection_reentry_relief | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 3 | 550.53 | 494.87 | 3.59 | 0.00 | 55.67 |
| redesign_fast_rejection_hour_extension | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 2 | 1079.91 | 1032.91 | inf | 0.00 | 47.00 |
| redesign_fast_rejection_sweep_relief | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 4 | 267.36 | 225.46 | 1.84 | 542.33 | 41.90 |
| redesign_fast_rejection_base | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 5 | 768.63 | 650.29 | 6.72 | 0.00 | 118.34 |
| redesign_fast_rejection_reentry_relief | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 5 | 768.63 | 650.29 | 6.72 | 0.00 | 118.34 |
| redesign_fast_rejection_hour_extension | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 7 | 400.88 | 300.16 | 2.25 | 569.18 | 100.71 |
| redesign_fast_rejection_sweep_relief | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 7 | 380.45 | 245.90 | 1.90 | 702.98 | 134.54 |
| redesign_fast_rejection_base | recent_holdout_style | 2025-01-01 | 2025-06-30 | 3 | 643.71 | 587.61 | 110.43 | 16.11 | 56.10 |
| redesign_fast_rejection_reentry_relief | recent_holdout_style | 2025-01-01 | 2025-06-30 | 4 | 443.38 | 395.70 | 9.13 | 178.54 | 47.67 |
| redesign_fast_rejection_hour_extension | recent_holdout_style | 2025-01-01 | 2025-06-30 | 3 | 643.71 | 587.61 | 110.43 | 16.11 | 56.10 |
| redesign_fast_rejection_sweep_relief | recent_holdout_style | 2025-01-01 | 2025-06-30 | 4 | 574.88 | 517.58 | 124.01 | 16.83 | 57.30 |

## 3. Cross-window summary
| Variant | Total trades | Positive net windows | Mean net PnL/trade | Median net PnL/trade | Mean profit factor | Worst max drawdown | Mean explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | 10 | 3/3 | 756.94 | 650.29 | inf | 16.11 | 73.81 |
| redesign_fast_rejection_hour_extension | 12 | 3/3 | 640.23 | 587.61 | inf | 569.18 | 67.94 |
| redesign_fast_rejection_reentry_relief | 12 | 3/3 | 513.62 | 494.87 | 6.48 | 178.54 | 73.89 |
| redesign_fast_rejection_sweep_relief | 15 | 3/3 | 329.65 | 245.90 | 42.58 | 702.98 | 77.91 |
