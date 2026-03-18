# Strategy Report — {{strategy_name}}

## 1. Research summary
- Final label:
- Strategy family:
- Primary symbol(s):
- Primary timeframe(s):
- Report date:
- Research version / commit:
- Short verdict:

## 2. Hypothesis
- Plain-English intuition:
- Why this idea could plausibly exist:
- Main assumptions behind the logic:

## 3. Exact rules
### Entry logic
- Long entry:
- Short entry:

### Exit logic
- Stop-loss:
- Take-profit:
- Time-based exit:
- Session close handling:
- Re-entry rules:

### Position sizing / risk assumptions
- Sizing mode:
- Risk per trade:
- Max concurrent positions:

## 4. Parameters tested
| Parameter | Description | Range tested | Chosen value |
|---|---|---:|---:|
|  |  |  |  |

## 5. Data and split integrity
- Train period:
- Validation period:
- Test period:
- Holdout period:
- Holdout kept untouched during selection?:
- Symbols used:
- Timeframe(s) used:
- Data quality notes:

## 6. Cost and execution assumptions
- Cost model:
- Spread assumptions:
- Slippage assumptions:
- Commission assumptions:
- Bar-based fill assumptions:
- Any symbol-specific execution note:

## 7. In-sample result
| Metric | Value |
|---|---:|
| Total return |  |
| Annualized return |  |
| Profit factor |  |
| Max drawdown |  |
| Return / Max DD |  |
| Expectancy / trade |  |
| Expectancy in R |  |
| Win rate |  |
| Average win |  |
| Average loss |  |
| Total trades |  |
| Max consecutive losses |  |

## 8. Validation result
| Metric | Value |
|---|---:|
| Total return |  |
| Profit factor |  |
| Max drawdown |  |
| Return / Max DD |  |
| Expectancy in R |  |
| Trades |  |

## 9. Test result
| Metric | Value |
|---|---:|
| Total return |  |
| Profit factor |  |
| Max drawdown |  |
| Return / Max DD |  |
| Expectancy in R |  |
| Trades |  |

## 10. Combined out-of-sample result
| Metric | Value |
|---|---:|
| Combined OOS return |  |
| Combined OOS profit factor |  |
| Combined OOS max drawdown |  |
| Combined OOS Return / Max DD |  |
| Combined OOS expectancy in R |  |
| Combined OOS trades |  |

## 11. Holdout result
| Metric | Value |
|---|---:|
| Total return |  |
| Profit factor |  |
| Max drawdown |  |
| Return / Max DD |  |
| Expectancy in R |  |
| Trades |  |
| Holdout sanity check |  |

## 12. Walk-forward summary
- Windows tested:
- Windows passed:
- Windows failed:
- Aggregate comment:
- Any obvious instability:

## 13. Stress tests
### Higher-cost stress
- Base:
- Moderate:
- Harsh:
- Comment:

### Execution perturbation
- Delayed entry / worse fills:
- Comment:

### Monte Carlo / trade-order stress
- Method(s):
- Main result:
- Comment:

## 14. Parameter robustness
- Neighborhood tested:
- Neighbor pass ratio:
- Plateau-like or isolated peak?:
- Comment:

## 15. Distribution of results
### By symbol
| Symbol | Return | Profit factor | Trades | Comment |
|---|---:|---:|---:|---|
|  |  |  |  |  |

### By year
| Year | Return | Profit factor | Max DD | Trades |
|---|---:|---:|---:|---:|
|  |  |  |  |  |

### Monthly return notes
- Best month:
- Worst month:
- Any concentration issue:

## 16. Acceptance criteria check
| Criterion | Pass / Fail | Comment |
|---|---|---|
| Min total trades |  |  |
| Min OOS trades |  |  |
| OOS profit factor |  |  |
| OOS expectancy in R |  |  |
| OOS return / max DD |  |  |
| Cost robustness |  |  |
| Parameter stability |  |  |
| Walk-forward consistency |  |  |
| Cross-symbol distribution |  |  |
| Holdout sanity |  |  |
| Simplicity / interpretability |  |  |

## 17. Final verdict
- Final label:
- Why this label was assigned:
- Main weakness:
- Main strength:
- Next action:
  - Reject and archive
  - Keep for more validation
  - Port to MQL5
