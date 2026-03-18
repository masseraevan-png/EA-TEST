Implement and test the selected candidate strategies using this repository.

Mandatory references before coding or reporting:
- `README.md`
- `RESEARCH_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- `configs/base_config.yaml`

Required workflow:
1. implement the selected candidate strategies
2. run in-sample backtests
3. run validation tests
4. run test-period out-of-sample checks
5. run final holdout checks without using holdout for parameter selection
6. run walk-forward testing
7. run parameter sensitivity / neighborhood checks
8. run Monte Carlo / trade-order stress tests
9. run higher-cost stress tests
10. update the experiment log
11. generate one markdown report per strategy
12. generate a comparison summary across all tested strategies

Output required:
- one markdown report per strategy in `reports/generated/`
- one comparison table in `exports/`
- one updated `EXPERIMENT_LOG.csv`
- one shortlist of final labels using only:
  - Rejected
  - Needs more validation
  - Survivor candidate

Reporting requirements:
- keep train / validation / test / holdout clearly separated
- show by-symbol results
- show by-year results
- show combined out-of-sample metrics
- show monthly return output
- show trade counts
- show explicit holdout sanity-check output
- show drawdown metrics
- show cost-stress results
- show walk-forward summary
- show parameter sensitivity summary
- show a short honest explanation of why the final label was assigned

Important rules:
- do not blur in-sample and out-of-sample together
- do not optimize on the holdout
- do not hide failed runs
- do not use optimistic execution language
- if the strategy is borderline, label it `Needs more validation`, not `Survivor candidate`

A strategy survives only if it genuinely satisfies the thresholds and logic in `ACCEPTANCE_CRITERIA.md`.
