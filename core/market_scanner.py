import time
from typing import Dict, List, Optional

import pandas as pd

from config import (
    TOP_COINS_COUNT, MIN_VOLUME_24H_USD, MIN_RR_RATIO,
    MIN_CONFIDENCE_SCORE, TIMEFRAMES, CANDLES_PER_TIMEFRAME, TOP_RECOMMENDATIONS
)
from data.exchange_client import get_exchange_client
from data.coingecko_client import get_top_coins
from features.feature_builder import build_features
from ml.predictor import get_predictor
from utils.math_helpers import (
    find_support_resistance, compute_targets,
    compute_stop_loss, compute_rr_ratio, estimate_trade_duration
)
from features.technical_indicators import compute_atr as ta_atr
from utils.logger import get_logger

logger = get_logger(__name__)


def scan_market(regime: Dict, progress_callback=None) -> List[Dict]:
    """Scan top coins and return ranked trading opportunities."""
    if not regime.get("is_tradeable", True):
        logger.info("Market regime is dangerous - no recommendations")
        return []

    client = get_exchange_client()
    predictor = get_predictor()

    coins = get_top_coins(TOP_COINS_COUNT)
    logger.info(f"Scanning {len(coins)} coins...")

    btc_ohlcv = {}
    for tf in ["1h", "4h"]:
        df = client.fetch_ohlcv("BTC/USDT", tf, limit=CANDLES_PER_TIMEFRAME.get(tf, 100))
        if df is not None:
            btc_ohlcv[tf] = df
        time.sleep(0.2)

    opportunities = []
    total = len(coins)

    for i, coin in enumerate(coins):
        symbol = coin["symbol"]

        if symbol in ("BTC/USDT", "ETH/USDT"):
            continue

        if progress_callback:
            progress_callback(f"Scanning {symbol}...", i / total)

        ohlcv_by_tf = {}
        for tf in TIMEFRAMES:
            df = client.fetch_ohlcv(symbol, tf, limit=CANDLES_PER_TIMEFRAME.get(tf, 100))
            if df is not None and len(df) >= 30:
                ohlcv_by_tf[tf] = df
            time.sleep(0.15)

        if not ohlcv_by_tf:
            continue

        primary_df = ohlcv_by_tf.get("1h") or ohlcv_by_tf.get("4h")
        if primary_df is None or len(primary_df) < 50:
            continue

        features = build_features(ohlcv_by_tf, btc_ohlcv if btc_ohlcv else None)
        if features is None:
            continue

        swing_prob = predictor.predict_swing(features)
        risk_score = predictor.predict_risk(features)
        confidence = predictor.compute_confidence(swing_prob, risk_score)
        opp_score = predictor.compute_opportunity_score(swing_prob, risk_score, regime["regime"])

        if opp_score < MIN_CONFIDENCE_SCORE:
            continue

        close = primary_df["close"]
        high = primary_df["high"]
        low = primary_df["low"]

        current_price = float(close.iloc[-1])
        atr_series = ta_atr(high, low, close, period=14)
        atr = float(atr_series.iloc[-1])

        stop_loss = compute_stop_loss(current_price, atr, multiplier=1.5)
        target_1, target_2 = compute_targets(current_price, stop_loss, rr1=2.0, rr2=3.5)
        rr = compute_rr_ratio(current_price, stop_loss, target_1)

        if rr < MIN_RR_RATIO:
            continue

        support_levels, resistance_levels = find_support_resistance(primary_df, window=5)
        if resistance_levels:
            nearest_res = min((r for r in resistance_levels if r > current_price * 1.005), default=target_1)
            target_1 = min(target_1, nearest_res) if nearest_res > current_price else target_1

        atr_per_hour = float(atr_series.diff().abs().rolling(5).mean().iloc[-1]) if len(atr_series) > 5 else atr * 0.01
        est_duration = estimate_trade_duration(current_price, target_1, max(atr_per_hour, atr * 0.005))

        reasons = _build_reasons(features, coin, regime)
        setup_type = _classify_setup(features)

        expected_gain = round((target_1 - current_price) / current_price * 100, 2)

        opportunity = {
            "symbol": symbol,
            "name": coin.get("name", symbol),
            "opportunity_score": opp_score,
            "swing_probability": swing_prob,
            "confidence_score": confidence,
            "risk_score": risk_score,
            "current_price": current_price,
            "entry_price_low": round(current_price * 0.998, 8),
            "entry_price_high": round(current_price * 1.003, 8),
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "rr_ratio": rr,
            "expected_gain_pct": expected_gain,
            "expected_duration_h": est_duration,
            "setup_type": setup_type,
            "reasons": reasons,
            "regime_at_entry": regime["regime"],
            "volume_24h": coin.get("volume_24h_usd", 0),
            "market_cap_rank": coin.get("market_cap_rank"),
            "atr": atr,
        }
        opportunities.append(opportunity)

    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    top = opportunities[:TOP_RECOMMENDATIONS]

    logger.info(f"Scan complete: {len(top)} recommendations from {len(opportunities)} candidates")
    return top


def _build_reasons(features: pd.Series, coin: Dict, regime: Dict) -> List[str]:
    reasons = []

    rsi = features.get("1h_rsi", 50)
    if 40 < rsi < 65:
        reasons.append("RSI in healthy zone")
    if features.get("1h_macd_bullish", 0):
        reasons.append("MACD bullish momentum")
    if features.get("1h_macd_cross_up", 0):
        reasons.append("MACD bullish crossover")
    if features.get("1h_trend_aligned", 0):
        reasons.append("Price above key EMAs")
    if features.get("1h_volume_ratio", 1) > 1.5:
        reasons.append("Volume expansion detected")
    if features.get("1h_above_vwap", 0):
        reasons.append("Trading above VWAP")
    if features.get("bullish_structure", 0):
        reasons.append("Higher highs & higher lows")
    if features.get("btc_recent_strength", 0) > 0.01:
        reasons.append("BTC showing strength")
    if features.get("1h_bb_squeeze", 0):
        reasons.append("Bollinger Band squeeze (breakout potential)")
    if features.get("1h_obv_rising", 0):
        reasons.append("OBV trending up")
    if regime["regime"] == "bull":
        reasons.append("Bullish market regime")

    return reasons[:6] if reasons else ["Momentum signal detected"]


def _classify_setup(features: pd.Series) -> str:
    bb_squeeze = features.get("1h_bb_squeeze", 0)
    volume_spike = features.get("1h_volume_spike", 0)
    rsi = features.get("1h_rsi", 50)
    trend_aligned = features.get("1h_trend_aligned", 0)
    bb_pct = features.get("1h_bb_pct", 0.5)

    if bb_squeeze and volume_spike:
        return "breakout"
    elif trend_aligned and 0.3 < bb_pct < 0.6:
        return "momentum"
    elif bb_pct < 0.35 and rsi < 50:
        return "pullback"
    elif rsi > 60 and trend_aligned:
        return "trend_continuation"
    else:
        return "momentum"
