import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

from features.technical_indicators import compute_all_indicators, compute_atr
from utils.math_helpers import find_support_resistance
from utils.logger import get_logger

logger = get_logger(__name__)


def build_features(ohlcv_by_tf: Dict[str, pd.DataFrame], btc_ohlcv: Optional[Dict[str, pd.DataFrame]] = None) -> Optional[pd.Series]:
    """
    Build a feature vector for a coin given multi-timeframe OHLCV data.
    Returns the most recent row as a Series.
    """
    feature_frames = []

    for tf in ["15m", "1h", "4h", "1d"]:
        df = ohlcv_by_tf.get(tf)
        if df is None or len(df) < 30:
            continue
        tf_features = compute_all_indicators(df, prefix=f"{tf}_")
        if not tf_features.empty:
            feature_frames.append(tf_features.iloc[-1])

    if not feature_frames:
        return None

    combined = pd.concat(feature_frames)

    primary_df = ohlcv_by_tf.get("1h") or ohlcv_by_tf.get("4h")
    if primary_df is not None and len(primary_df) > 20:
        support_levels, resistance_levels = find_support_resistance(primary_df, window=5)
        current_price = primary_df["close"].iloc[-1]

        nearest_sup = max((s for s in support_levels if s < current_price), default=current_price * 0.95)
        nearest_res = min((r for r in resistance_levels if r > current_price), default=current_price * 1.05)

        atr_vals = compute_atr(primary_df["high"], primary_df["low"], primary_df["close"])
        current_atr = atr_vals.iloc[-1] if len(atr_vals) > 0 else current_price * 0.02

        combined["support_dist_atr"] = (current_price - nearest_sup) / (current_atr + 1e-10)
        combined["resistance_dist_atr"] = (nearest_res - current_price) / (current_atr + 1e-10)
        combined["sr_ratio"] = combined["resistance_dist_atr"] / (combined["support_dist_atr"] + 1e-10)

        close_series = primary_df["close"]
        swing_highs = []
        swing_lows = []
        for i in range(3, len(close_series) - 3):
            if close_series.iloc[i] > close_series.iloc[i-3:i+4].max() * 0.999:
                swing_highs.append(close_series.iloc[i])
            if close_series.iloc[i] < close_series.iloc[i-3:i+4].min() * 1.001:
                swing_lows.append(close_series.iloc[i])

        if len(swing_highs) >= 2:
            combined["hh_pattern"] = float(swing_highs[-1] > swing_highs[-2])
        else:
            combined["hh_pattern"] = 0.5

        if len(swing_lows) >= 2:
            combined["hl_pattern"] = float(swing_lows[-1] > swing_lows[-2])
        else:
            combined["hl_pattern"] = 0.5

        combined["bullish_structure"] = float(combined["hh_pattern"] > 0.5 and combined["hl_pattern"] > 0.5)

    if btc_ohlcv:
        btc_df = btc_ohlcv.get("1h") or btc_ohlcv.get("4h")
        if btc_df is not None and primary_df is not None:
            min_len = min(len(btc_df), len(primary_df), 30)
            if min_len >= 10:
                coin_rets = primary_df["close"].pct_change().iloc[-min_len:]
                btc_rets = btc_df["close"].pct_change().iloc[-min_len:]
                coin_rets, btc_rets = coin_rets.align(btc_rets, join="inner")
                if len(coin_rets) >= 10 and btc_rets.std() > 0:
                    combined["btc_correlation"] = float(coin_rets.corr(btc_rets))
                    combined["btc_beta"] = float(coin_rets.cov(btc_rets) / (btc_rets.var() + 1e-10))
                    btc_ret_last = float(btc_rets.iloc[-1]) if len(btc_rets) > 0 else 0
                    combined["btc_momentum"] = btc_ret_last
                    combined["btc_recent_strength"] = float(btc_df["close"].pct_change(5).iloc[-1])
                else:
                    _set_btc_defaults(combined)
            else:
                _set_btc_defaults(combined)
    else:
        _set_btc_defaults(combined)

    combined = combined.replace([np.inf, -np.inf], 0).fillna(0)
    return combined


def _set_btc_defaults(features: pd.Series):
    features["btc_correlation"] = 0.5
    features["btc_beta"] = 1.0
    features["btc_momentum"] = 0.0
    features["btc_recent_strength"] = 0.0


def build_feature_matrix_for_training(ohlcv_df: pd.DataFrame, prefix: str = "1h_") -> pd.DataFrame:
    """Build a rolling feature matrix for ML training from a single-timeframe DataFrame."""
    features = compute_all_indicators(ohlcv_df, prefix=prefix)

    close = ohlcv_df["close"]
    high = ohlcv_df["high"]
    low = ohlcv_df["low"]

    swing_highs_flag = pd.Series(0.0, index=ohlcv_df.index)
    swing_lows_flag = pd.Series(0.0, index=ohlcv_df.index)
    for i in range(5, len(close) - 5):
        if close.iloc[i] >= close.iloc[i-5:i+6].max() * 0.998:
            swing_highs_flag.iloc[i] = 1.0
        if close.iloc[i] <= close.iloc[i-5:i+6].min() * 1.002:
            swing_lows_flag.iloc[i] = 1.0

    features[f"{prefix}swing_high"] = swing_highs_flag
    features[f"{prefix}swing_low"] = swing_lows_flag

    features[f"{prefix}hh_pattern"] = (close.rolling(20).max().diff() > 0).astype(float)
    features[f"{prefix}ll_pattern"] = (close.rolling(20).min().diff() < 0).astype(float)

    return features.replace([np.inf, -np.inf], 0).fillna(0)
