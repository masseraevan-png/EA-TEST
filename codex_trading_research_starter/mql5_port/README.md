# MQL5 Port Area

Only move a strategy here **after** it survives the Python research process and is labeled **Survivor candidate**.

## Why this folder exists

Python is the research environment.
MQL5 is the execution-porting environment.

This folder exists to translate already-surviving ideas into MT5/EA form, not to discover ideas from scratch.

## Porting checklist

Before porting, confirm all of the following:
- the strategy is labeled **Survivor candidate**
- the hypothesis and rules are written clearly
- the final parameter set is documented
- the cost assumptions are documented
- the report includes walk-forward and stress-test results
- the strategy is not dependent on one fragile parameter spike
- the holdout was not abused

## Recommended process

1. Port the clean final rules from the survivor report.
2. Match cost assumptions as closely as possible.
3. Match bar timing and signal timing carefully.
4. Validate logic against the Python research version.
5. Run MT5 backtests with realistic settings.
6. Then run demo / pilot validation.
7. Only after that, consider any real-money use.

## Important warning

Do **not** change the logic silently during the MQL5 port and still pretend it is the same strategy.
If you materially change:
- entry logic,
- exit logic,
- stop/target logic,
- session rules,
- sizing logic,
- or execution assumptions,

then it is effectively a new variant and should be documented as such.

## Suggested contents per survivor

For each survivor, try to keep:
- the final research report
- a short one-page porting spec
- the final chosen parameters
- an MQL5 implementation file
- MT5 validation notes
- differences versus Python implementation, if any

Do not use this folder as the primary idea-mining environment.
