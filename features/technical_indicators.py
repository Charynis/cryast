import pandas as pd
import numpy as np
from typing import Optional

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    if HAS_PANDAS_TA:
        return ta.rsi(close, length=period).rename("rsi")
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / (loss + 1e-10)
    return (100 - 100 / (1 + rs)).rename("rsi")


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    if HAS_PANDAS_TA:
        result = ta.macd(close, fast=fast, slow=slow, signal=signal)
        if result is not None:
            result.columns = ["macd", "macd_hist", "macd_signal"]
            return result
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "macd_signal": signal_line, "macd_hist": histogram})


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean().rename(f"ema_{period}")


def compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean().rename(f"sma_{period}")


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    if HAS_PANDAS_TA:
        return ta.atr(high, low, close, length=period).rename("atr")
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean().rename("atr")


def compute_bollinger_bands(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    if HAS_PANDAS_TA:
        result = ta.bbands(close, length=period, std=std)
        if result is not None:
            result.columns = ["bb_lower", "bb_mid", "bb_upper", "bb_bw", "bb_pct"]
            return result
    mid = close.rolling(period).mean()
    std_dev = close.rolling(period).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    bb_bw = (upper - lower) / (mid + 1e-10)
    bb_pct = (close - lower) / (upper - lower + 1e-10)
    return pd.DataFrame({"bb_lower": lower, "bb_mid": mid, "bb_upper": upper, "bb_bw": bb_bw, "bb_pct": bb_pct})


def compute_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    typical_price = (high + low + close) / 3
    cumulative_tpv = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    return (cumulative_tpv / (cumulative_vol + 1e-10)).rename("vwap")


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum().rename("obv")


def compute_stoch_rsi(close: pd.Series, period: int = 14) -> pd.DataFrame:
    if HAS_PANDAS_TA:
        result = ta.stochrsi(close, length=period)
        if result is not None and len(result.columns) >= 2:
            result.columns = ["stoch_k", "stoch_d"] + list(result.columns[2:])
            return result[["stoch_k", "stoch_d"]]
    rsi = compute_rsi(close, period)
    rsi_min = rsi.rolling(period).min()
    rsi_max = rsi.rolling(period).max()
    stoch_k = 100 * (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10)
    stoch_d = stoch_k.rolling(3).mean()
    return pd.DataFrame({"stoch_k": stoch_k, "stoch_d": stoch_d})


def compute_all_indicators(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """Compute all indicators and return a flat feature DataFrame."""
    if len(df) < 30:
        return pd.DataFrame()

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    features = pd.DataFrame(index=df.index)

    rsi = compute_rsi(close)
    features[f"{prefix}rsi"] = rsi
    features[f"{prefix}rsi_oversold"] = (rsi < 30).astype(float)
    features[f"{prefix}rsi_overbought"] = (rsi > 70).astype(float)

    macd_df = compute_macd(close)
    features[f"{prefix}macd"] = macd_df["macd"]
    features[f"{prefix}macd_signal"] = macd_df["macd_signal"]
    features[f"{prefix}macd_hist"] = macd_df["macd_hist"]
    features[f"{prefix}macd_bullish"] = (macd_df["macd_hist"] > 0).astype(float)
    features[f"{prefix}macd_cross_up"] = (
        (macd_df["macd_hist"] > 0) & (macd_df["macd_hist"].shift(1) <= 0)
    ).astype(float)

    for period in [9, 21, 50, 200]:
        ema = compute_ema(close, period)
        features[f"{prefix}ema_{period}"] = ema
        features[f"{prefix}price_above_ema_{period}"] = (close > ema).astype(float)

    atr = compute_atr(high, low, close)
    features[f"{prefix}atr"] = atr
    features[f"{prefix}atr_pct"] = atr / (close + 1e-10)
    features[f"{prefix}atr_expanding"] = (atr > atr.rolling(10).mean()).astype(float)

    bb = compute_bollinger_bands(close)
    features[f"{prefix}bb_bw"] = bb["bb_bw"]
    features[f"{prefix}bb_pct"] = bb["bb_pct"]
    features[f"{prefix}bb_squeeze"] = (bb["bb_bw"] < bb["bb_bw"].rolling(20).quantile(0.2)).astype(float)

    vwap = compute_vwap(high, low, close, volume)
    features[f"{prefix}vwap_dist"] = (close - vwap) / (vwap + 1e-10)
    features[f"{prefix}above_vwap"] = (close > vwap).astype(float)

    obv = compute_obv(close, volume)
    features[f"{prefix}obv_slope"] = obv.diff(5)
    features[f"{prefix}obv_rising"] = (obv.diff(5) > 0).astype(float)

    features[f"{prefix}volume_ratio"] = volume / (volume.rolling(20).mean() + 1e-10)
    features[f"{prefix}volume_spike"] = (features[f"{prefix}volume_ratio"] > 2.0).astype(float)

    features[f"{prefix}price_change_1"] = close.pct_change(1)
    features[f"{prefix}price_change_5"] = close.pct_change(5)
    features[f"{prefix}price_change_10"] = close.pct_change(10)

    # Trend alignment: price above all EMAs
    features[f"{prefix}trend_aligned"] = (
        (close > features.get(f"{prefix}ema_9", close)) &
        (close > features.get(f"{prefix}ema_21", close)) &
        (close > features.get(f"{prefix}ema_50", close))
    ).astype(float)

    stoch = compute_stoch_rsi(close)
    features[f"{prefix}stoch_k"] = stoch["stoch_k"]
    features[f"{prefix}stoch_d"] = stoch["stoch_d"]

    return features.ffill().bfill()
