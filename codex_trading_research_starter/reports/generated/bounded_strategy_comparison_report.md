# Bounded Strategy Comparison Report

## 1. Scope
- Symbol: EURUSD
- Timeframe: M15
- Run mode: real_research_mode
- Backtest window: 2024-01-01 to 2024-12-31
- Research shape: small bounded parameter subset only; no full pipeline

## 2. Best run per strategy
- mean_reversion_after_expansion: best parameter_index=1, trades=568, return=-42670.03, pf=0.69, max_dd=49448.55, return/max_dd=-0.86, avg_cost=93.06
- session_breakout: best parameter_index=1, trades=1145, return=-78351.26, pf=0.69, max_dd=79569.62, return/max_dd=-0.98, avg_cost=55.92

## 3. All bounded runs
| Strategy | Param idx | Trades | Total return | Profit factor | Max DD | Return / Max DD | Avg explicit cost/trade | Data quality |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| session_breakout | 0 | 1577 | -89985.74 | 0.64 | 91051.17 | -0.99 | 51.30 | warning |
| session_breakout | 1 | 1145 | -78351.26 | 0.69 | 79569.62 | -0.98 | 55.92 | warning |
| mean_reversion_after_expansion | 0 | 1270 | -89037.04 | 0.49 | 90016.45 | -0.99 | 65.30 | warning |
| mean_reversion_after_expansion | 1 | 568 | -42670.03 | 0.69 | 49448.55 | -0.86 | 93.06 | warning |

## 4. Small-subset consistency
- mean_reversion_after_expansion: 2 bounded runs, positive runs=0, pf>1 runs=0
- session_breakout: 2 bounded runs, positive runs=0, pf>1 runs=0

## 5. Intentionally skipped
- Broad parameter sweep
- Neighbor sensitivity grid
- Full walk-forward validation
- Full stress-test matrix
- Full train / validation / holdout research batch
