# Trading Research Starter Repo

This repo is a **research factory**, not a “find me a perfect strategy” folder.

The goal is to help Codex or any coding agent:
- generate hypotheses,
- code them,
- backtest them,
- stress-test them,
- log every experiment,
- and only keep robust survivors.

## Core principle

**Do not optimize for the prettiest backtest. Optimize for robustness.**

That means:
- strict data splits,
- realistic transaction costs,
- walk-forward validation,
- parameter stability checks,
- Monte Carlo stress,
- and a final untouched holdout.

## Intended use case

This repo is tailored for:
- **intraday** strategy research,
- later **MT5 / MQL5 EA** porting,
- instruments such as **EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100, and US30**,
- simple **price-action / session / volatility** logic first,
- and **conservative** execution assumptions.

It is **not** intended to be:
- a black-box alpha miner,
- an excuse to over-optimize historical data,
- or a replacement for human research judgment.

## Suggested workflow with Codex

1. Open this repo in Codex.
2. Start with `prompts/01_build_pipeline.md`.
3. Let Codex build the Python research harness inside this repo.
4. Use `prompts/02_generate_hypotheses.md` to create candidate ideas.
5. Use `prompts/03_test_candidates.md` to test and rank them.
6. Port only **Survivor candidate** strategies into `mql5_port/`.

## Non-negotiables

Read these before running anything:
- `RESEARCH_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- `configs/base_config.yaml`

## Folder overview

- `configs/` → base settings and assumptions
- `data/` → local market data or pointers to data source
- `prompts/` → ready-to-use Codex prompts
- `reports/` → generated research reports and templates
- `scripts/` → runners and orchestration scripts
- `src/` → Python research framework
- `strategies/` → strategy definitions or wrappers
- `stress_tests/` → robustness/stress-test logic
- `backtests/` → backtest outputs or cached results
- `exports/` → CSV / JSON / summary exports
- `mql5_port/` → final MT5 porting area for survivors

## Operational notes

### 1) Python first, MQL5 later
The clean workflow is:
- research in Python,
- shortlist only robust survivors,
- port survivors to MQL5 afterwards.

Do **not** make MQL5 the primary idea-mining environment.

### 2) Conservative assumptions on purpose
The base config is intentionally a bit harsh on spreads/slippage.
That is deliberate.

A strategy that only survives under best-case execution assumptions is not robust enough.

Also: if a symbol in the active research universe is missing an explicit cost entry, the framework should error out rather than quietly falling back to a fake default.

### 3) Keep the holdout clean
The holdout period is not another optimization playground.
If you keep peeking until it looks good, you are contaminating it.

### 4) Keep experiment history
Do not delete failed experiments from the log just because they are ugly.
Failed research attempts still matter.

## First task to give Codex

Copy-paste `prompts/01_build_pipeline.md` into Codex and let it scaffold the actual engine.

## After Codex builds the engine

Your next sequence should usually be:
1. refine config assumptions if needed,
2. generate hypotheses,
3. code only the best few,
4. test them under the strict rules,
5. keep only real survivors,
6. then port to MQL5.

## Important reminder

If a strategy only looks good because of:
- one asset,
- one short period,
- one fragile parameter set,
- or unrealistically low execution costs,

then it is not a survivor.
