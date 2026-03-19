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
