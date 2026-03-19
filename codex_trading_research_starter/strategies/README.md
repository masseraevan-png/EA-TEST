# Example strategies

This folder documents the two sample phase-1 strategy families wired into the Python pipeline.

## 1. Session breakout
- Hypothesis: breaks of a recent session range can continue during liquid London/New York hours.
- Entry: next-bar-open after the close breaks above or below the rolling high/low plus an ATR buffer.
- Exit: ATR stop, ATR target, or timeout in bars.
- Main parameters: range lookback, breakout ATR buffer, stop ATR, target ATR, timeout, direction.

## 2. Mean reversion after expansion
- Hypothesis: unusually large bars can mean-revert during liquid intraday sessions.
- Entry: next-bar-open after a bar range exceeds ATR multiple and closes strongly in one direction.
- Exit: ATR stop, ATR target, or timeout in bars.
- Main parameters: expansion multiple, stop ATR, target ATR, timeout, direction.


## 3. Liquidity sweep failed break
- Hypothesis: stop-runs beyond the Asian session high/low that quickly reclaim the range can reverse toward internal liquidity.
- Entry: next-bar-open after a London/New York bar sweeps the Asian extreme, rejects it, and closes back inside the range.
- Exit: ATR stop, ATR target, or timeout in bars.
- Main parameters: minimum sweep size, re-entry depth into range, wick fraction, stop ATR, target ATR, timeout.

## 4. Opening drive pullback continuation
- Hypothesis: a real session opening drive that breaks the Asian range and then pulls back shallowly can continue with better edge than indiscriminate breakout chasing.
- Entry: next-bar-open after an ATR-sized impulse break plus one-bar shallow pullback that still holds the broken level.
- Exit: ATR stop, ATR target, or timeout in bars.
- Main parameters: impulse body ATR threshold, break buffer ATR, max pullback fraction, stop ATR, target ATR, timeout.
