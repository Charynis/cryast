from typing import Dict, List, Optional

import pandas as pd

from config import (
    INVALIDATION_SL_BREACH_FACTOR, INVALIDATION_VOLUME_COLLAPSE_RATIO,
    INVALIDATION_BTC_DROP_THRESHOLD
)
from data.exchange_client import get_exchange_client
from data.data_cache import cache
from features.technical_indicators import compute_atr as ta_atr, compute_rsi, compute_macd
from utils.logger import get_logger

logger = get_logger(__name__)

STATUS_STRONG = "Strong"
STATUS_STABLE = "Stable"
STATUS_WEAKENING = "Weakening"
STATUS_DANGEROUS = "Dangerous"
STATUS_EXIT = "Exit Suggested"

STATUS_COLORS = {
    STATUS_STRONG: "#00C853",
    STATUS_STABLE: "#64B5F6",
    STATUS_WEAKENING: "#FFB300",
    STATUS_DANGEROUS: "#FF6D00",
    STATUS_EXIT: "#D50000",
}


def check_invalidation(prediction: Dict) -> Dict:
    """
    Re-evaluate a prediction against current market data.
    Returns dict with: status, flags, action, updated swing_prob, etc.
    """
    symbol = prediction["symbol"]
    client = get_exchange_client()

    df_1h = client.fetch_ohlcv(symbol, "1h", limit=100)
    df_4h = client.fetch_ohlcv(symbol, "4h", limit=50)
    btc_4h = client.fetch_ohlcv("BTC/USDT", "4h", limit=20)

    if df_1h is None or len(df_1h) < 20:
        return _build_result(STATUS_STABLE, [], "hold", prediction)

    current_price = float(df_1h["close"].iloc[-1])
    entry_price = prediction.get("entry_price_high", current_price)
    stop_loss = prediction["stop_loss"]
    target_1 = prediction["target_1"]

    current_profit_pct = (current_price - entry_price) / (entry_price + 1e-10) * 100

    flags: List[str] = []

    if current_price <= stop_loss:
        flags.append("stop_loss_hit")
        return _build_result(STATUS_EXIT, flags, "exit_immediately", prediction,
                             current_price, current_profit_pct, 0.05)

    if current_price >= target_1 * 0.99:
        flags.append("target_1_approaching")

    sl_proximity = (current_price - stop_loss) / (current_price + 1e-10)
    if sl_proximity < (1 - INVALIDATION_SL_BREACH_FACTOR):
        flags.append("near_stop_loss")

    if len(df_1h) >= 20:
        vol_avg = df_1h["volume"].rolling(20).mean().iloc[-1]
        current_vol = df_1h["volume"].iloc[-1]
        if vol_avg > 0 and current_vol / vol_avg < INVALIDATION_VOLUME_COLLAPSE_RATIO:
            flags.append("volume_collapse")

    atr_series = ta_atr(df_1h["high"], df_1h["low"], df_1h["close"])
    if len(atr_series) >= 20:
        atr_current = float(atr_series.iloc[-1])
        atr_avg = float(atr_series.rolling(20).mean().iloc[-1])
        if atr_current > atr_avg * 1.8:
            flags.append("volatility_spike")

    if len(df_1h) >= 14:
        rsi = float(compute_rsi(df_1h["close"]).iloc[-1])
        macd_df = compute_macd(df_1h["close"])
        macd_hist = float(macd_df["macd_hist"].iloc[-1])
        macd_hist_prev = float(macd_df["macd_hist"].iloc[-2]) if len(macd_df) > 2 else macd_hist

        if rsi < 40 and macd_hist < 0:
            flags.append("momentum_reversal")

        if macd_hist < 0 and macd_hist_prev >= 0:
            flags.append("macd_bearish_cross")

    if df_4h is not None and len(df_4h) >= 10:
        recent_highs = df_4h["high"].iloc[-5:]
        recent_lows = df_4h["low"].iloc[-5:]
        if recent_highs.is_monotonic_decreasing and recent_lows.is_monotonic_decreasing:
            flags.append("trend_structure_failed")

    if btc_4h is not None and len(btc_4h) >= 5:
        btc_change = (btc_4h["close"].iloc[-1] - btc_4h["close"].iloc[-4]) / btc_4h["close"].iloc[-4]
        if btc_change < -INVALIDATION_BTC_DROP_THRESHOLD:
            flags.append(f"btc_weakness ({btc_change*100:.1f}%)")

    status, action, swing_prob = _determine_status_and_action(flags, current_profit_pct, prediction)

    result = _build_result(status, flags, action, prediction, current_price, current_profit_pct, swing_prob)

    if flags:
        logger.info(f"{symbol} invalidation check: {status} | flags={flags}")

    return result


def _determine_status_and_action(flags, profit_pct, prediction) -> tuple:
    critical_flags = {"stop_loss_hit", "trend_structure_failed", "momentum_reversal"}
    warning_flags = {"volume_collapse", "volatility_spike", "macd_bearish_cross", "near_stop_loss", "btc_weakness"}

    critical = [f for f in flags if any(cf in f for cf in critical_flags)]
    warnings = [f for f in flags if any(wf in f for wf in warning_flags)]

    if critical:
        return STATUS_EXIT, "exit", 0.15
    if len(warnings) >= 2:
        return STATUS_DANGEROUS, "partial_exit", 0.3
    if len(warnings) == 1:
        if profit_pct > 2:
            return STATUS_WEAKENING, "tighten_sl", 0.45
        return STATUS_WEAKENING, "watch_closely", 0.45
    if profit_pct > 3:
        return STATUS_STRONG, "hold", 0.75
    return STATUS_STABLE, "hold", 0.6


def _build_result(status, flags, action, prediction,
                  current_price=None, profit_pct=None, swing_prob=None) -> Dict:
    if current_price is None:
        client = get_exchange_client()
        p = client.get_current_price(prediction["symbol"])
        current_price = p if p else prediction.get("entry_price_high", 0)

    if profit_pct is None:
        entry = prediction.get("entry_price_high", current_price)
        profit_pct = (current_price - entry) / (entry + 1e-10) * 100

    return {
        "prediction_id": prediction.get("id"),
        "symbol": prediction["symbol"],
        "status": status,
        "status_color": STATUS_COLORS.get(status, "#9E9E9E"),
        "invalidation_flags": flags,
        "recommended_action": action,
        "current_price": current_price,
        "current_profit_pct": round(profit_pct, 2),
        "swing_probability": round(swing_prob if swing_prob is not None else 0.5, 4),
        "target_1": prediction["target_1"],
        "stop_loss": prediction["stop_loss"],
        "is_invalidated": status == STATUS_EXIT,
        "requires_attention": status in (STATUS_WEAKENING, STATUS_DANGEROUS, STATUS_EXIT),
    }
