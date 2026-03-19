# Liquidity Sweep Reversal Redesign Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Bounded backtest window: 2024-01-01 to 2024-12-31
- Active candidate family: liquidity_sweep_reversal / redesign_fast_rejection only
- Deprioritized: redesign_deep_reclaim and prior breakout/mean-reversion families

## 2. Baseline post-mortem
| Variant | Trades | Avg hold (hrs) | Avg stop (pips) | Avg size (lots) | Gross PnL/trade | Net PnL/trade | Spread/Slip/Comm per trade | Win rate | Avg winner | Avg loser |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_param_0 | 137 | 0.37 | 4.97 | 11.28 | 57.04 | -55.73 | 22.55/11.28/78.94 | 37.23% | 845.72 | -590.31 |
| baseline_param_1 | 74 | 0.46 | 5.44 | 10.50 | 24.20 | -80.75 | 20.99/10.50/73.47 | 35.14% | 866.09 | -593.63 |

## 3. Proposed redesigns
- **fast_rejection_base**: Current candidate: sharp wick-led rejections during liquid hours, meaningful reclaim body, and quick exits to avoid paying costs on weak follow-through.
- **fast_rejection_reentry_relief**: Loosen only the reclaim-depth thresholds slightly to admit bars that still reject decisively but do not close quite as deep inside the range.
- **fast_rejection_hour_extension**: Keep the base pattern unchanged but add the 11:00 hour to test whether one extra liquid hour can add modest frequency without opening the floodgates.
- **fast_rejection_sweep_relief**: Slightly reduce the minimum sweep and wick/body strictness while keeping the same rejection family and quick-exit structure.

## 4. Implemented bounded test results
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
| redesign_fast_rejection_base | 8 | 900.94 | 789.53 | 12.11 | 568.66 | 111.41 |
| redesign_fast_rejection_reentry_relief | 9 | 741.72 | 631.11 | 5.74 | 630.43 | 110.61 |
| redesign_fast_rejection_hour_extension | 10 | 613.36 | 513.23 | 4.05 | 1113.42 | 100.13 |
| redesign_fast_rejection_sweep_relief | 11 | 341.01 | 215.19 | 1.75 | 1348.55 | 125.82 |
