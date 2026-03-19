# Mean Reversion Redesign Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Backtest window: 2024-01-01 to 2024-12-31
- Baseline: mean_reversion_after_expansion parameter set 1 only
- Redesigns tested: exhaustion wick, failed follow-through

## 2. Compact comparison
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
| baseline_param_1 | 568 | 17.94 | -75.12 | 0.69 | 49448.55 | 93.06 |
| redesign_exhaustion_wick | 12 | -100.34 | -186.81 | 0.52 | 2241.67 | 86.47 |
| redesign_failed_follow_through | 126 | 14.48 | -102.24 | 0.68 | 12881.72 | 116.72 |
