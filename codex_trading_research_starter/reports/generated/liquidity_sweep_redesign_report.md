# Liquidity Sweep Reversal Redesign Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Bounded backtest window: 2024-01-01 to 2024-12-31
- Active candidate family: liquidity_sweep_reversal only
- Deprioritized family: opening_drive_pullback

## 2. Baseline post-mortem
| Variant | Trades | Avg hold (hrs) | Avg stop (pips) | Avg size (lots) | Gross PnL/trade | Net PnL/trade | Spread/Slip/Comm per trade | Win rate | Avg winner | Avg loser |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_param_0 | 137 | 0.37 | 4.97 | 11.28 | 57.04 | -55.73 | 22.55/11.28/78.94 | 37.23% | 845.72 | -590.31 |
| baseline_param_1 | 74 | 0.46 | 5.44 | 10.50 | 24.20 | -80.75 | 20.99/10.50/73.47 | 35.14% | 866.09 | -593.63 |

## 3. Proposed redesigns
- **deep_reclaim**: Only take large-session sweeps that reclaim deeply back inside the Asian range, close near the opposite end of the rejection bar, and use a wider stop with a 3R target to cut size-driven friction.
- **fast_rejection**: Trade only the sharpest wick-led rejections during the most liquid hours, require a meaningful body in the reclaim direction, and exit quickly to avoid paying costs on weaker follow-through.
- **one_side_confirmation**: Restrict the setup to the historically stronger direction only after confirming which side of the Asian range produces better gross edge, reducing frequency and avoiding symmetrical low-quality trades.

## 4. Implemented bounded test results
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
| redesign_deep_reclaim | 2 | 371.04 | 220.94 | 1.69 | 639.13 | 150.10 |
| redesign_fast_rejection | 8 | 900.94 | 789.53 | 12.11 | 568.66 | 111.41 |
