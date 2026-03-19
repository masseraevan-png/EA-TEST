# Price-Action Family Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Bounded backtest window: 2024-01-01 to 2024-12-31
- Objective: test lower-frequency, more price-action/liquidity-focused alternatives to the prior mean-reversion family.

## 2. Proposed next families
- **liquidity_sweep_failed_break**: Fade London/New York sweeps of the Asian session extreme after a reclaim back inside the range.
- **opening_drive_pullback_continuation**: Trade only strong opening displacement breaks that pull back shallowly and then resume in the impulse direction.
- **compression_breakout_retest**: Wait for a tight intraday coil near session boundary, then trade only breakout-retest continuation rather than first-touch breakout.
- **range_reclaim_after_stop_run**: Trade reclaims of prior day high/low after a stop run fails and price closes back through the breached level.

## 3. Tested implementations
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
| liquidity_sweep_reversal_param_0 | 137 | 57.04 | -55.73 | 0.85 | 15284.51 | 112.77 |
| liquidity_sweep_reversal_param_1 | 74 | 24.20 | -80.75 | 0.79 | 10003.23 | 104.95 |
| opening_drive_pullback_param_0 | 570 | -19.19 | -92.24 | 0.68 | 55510.24 | 73.05 |
| opening_drive_pullback_param_1 | 390 | -51.96 | -122.39 | 0.61 | 49114.92 | 70.42 |
