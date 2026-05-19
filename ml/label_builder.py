import numpy as np
import pandas as pd
from typing import Optional

from config import LABEL_TARGET_PCT, LABEL_SL_PCT, LABEL_WINDOW_1H


def build_swing_label(
    ohlcv_df: pd.DataFrame,
    idx: int,
    target_pct: float = LABEL_TARGET_PCT,
    sl_pct: float = LABEL_SL_PCT,
    window: int = LABEL_WINDOW_1H,
) -> int:
    """
    Returns 1 if price hits target before stop loss within `window` candles.
    Returns 0 if stop hit first, or window expires without hitting target.
    """
    if idx + 1 >= len(ohlcv_df):
        return 0

    entry = float(ohlcv_df["close"].iloc[idx])
    target = entry * (1 + target_pct)
    stop = entry * (1 - sl_pct)

    future = ohlcv_df.iloc[idx + 1 : idx + window + 1]

    for _, row in future.iterrows():
        if float(row["low"]) <= stop:
            return 0
        if float(row["high"]) >= target:
            return 1

    return 0


def build_labels_for_df(
    ohlcv_df: pd.DataFrame,
    target_pct: float = LABEL_TARGET_PCT,
    sl_pct: float = LABEL_SL_PCT,
    window: int = LABEL_WINDOW_1H,
) -> pd.Series:
    """Build label series for entire DataFrame (excludes last `window` rows)."""
    n = len(ohlcv_df)
    labels = []
    valid_indices = []

    for i in range(n - window):
        label = build_swing_label(ohlcv_df, i, target_pct, sl_pct, window)
        labels.append(label)
        valid_indices.append(ohlcv_df.index[i])

    return pd.Series(labels, index=valid_indices, name="label")


def build_regime_label(ohlcv_df: pd.DataFrame, idx: int, lookback: int = 20) -> int:
    """
    Classify market regime at a given index.
    0=bear, 1=sideways, 2=bull, 3=dangerous
    """
    if idx < lookback:
        return 1

    window_df = ohlcv_df.iloc[idx - lookback : idx]
    close = window_df["close"]
    volume = window_df["volume"]

    price_change = (close.iloc[-1] - close.iloc[0]) / (close.iloc[0] + 1e-10)
    volatility = close.pct_change().std()

    if volatility > 0.05:
        return 3  # dangerous
    elif price_change > 0.05:
        return 2  # bull
    elif price_change < -0.05:
        return 0  # bear
    else:
        return 1  # sideways
