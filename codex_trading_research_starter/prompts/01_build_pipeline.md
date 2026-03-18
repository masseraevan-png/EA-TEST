Build a systematic strategy research pipeline inside this repository for my real workflow.

Context about the target use case:
- I mainly research intraday strategies that may later be ported to MT5 / MQL5 EAs.
- Primary markets: EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100, and US30.
- Preferred style: simple, interpretable, price-action / session / volatility logic.
- Typical ideas include session filters, breakouts, mean reversion after expansion, continuation after pullback, liquidity sweep / imbalance-style concepts, ATR-based stops, and time-of-day behavior.
- Avoid black-box ML for phase 1. No deep learning, no opaque models, no indicator soup.
- The purpose of this pipeline is to find robust survivor candidates that can later be ported to MQL5, not to optimize the prettiest backtest.

First, read and follow these files before coding:
- `README.md`
- `RESEARCH_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- `configs/base_config.yaml`

Main objective:
Create a modular Python research harness that can generate, test, and compare simple intraday strategy candidates under strict anti-overfitting rules.

Core design requirements:
1. Use Python for research and backtesting.
2. Make the framework modular and easy to extend.
3. Keep implementation readable and practical rather than over-engineered.
4. Build the framework so that later I can port only survivor candidates into `mql5_port/`.
5. Prefer bar-based research with conservative assumptions. Do not pretend bar data gives tick-perfect execution.

The framework must include:
1. strategy definitions / interfaces
2. data loading layer
3. backtest runner
4. walk-forward runner
5. stress-test runner
6. parameter sweep / sensitivity analysis module
7. report generator
8. experiment log updater
9. comparison table exporter for multiple strategies

Research constraints:
- Keep a final untouched holdout set.
- Separate train, validation, test, and holdout periods clearly.
- Do not optimize on the final holdout.
- Include realistic spread, slippage, and commission assumptions.
- Fail loudly if a tested symbol is missing an explicit symbol-specific cost entry. Do not silently rely on default cost placeholders for active universe symbols.
- Costs must respect the explicit units in `configs/base_config.yaml`:
  - FX spreads/slippage in pips,
  - XAUUSD in USD move,
  - NAS100 and US30 in index points.
- Include session/time-of-day constraints where relevant.
- Reject low-trade-count strategies.
- Reject fragile parameter spikes.
- Reject strategies whose edge disappears with moderate cost increases.
- Reports must clearly separate in-sample, validation, out-of-sample, walk-forward, and stress-test results.

Style-specific constraints:
- Start with simple intraday strategy families only.
- Strategy logic should be interpretable in plain English.
- No more than a small number of key parameters per strategy.
- Avoid overuse of indicators. Favor direct price / range / session / volatility logic.
- Allow ATR-based stop-loss / take-profit logic as a first-class option.
- Support long-only, short-only, and both-direction testing where relevant.
- Support multiple instruments from the target universe.
- Make it easy to test by timeframe, session, and symbol.

Execution realism requirements:
- Backtests must model costs explicitly.
- Add a conservative execution mode for bar-based fills.
- Clearly document fill assumptions.
- Include cost-stress scenarios.
- Include simple Monte Carlo trade-order reshuffling.
- Include parameter-neighborhood stability checks.

Performance outputs required for each run:
- total return
- CAGR or annualized return where applicable
- max drawdown
- profit factor
- expectancy per trade
- win rate
- average win / average loss
- total trades
- out-of-sample trades
- by-symbol results
- by-year results if enough data exists
- monthly return series export

Additional metrics relevant for my workflow:
- return / max drawdown ratio
- ability to evaluate whether a strategy is compatible with tight drawdown constraints similar to prop-style accounts
- consecutive loss statistics
- simple risk-of-ruin style summary if feasible without overcomplicating the framework

Sample strategy coverage to implement now:
Implement 2 sample strategies only as examples for the framework. Keep them simple.

Suggested examples:
1. Session breakout strategy
2. Mean reversion after expansion strategy

For each sample strategy:
- define the hypothesis in plain English
- define exact entry rules
- define exact exit rules
- define stop/target logic
- expose only the main parameters worth testing

Technical deliverables:
- refine the repo structure if needed, but keep it clean
- create runnable scripts inside `scripts/`
- implement framework code inside `src/research_pipeline/`
- create example strategy modules
- wire reporting to `reports/generated/`
- wire exports to `exports/`
- update `EXPERIMENT_LOG.csv` automatically after each experiment batch
- create a simple example command-line workflow to run one strategy and one batch

Expected scripts:
- `scripts/run_backtests.py`
- `scripts/run_walkforward.py`
- `scripts/run_stress_tests.py`
- create additional helper scripts only if truly useful

Expected code qualities:
- type hints where reasonable
- clear docstrings on core interfaces
- no unnecessary complexity
- fail loudly on bad config
- make assumptions explicit
- do not claim a strategy is profitable or proven; only classify as Rejected / Needs more validation / Survivor candidate

Expected final output from this task:
1. the implemented Python framework
2. 2 example strategies wired into it
3. runnable commands
4. one sample generated report
5. one sample updated experiment log row or batch
6. a short explanation of the architecture and where to add new strategies later

Important behavioral instruction:
If you are uncertain about a design choice, prefer the more conservative and less overfit-prone option.
