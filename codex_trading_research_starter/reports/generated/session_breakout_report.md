# Strategy Report — session_breakout

## 1. Research summary
- Final label: Rejected
- Strategy family: session_breakout
- Primary symbol(s): EURUSD
- Primary timeframe(s): M15
- Run mode: demo_mode
- Short verdict: Conservative phase-1 research result only.

## 2. Hypothesis
- Plain-English intuition: A break of the recent session range during London or New York can continue far enough to cover conservative costs.
- Main assumptions behind the logic: Uses the prior lookback window high/low as a breakout trigger, requires the trade to be opened during enabled sessions, and exits using ATR-derived stop, target, or timeout.

## 3. Exact rules
- ATR-based stops and targets with next-bar-open entry under conservative bar-based execution.
- No same-bar entry/exit optimism; stop has priority if stop and target are both touched.
- Sizing model: fixed-fractional equity-aware sizing using `initial_equity_usd`, `risk_per_trade`, stop distance, and symbol lot constraints.

## 4. Parameters tested
- Selected parameters: {'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}

## 5. Data and split integrity
- Train period: 2018-01-01 to 2022-12-31
- Validation period: 2023-01-01 to 2023-12-31
- Test period: 2024-01-01 to 2024-12-31
- Holdout period: 2025-01-01 to 2025-12-31
- Holdout kept untouched during selection?: Yes
- Symbols used: EURUSD
- Data sources:
  - EURUSD: synthetic::EURUSD_M15

## 6. Cost and execution assumptions
- Explicit symbol-specific costs from `configs/base_config.yaml`
- Conservative execution mode with next-bar-open entries and pessimistic tie-breaking.
- Symbol mechanics:
  - EURUSD: asset_class=fx, base=EUR, quote=USD, contract_size=100000.0, min_size=0.01, size_step=0.01, max_size=100.0, price_increment=1e-05, pip_size=0.0001
- Position sizing assumptions:
  - Equity-aware sizing is applied per trade.
  - Risk budget equals `equity_before * risk_per_trade`.
  - Position size is floored to the configured minimum/step and capped by optional max size.

## 7. In-sample result
- Total return: 686224.37
- Profit factor: 12.57
- Max drawdown: 3528.64
- Return / Max DD: 194.47
- Total trades: 1208

## 8. Validation result
- Total return: 90619.83
- Profit factor: 16.96
- Trades: 225

## 9. Test result
- Total return: 110774.49
- Profit factor: 13.96
- Trades: 237

## 10. Combined out-of-sample result
- Combined OOS return: 201394.32
- Combined OOS profit factor: 15.16
- Combined OOS max drawdown: 3742.70
- Combined OOS Return / Max DD: 53.81
- Combined OOS expectancy in R: 0.6031
- Combined OOS trades: 462

## 11. Holdout result
- Total return: 98972.52
- Profit factor: 11.49
- Return / Max DD: 52.11
- Trades: 246

## 12. Walk-forward summary
- Total windows: 17
- Passed windows: 17
- Average walk-forward test return: 40022.29
- Average walk-forward test profit factor: 15.89
- Best window return: 47043.03
- Worst window return: 32601.59
- Test return dispersion (std): 3553.68
- Test PF dispersion (std): 10.02
- train=2018-01-01→2019-12-31, validation=2020-01-01→2020-06-30, test=2020-07-01→2020-12-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.72, validation_pf=9.06, test_pf=20.02, passed=True
- train=2018-04-01→2020-03-31, validation=2020-04-01→2020-09-30, test=2020-10-01→2021-03-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.35, validation_pf=13.31, test_pf=15.11, passed=True
- train=2018-07-01→2020-06-30, validation=2020-07-01→2020-12-31, test=2021-01-01→2021-06-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=10.18, validation_pf=20.02, test_pf=9.63, passed=True
- train=2018-10-01→2020-09-30, validation=2020-10-01→2021-03-31, test=2021-04-01→2021-09-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.89, validation_pf=15.11, test_pf=9.99, passed=True
- train=2019-01-01→2020-12-31, validation=2021-01-01→2021-06-30, test=2021-07-01→2021-12-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=12.36, validation_pf=9.63, test_pf=5.48, passed=True
- train=2019-04-01→2021-03-31, validation=2021-04-01→2021-09-30, test=2021-10-01→2022-03-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=14.39, validation_pf=9.99, test_pf=5.44, passed=True
- train=2019-07-01→2021-06-30, validation=2021-07-01→2021-12-31, test=2022-01-01→2022-06-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=14.41, validation_pf=5.48, test_pf=8.18, passed=True
- train=2019-10-01→2021-09-30, validation=2021-10-01→2022-03-31, test=2022-04-01→2022-09-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=15.06, validation_pf=5.44, test_pf=8.00, passed=True
- train=2020-01-01→2021-12-31, validation=2022-01-01→2022-06-30, test=2022-07-01→2022-12-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=12.39, validation_pf=8.18, test_pf=10.70, passed=True
- train=2020-04-01→2022-03-31, validation=2022-04-01→2022-09-30, test=2022-10-01→2023-03-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.43, validation_pf=8.00, test_pf=15.96, passed=True
- train=2020-07-01→2022-06-30, validation=2022-07-01→2022-12-31, test=2023-01-01→2023-06-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.36, validation_pf=10.70, test_pf=12.35, passed=True
- train=2020-10-01→2022-09-30, validation=2022-10-01→2023-03-31, test=2023-04-01→2023-09-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=10.02, validation_pf=15.96, test_pf=12.34, passed=True
- train=2021-01-01→2022-12-31, validation=2023-01-01→2023-06-30, test=2023-07-01→2023-12-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=9.92, validation_pf=12.35, test_pf=23.33, passed=True
- train=2021-04-01→2023-03-31, validation=2023-04-01→2023-09-30, test=2023-10-01→2024-03-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=10.50, validation_pf=12.34, test_pf=39.22, passed=True
- train=2021-07-01→2023-06-30, validation=2023-07-01→2023-12-31, test=2024-01-01→2024-06-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=10.22, validation_pf=23.33, test_pf=33.37, passed=True
- train=2021-10-01→2023-09-30, validation=2023-10-01→2024-03-31, test=2024-04-01→2024-09-30, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=11.09, validation_pf=39.22, test_pf=32.26, passed=True
- train=2022-01-01→2023-12-31, validation=2024-01-01→2024-06-30, test=2024-07-01→2024-12-31, params={'range_lookback': 18, 'breakout_buffer_atr': 0.2, 'stop_atr': 1.2, 'target_atr': 2.0, 'timeout_bars': 18, 'direction': 'both'}, train_pf=13.88, validation_pf=33.37, test_pf=8.84, passed=True

## 13. Stress tests
- Stress pass rate: 1.00
- Average stressed return: 163527.36
- Worst stressed return: 23514.10
- Worst stressed profit factor: 2.02
- Moderate scenario remained acceptable?: True
- Parameter neighbor pass ratio: 1.00
- Monte Carlo median return: 201394.32
- Monte Carlo 1st percentile return: 182461.69
- Monte Carlo 5th percentile return: 190207.12
- Monte Carlo 95th percentile return: 213045.59
### Stress scenario matrix
| Scenario | Return | Profit factor | Return / Max DD | Trades | Pass |
|---|---:|---:|---:|---:|---|
| base | 257338.19 | 18.37 | 68.76 | 472 | True |
| moderate_cost | 220377.47 | 15.39 | 56.61 | 472 | True |
| higher_cost | 93485.43 | 6.21 | 21.28 | 472 | True |
| spread_shock | 156033.57 | 10.58 | 37.66 | 472 | True |
| slippage_shock | 207573.20 | 14.39 | 52.65 | 472 | True |
| commission_shock | 168812.80 | 11.50 | 41.25 | 472 | True |
| delayed_entry | 207685.26 | 10.57 | 53.35 | 472 | True |
| skip_5pct | 220377.47 | 15.39 | 56.61 | 472 | True |
| skip_10pct | 80076.11 | 6.32 | 18.65 | 423 | True |
| harsh_execution | 23514.10 | 2.02 | 6.95 | 423 | True |


## 14. Distribution of results
### By symbol
| Symbol | Return | Profit factor | Trades | Comment |
|---|---:|---:|---:|---|
| EURUSD | 201394.32 | 15.16 | 462 | Positive |

### By year
| Year | Return | Profit factor | Max DD | Trades |
|---|---:|---:|---:|---:|
| 2023 | 90619.83 | 16.96 | n/a | 225 |
| 2024 | 110774.49 | 13.96 | n/a | 237 |

## 15. Acceptance criteria check
| Criterion | Pass / Fail | Comment |
|---|---|---|
| Min total trades | Pass | Observed 1670 |
| Min OOS trades | Pass | Observed 462 |
| OOS profit factor | Pass | Observed 15.16 |
| OOS expectancy in R | Pass | Observed 0.603 |
| OOS return / max DD | Pass | Observed 53.81 |
| Cross-symbol distribution | Fail | Positive symbols 1, max share 1.00 |
| Cost robustness | Pass | pass_rate=1.00, avg_return=163527.36, worst_return=23514.10, worst_pf=2.02 |
| Parameter stability | Pass | Observed 1.00 |
| Walk-forward consistency | Pass | Windows=17, passes=17, pass_ratio=1.00, avg_pf=15.89 |
| Holdout sanity | Pass | Trades=246, PF=11.49, Return/DD=52.11 |
| Simplicity / interpretability | Pass | Phase 1 strategies remain simple and explainable |

## 16. Final verdict
- Final label: Rejected
- Notes: The framework remains conservative and does not claim the strategy is proven.
