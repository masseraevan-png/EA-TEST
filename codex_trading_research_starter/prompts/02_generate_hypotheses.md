Generate **20 simple intraday strategy hypotheses** for this repo and rank them before coding anything.

Context:
- Target instruments: EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100, US30
- Target timeframes: mainly M5 and M15
- Goal: find simple, interpretable strategy ideas that can survive robust testing later
- Do not optimize anything yet. This task is only about hypothesis generation and ranking.

Mandatory references before answering:
- `RESEARCH_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- `configs/base_config.yaml`

Rules:
- Keep logic simple and interpretable.
- No machine learning.
- Focus on **one clean idea per strategy**.
- Avoid “rule soup”.
- Prefer ideas that can be ported cleanly to MQL5 later.
- Respect intraday execution realism and the configured sessions/cost assumptions.

Allowed families include:
- session breakout
- mean reversion after expansion
- pullback continuation
- volatility compression / expansion
- time-of-day effects
- simple liquidity sweep / failed-break style logic
- ATR-based risk framing where useful

For each of the 20 hypotheses, provide:
1. strategy name
2. family
3. plain-English intuition
4. best-fit symbols
5. best-fit timeframe(s)
6. exact entry idea
7. exact exit idea
8. stop-loss / target structure
9. main parameters worth testing
10. likely overfitting risks
11. implementation difficulty (Low / Medium / High)
12. porting difficulty to MQL5 (Low / Medium / High)

Then:
- rank all 20 from most plausible to least plausible for this repo
- explain the top 5 briefly
- only recommend **the best 5 for coding first**
- explicitly reject any idea that is too complex, too regime-specific, or too fragile

Important:
Do **not** claim that any hypothesis is profitable.
Treat them as research candidates only.
