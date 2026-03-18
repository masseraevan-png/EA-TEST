# Acceptance Criteria

These criteria define what **passes**, what **fails**, and what only **deserves more validation**.

They are designed for **phase 1** of this repo:
- intraday research,
- simple interpretable logic,
- conservative bar-based execution,
- conservative cost assumptions.

## Core principle

A strategy is **not** accepted because it has a pretty equity curve.

A strategy only survives if it shows:
- acceptable **out-of-sample behavior**,
- acceptable behavior under **higher trading costs**,
- acceptable **parameter stability**,
- acceptable **distribution of results** across time and symbols,
- acceptable **drawdown quality** relative to return,
- and logic that is still simple enough to trust.

---

## Classification labels

Only use these final labels in reports:
- **Rejected**
- **Needs more validation**
- **Survivor candidate**

Never use language such as:
- guaranteed profitable,
- proven edge,
- safe to trade live,
- validated money machine.

---

## Hard rejection rules

A candidate is **Rejected** immediately if **any** of the following is true.

### 1) Trade count is too low
- Total trades < **150**
- Train trades < **60**
- Validation trades < **25**
- Test trades < **25**
- Combined out-of-sample trades < **50**

Reason: low sample size makes almost everything look more reliable than it really is.

### 2) Out-of-sample quality is too weak
- Combined out-of-sample profit factor < **1.10**
- Combined out-of-sample expectancy in R < **0.00**
- Combined out-of-sample result is not positive

Reason: a strategy that only works in-sample is research trash.

### 3) Drawdown quality is too poor
- Return / Max Drawdown < **1.00** on combined out-of-sample

Reason: if return is not at least on the same order as drawdown, the strategy is usually not worth further attention.

### 4) Performance is too concentrated in one symbol
- Fewer than **2 symbols** have positive out-of-sample performance
- More than **65%** of total out-of-sample profit comes from one symbol

Reason: one-symbol dependency is often disguised overfitting or regime luck.

### 5) Performance collapses under cost stress
- Strategy turns unacceptable under **moderate** cost stress
- Strategy becomes clearly negative under realistic spread/slippage increases

Reason: fragile cost sensitivity kills live tradability.

### 6) Parameter surface is too fragile
- Best parameter set is isolated
- Nearby parameter values collapse immediately
- Neighbor pass ratio < **50%** in the defined neighborhood test

Reason: sharp parameter peaks are usually fake edges.

### 7) Walk-forward behavior is too inconsistent
- Fewer than **4** valid walk-forward windows
- Most walk-forward windows fail
- Out-of-sample performance is driven by only one favorable window

Reason: one lucky split is not evidence.

### 8) Holdout was abused or clearly collapses
Reject if any of the following is true:
- holdout was used for parameter selection,
- holdout was repeatedly re-checked during search until it looked acceptable,
- holdout has adequate trade count and shows a clear collapse versus the already-selected strategy.

Practical interpretation of “clear collapse” for phase 1:
- holdout trades >= **20** and holdout result is materially negative,
- or holdout Profit Factor < **0.95**,
- or holdout Return / Max Drawdown < **0.50**.

Reason: the holdout is the final honesty check. If it breaks there, the pipeline has not found a reliable survivor.

### 9) Logic is too complex for the evidence
Reject if the strategy has any of the following in phase 1:
- too many stacked filters,
- too many degrees of freedom,
- opaque ML logic,
- martingale / grid / averaging down,
- no hard stop structure,
- research explanation that cannot be stated clearly in a few sentences.

Reason: if the logic is messy, the backtest usually lies more than it informs.

---

## Survivor candidate rules

A strategy can be labeled **Survivor candidate** only if **all** of the following are true.

### Sample size and coverage
- Total trades >= **150**
- Combined out-of-sample trades >= **50**
- At least **2 symbols** show positive out-of-sample contribution

### Out-of-sample quality
- Combined out-of-sample profit factor >= **1.10**
- Combined out-of-sample expectancy in R > **0.00**
- Combined out-of-sample result > **0**
- Combined out-of-sample Return / Max Drawdown >= **1.00**

### Cost robustness
- Remains acceptable under **moderate** cost stress
- Does not show immediate collapse when spread and slippage are increased within the configured stress ranges

### Stability
- Parameter neighborhood pass ratio >= **50%**
- Walk-forward has at least **4** valid windows
- No obvious dependency on one short period only
- No obvious dependency on one single symbol only

### Holdout sanity
- Holdout must remain untouched during selection
- If holdout contains at least **20** trades, it must not show a clear collapse
- A mild wobble is acceptable; a clear break is not

### Simplicity
- The logic is still interpretable
- The parameter count is modest relative to the strategy family
- The intuition can be written clearly and checked logically

### Reporting completeness
The report must include at minimum:
- in-sample vs validation vs test vs holdout separation,
- by-symbol results,
- by-year results,
- monthly returns,
- drawdown metrics,
- trade count metrics,
- parameter sensitivity output,
- cost stress output,
- walk-forward summary,
- Monte Carlo stress summary.

A strategy that passes the numeric rules but lacks this reporting is **not** a survivor yet.

---

## Needs more validation rules

Use **Needs more validation** when the strategy is not bad enough to reject, but not clean enough to survive.

Typical cases:
- out-of-sample is positive but only slightly above thresholds,
- trade count is acceptable but still a bit thin,
- cost stress hurts more than expected but does not fully kill it,
- parameter surface is decent but not clearly plateau-like,
- one symbol contributes too much, but not enough to trigger hard rejection,
- walk-forward is mixed rather than clearly strong,
- holdout is not disastrous but is weaker than expected.

This label means:
- worth further testing,
- not ready for MT5 porting as a serious candidate,
- not a green light for live use.

---

## Holdout rule

The **holdout period** exists to reduce self-deception.

Rules:
- do **not** optimize on holdout,
- do **not** select parameters using holdout,
- do **not** repeatedly re-run search until holdout looks good.

The holdout is the final check, not another playground.

If a strategy only looks good after repeated holdout peeking, treat it as **Rejected**.

---

## Conservative cost rule

The configured spread and slippage assumptions are intentionally a bit **pessimistic**, not best-case.

That is deliberate.

A strategy that only survives under perfect or near-perfect fills is not robust enough.

So for phase 1:
- prefer slightly harsh assumptions over flattering assumptions,
- prefer survivability over cosmetic backtest quality.

---

## Simplicity tiebreaker

If two strategies are close, prefer the one with:
- fewer rules,
- fewer parameters,
- cleaner market intuition,
- easier MT5 implementation,
- lower risk of hidden overfitting.

The simpler strategy is usually the more honest one.

---

## MT5 porting gate

A strategy should only be sent to the `mql5_port/` stage if it is already labeled **Survivor candidate**.

Do **not** port:
- rejected strategies,
- borderline strategies with unclear robustness,
- strategies that need perfect cost assumptions,
- strategies with isolated parameter peaks.

Porting weak research into an EA only wastes time faster.
