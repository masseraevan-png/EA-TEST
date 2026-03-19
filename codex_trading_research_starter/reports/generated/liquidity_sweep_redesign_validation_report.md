# Liquidity Sweep Reversal Validation Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Active candidate family: liquidity_sweep_reversal only
- Validation style: bounded, fixed-logic multi-window check
- Optimization/search policy: no further optimization, no broad parameter search

## 2. Window-by-window results
| Variant | Window | Start | End | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| redesign_deep_reclaim | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 2 | 370.76 | 320.06 | 2.13 | 0.00 | 50.70 |
| redesign_fast_rejection | earlier_in_sample_style | 2022-01-01 | 2022-06-30 | 2 | 1079.91 | 1032.91 | inf | 0.00 | 47.00 |
| redesign_deep_reclaim | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 1 | -499.93 | -639.13 | 0.00 | 0.00 | 139.20 |
| redesign_fast_rejection | later_out_of_sample_style | 2024-01-01 | 2024-06-30 | 5 | 768.63 | 650.29 | 6.72 | 0.00 | 118.34 |
| redesign_deep_reclaim | recent_holdout_style | 2025-01-01 | 2025-06-30 | 1 | -49.59 | -104.69 | 0.00 | 0.00 | 55.10 |
| redesign_fast_rejection | recent_holdout_style | 2025-01-01 | 2025-06-30 | 3 | 643.71 | 587.61 | 110.43 | 16.11 | 56.10 |

## 3. Cross-window summary
| Variant | Total trades | Positive net windows | Mean net PnL/trade | Median net PnL/trade | Mean profit factor | Worst max drawdown | Mean explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|---:|
| redesign_deep_reclaim | 4 | 1/3 | -141.25 | -104.69 | 0.71 | 0.00 | 81.67 |
| redesign_fast_rejection | 10 | 3/3 | 756.94 | 650.29 | inf | 16.11 | 73.81 |
