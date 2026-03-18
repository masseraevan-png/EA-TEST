# Strategies Folder

This folder is for strategy definitions used by the Python research pipeline.

## Principle

Each strategy should represent **one clear hypothesis**.

Avoid:
- giant all-in-one strategy files,
- mixing unrelated ideas in one module,
- hidden discretionary logic,
- and overly adaptive rules that are hard to explain.

## Recommended structure per strategy

A strategy module should ideally define:
- strategy name
- family
- plain-English description
- parameters and defaults
- signal generation logic
- exit logic
- risk model assumptions, if strategy-specific
- optional metadata such as preferred symbols or sessions

## Keep it simple

For phase 1:
- prefer fewer parameters,
- prefer direct price/session/volatility logic,
- avoid indicator soup,
- and make sure the strategy could be explained in a few sentences.

## Typical examples for this repo

- session breakout
- mean reversion after expansion
- pullback continuation
- volatility compression / expansion
- time-of-day effects

If a strategy cannot be explained clearly, it probably should not be here.
