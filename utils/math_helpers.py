import numpy as np
import pandas as pd
from typing import Tuple, Optional


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def compute_stop_loss(entry: float, atr: float, multiplier: float = 1.5, direction: str = "long") -> float:
    if direction == "long":
        return round(entry - atr * multiplier, 8)
    return round(entry + atr * multiplier, 8)


def compute_targets(entry: float, stop_loss: float, rr1: float = 2.0, rr2: float = 3.5) -> Tuple[float, float]:
    risk = abs(entry - stop_loss)
    t1 = round(entry + risk * rr1, 8)
    t2 = round(entry + risk * rr2, 8)
    return t1, t2


def compute_rr_ratio(entry: float, stop_loss: float, target: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)


def compute_profit_pct(entry: float, current: float, direction: str = "long") -> float:
    if entry == 0:
        return 0.0
    if direction == "long":
        return round((current - entry) / entry * 100, 2)
    return round((entry - current) / entry * 100, 2)


def compute_max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return round(drawdown.min() * 100, 2)


def compute_profit_factor(profits: list, losses: list) -> float:
    gross_profit = sum(p for p in profits if p > 0)
    gross_loss = abs(sum(l for l in losses if l < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 2)


def find_support_resistance(ohlcv: pd.DataFrame, window: int = 10) -> Tuple[list, list]:
    highs = ohlcv['high']
    lows = ohlcv['low']

    resistance_levels = []
    support_levels = []

    for i in range(window, len(ohlcv) - window):
        if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
            resistance_levels.append(highs.iloc[i])
        if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
            support_levels.append(lows.iloc[i])

    return sorted(set(support_levels)), sorted(set(resistance_levels))


def nearest_resistance(price: float, resistance_levels: list) -> Optional[float]:
    above = [r for r in resistance_levels if r > price * 1.005]
    return min(above) if above else None


def nearest_support(price: float, support_levels: list) -> Optional[float]:
    below = [s for s in support_levels if s < price * 0.995]
    return max(below) if below else None


def estimate_trade_duration(entry: float, target: float, atr_per_hour: float) -> int:
    """Estimate hours to reach target based on ATR velocity."""
    distance = abs(target - entry)
    if atr_per_hour <= 0:
        return 48
    hours = distance / atr_per_hour
    return max(4, min(int(hours), 96))
