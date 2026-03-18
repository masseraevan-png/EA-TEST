# Research Rules

These rules are mandatory.

They exist to stop the research process from turning into automated curve-fitting.
Codex must follow them when generating, coding, testing, ranking, and reporting strategies.

---

## 1) Mission

The objective is **not** to produce the prettiest backtest.

The objective is to find **simple, robust, out-of-sample survivors** that may deserve later MT5 implementation and further validation.

Codex must optimize for:
- robustness,
- simplicity,
- repeatability,
- realistic execution assumptions,
- and honest reporting.

Codex must **not** optimize for:
- maximum in-sample return,
- the highest Sharpe on one lucky period,
- one-symbol dominance,
- fragile parameter peaks,
- or cosmetic equity curves.

---

## 2) Phase 1 scope

This repo is for **phase 1 research**, not for final live deployment.

Phase 1 focus:
- intraday strategies,
- FX majors, gold, and major indices,
- simple interpretable logic,
- bar-based backtesting,
- conservative transaction-cost assumptions,
- and systematic robustness filtering.

Phase 1 does **not** allow:
- black-box ML models,
- martingale,
- grid systems,
- averaging down,
- unlimited hold times,
- hidden discretionary overrides,
- or strategy logic that cannot be explained clearly.

---

## 3) Strategy design rules

Prefer:
- one clear idea per strategy,
- few parameters,
- simple entry and exit logic,
- logic tied to plausible market behavior,
- clean risk management,
- and modest feature count.

Examples of acceptable phase 1 strategy families:
- session breakout,
- intraday mean reversion after expansion,
- trend continuation after pullback,
- volatility compression / expansion,
- time-of-day effects,
- simple ATR-based risk frameworks.

Avoid:
- rule soup,
- too many stacked filters,
- overly adaptive logic,
- indicator stacking with no clean hypothesis,
- complex decision trees made only to improve historical fit,
- and “because the backtest improved” as a research reason.

If the strategy intuition cannot be stated clearly in a few sentences, it is too messy.

---

## 4) Execution realism rules

All research must include realistic execution assumptions.

Required costs:
- spread,
- slippage,
- commission when applicable,
- and any symbol-specific cost differences from the config.

Required behavior:
- use the configured conservative assumptions,
- do not default to zero-cost tests,
- do not present optimistic best-case fills as the main result,
- do not hide cost sensitivity.

The current cost assumptions are intentionally **slightly pessimistic**, not flattering.
That is deliberate.

If a strategy only works with idealized fills, it is invalid.

---

## 5) Data split discipline

Codex must preserve the research split structure:
- train,
- validation,
- test,
- final holdout.

Rules:
- use train for idea formation and broad fitting,
- use validation for parameter selection,
- use test for first true unseen evaluation,
- use holdout only as the final check.

Strict prohibitions:
- do **not** optimize on holdout,
- do **not** choose parameters using holdout,
- do **not** repeatedly peek at holdout after each change,
- do **not** silently redefine splits after poor results.

If holdout is repeatedly used as a playground, the result is contaminated.

---

## 6) No hidden multiple-testing abuse

Codex must behave as if every new strategy variant is another hypothesis test.

That means:
- log every experiment,
- keep failed runs visible,
- do not only save winners,
- do not quietly mutate rules until something works,
- do not present the final survivor as if it was the first attempt.

Failures are information.
Discarded attempts still matter because they affect how believable the final result is.

---

## 7) Minimum evidence rules

Codex must reject low-evidence strategies early.

Guidelines:
- too few trades means weak evidence,
- too little out-of-sample data means weak evidence,
- one good year is weak evidence,
- one good symbol is weak evidence,
- one good parameter set is weak evidence.

Codex must not defend weak samples with optimistic language.

---

## 8) Parameter stability rules

Parameter robustness is mandatory.

Rules:
- test neighborhoods around candidate parameters,
- check whether nearby values remain acceptable,
- prefer plateaus,
- reject isolated spikes,
- and report parameter sensitivity explicitly.

If a strategy only works at one very specific setting and collapses around it, it is almost certainly not robust.

Codex must prefer the **simpler, more stable** parameter set over the numerically best-looking one.

---

## 9) Walk-forward rules

Walk-forward is mandatory for serious candidates.

Rules:
- use multiple rolling windows,
- separate optimization from evaluation in each window,
- report window-by-window outcomes,
- and do not rely on one lucky split.

Codex must not summarize a mixed walk-forward result as strong just because the aggregate number looks decent.

Window dispersion matters.
Consistency matters.

---

## 10) Stress-testing rules

Every serious candidate must be stress-tested.

At minimum, stress testing should include:
- higher trading costs,
- execution perturbations,
- trade-order reshuffling / Monte Carlo where applicable,
- and segmentation by time and symbol.

When possible, also include:
- worse slippage assumptions,
- worse spread assumptions,
- delayed entry or exit variants,
- and subperiod checks.

Codex must report whether the strategy:
- survives,
- weakens but remains acceptable,
- or collapses.

Do not hide fragility behind an average metric.

---

## 11) Cross-symbol and time-distribution rules

Codex must check whether the result is distributed honestly.

Required checks:
- by symbol,
- by year,
- by month,
- and by train / validation / test / holdout split.

Reject or downgrade strategies that depend mainly on:
- one symbol,
- one short period,
- one unusual market regime,
- or one burst of performance that dominates the whole sample.

A strategy with concentrated results is much weaker than it first appears.

---

## 12) Risk management rules

All strategies must use explicit and finite risk controls.

Required:
- clear stop logic,
- clear exit logic,
- position sizing assumptions that are transparent,
- no hidden averaging down,
- no unbounded loss logic.

Phase 1 prohibits:
- martingale,
- grid rescue logic,
- indefinite holding to avoid realizing losses,
- and position sizing that only looks good because risk expands after losses.

If the strategy has no clean loss containment, reject it.

---

## 13) Reporting rules

Every report must separate results clearly.

Required sections:
- hypothesis and intuition,
- exact rules,
- parameter set tested,
- in-sample results,
- validation results,
- test results,
- holdout results,
- walk-forward summary,
- stress-test summary,
- parameter sensitivity summary,
- by-symbol results,
- by-year results,
- monthly returns,
- trade counts,
- drawdown metrics,
- and final classification.

Codex must not blur in-sample and out-of-sample results together.
That is one of the easiest ways to mislead.

---

## 14) Language discipline

Codex must use honest language.

Allowed framing:
- passed current filters,
- survived current tests,
- deserves further validation,
- candidate for MT5 porting,
- promising but still uncertain.

Forbidden framing:
- proven profitable,
- guaranteed edge,
- validated for live trading,
- safe to scale,
- robust beyond doubt,
- or any wording that pretends uncertainty is gone.

Research outputs are evidence, not proof.

---

## 15) Porting rule

Do **not** port strategies to `mql5_port/` unless they already qualify as **Survivor candidate** under `ACCEPTANCE_CRITERIA.md`.

Do not port:
- rejected strategies,
- borderline strategies that still need major validation,
- cost-fragile strategies,
- holdout-contaminated strategies,
- or strategies with unstable parameters.

Porting weak research into an EA only wastes time faster.

---

## 16) Tiebreak rule

If multiple strategies are similar, prefer the one with:
- fewer rules,
- fewer parameters,
- cleaner economic or behavioral intuition,
- more even performance distribution,
- easier MT5 implementation,
- and lower apparent overfitting risk.

When two candidates are close, the simpler one is usually the more honest one.

---

## 17) Final principle

The AI is not here to manufacture confidence.
It is here to **do research work honestly**.

The correct outcome of many experiments is:
- rejection,
- uncertainty,
- or “needs more validation.”

That is not failure.
That is research discipline.
