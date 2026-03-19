from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    total_return: float
    annualized_return: float
    max_drawdown: float
    return_to_max_drawdown: float
    profit_factor: float
    expectancy_per_trade: float
    expectancy_r: float
    win_rate: float
    average_win: float
    average_loss: float
    total_trades: int
    consecutive_losses_max: int
    oos_trades: int = 0
    risk_of_ruin_proxy: float = 0.0


def max_consecutive_losses(pnl: pd.Series) -> int:
    streak = max_streak = 0
    for value in pnl:
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def compute_metrics(trades: pd.DataFrame, equity_curve: pd.DataFrame) -> PerformanceMetrics:
    pnl = trades["pnl"] if not trades.empty else pd.Series(dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    expectancy = float(pnl.mean()) if not pnl.empty else 0.0
    expectancy_r = float(trades["r_multiple"].mean()) if not trades.empty else 0.0
    win_rate = float((pnl > 0).mean()) if not pnl.empty else 0.0
    average_win = float(wins.mean()) if not wins.empty else 0.0
    average_loss = float(losses.mean()) if not losses.empty else 0.0
    total_return = float(pnl.sum())
    max_dd = float(equity_curve["drawdown"].max()) if not equity_curve.empty else 0.0
    return_to_dd = total_return / max_dd if max_dd > 0 else total_return

    if equity_curve.empty:
        annualized = 0.0
    else:
        span_days = max((equity_curve["timestamp"].max() - equity_curve["timestamp"].min()).days, 1)
        annualized = total_return / span_days * 365.0

    ruin_proxy = 1.0 / (1.0 + math.exp(4 * expectancy_r)) if trades.shape[0] else 1.0

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized,
        max_drawdown=max_dd,
        return_to_max_drawdown=return_to_dd,
        profit_factor=float(profit_factor),
        expectancy_per_trade=expectancy,
        expectancy_r=expectancy_r,
        win_rate=win_rate,
        average_win=average_win,
        average_loss=average_loss,
        total_trades=int(trades.shape[0]),
        consecutive_losses_max=max_consecutive_losses(pnl),
        risk_of_ruin_proxy=ruin_proxy,
    )


def monthly_returns(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["month", "return"])
    frame = trades.copy()
    frame["month"] = frame["exit_time"].dt.to_period("M").astype(str)
    return frame.groupby("month", as_index=False)["pnl"].sum().rename(columns={"pnl": "return"})


def by_year(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["year", "return", "profit_factor", "trades"])
    frame = trades.copy()
    frame["year"] = frame["exit_time"].dt.year
    rows = []
    for year, chunk in frame.groupby("year"):
        wins = chunk.loc[chunk["pnl"] > 0, "pnl"].sum()
        losses = abs(chunk.loc[chunk["pnl"] < 0, "pnl"].sum())
        pf = float(wins / losses) if losses else float("inf") if wins > 0 else 0.0
        rows.append({"year": int(year), "return": float(chunk["pnl"].sum()), "profit_factor": pf, "trades": int(len(chunk))})
    return pd.DataFrame(rows)
