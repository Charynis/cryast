from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import (
    DANGER_FEAR_GREED_MAX, DANGER_BTC_DROP_4H, SIDEWAYS_ATR_RATIO
)
from data.exchange_client import get_exchange_client
from data.sentiment_client import get_fear_greed_value
from data.coingecko_client import get_btc_dominance, get_total_market_cap
from features.feature_builder import build_features
from ml.predictor import get_predictor
from utils.logger import get_logger

logger = get_logger(__name__)

REGIME_COLORS = {
    "bull": "green",
    "bear": "red",
    "sideways": "orange",
    "dangerous": "darkred",
}

REGIME_ICONS = {
    "bull": "🟢",
    "bear": "🔴",
    "sideways": "🟡",
    "dangerous": "🚨",
}


def detect_market_regime() -> Dict:
    """Detect current market regime using BTC data + sentiment."""
    client = get_exchange_client()
    predictor = get_predictor()

    btc_1h = client.fetch_ohlcv("BTC/USDT", "1h", limit=200)
    btc_4h = client.fetch_ohlcv("BTC/USDT", "4h", limit=100)
    btc_1d = client.fetch_ohlcv("BTC/USDT", "1d", limit=60)

    btc_ohlcv_by_tf = {
        "1h": btc_1h,
        "4h": btc_4h,
        "1d": btc_1d,
    }

    danger_flags: List[str] = []
    regime_override: Optional[str] = None

    fear_greed = get_fear_greed_value()
    if fear_greed <= DANGER_FEAR_GREED_MAX:
        danger_flags.append(f"extreme_fear (FGI={fear_greed})")

    if btc_4h is not None and len(btc_4h) >= 5:
        btc_4h_change = (btc_4h["close"].iloc[-1] - btc_4h["close"].iloc[-4]) / btc_4h["close"].iloc[-4]
        if btc_4h_change < -DANGER_BTC_DROP_4H:
            danger_flags.append(f"btc_sharp_drop ({btc_4h_change*100:.1f}% in 4h)")
            regime_override = "dangerous"

    if btc_1h is not None and len(btc_1h) >= 50:
        atr = btc_1h["high"].sub(btc_1h["low"]).rolling(14).mean().iloc[-1]
        price_range = btc_1h["high"].iloc[-20:].max() - btc_1h["low"].iloc[-20:].min()
        if price_range < atr * SIDEWAYS_ATR_RATIO * 5:
            danger_flags.append("low_volatility_range")

    if regime_override:
        regime = regime_override
        confidence = 0.85
    else:
        features = build_features(btc_ohlcv_by_tf)
        if features is not None:
            regime, confidence = predictor.predict_regime(features)
        else:
            regime, confidence = "sideways", 0.5

    btc_price = None
    if btc_1h is not None and len(btc_1h) > 0:
        btc_price = float(btc_1h["close"].iloc[-1])

    btc_dominance = get_btc_dominance()
    total_mcap = get_total_market_cap()

    if len(danger_flags) >= 2 and regime not in ("dangerous",):
        regime = "dangerous"
        confidence = 0.75
        logger.warning(f"Regime forced to dangerous: {danger_flags}")

    result = {
        "regime": regime,
        "confidence": confidence,
        "btc_price": btc_price,
        "btc_dominance": btc_dominance,
        "fear_greed_index": fear_greed,
        "total_market_cap_b": total_mcap,
        "danger_flags": danger_flags,
        "is_dangerous": regime == "dangerous",
        "is_tradeable": regime not in ("dangerous",),
        "color": REGIME_COLORS.get(regime, "grey"),
        "icon": REGIME_ICONS.get(regime, "⚪"),
    }

    logger.info(f"Market regime: {regime} (confidence={confidence:.0%}), flags={danger_flags}")
    return result
