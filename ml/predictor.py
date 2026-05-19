import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple, List

from ml.model_registry import load_model, get_feature_names
from utils.logger import get_logger

logger = get_logger(__name__)

REGIME_LABELS = {0: "bear", 1: "sideways", 2: "bull", 3: "dangerous"}
REGIME_REVERSE = {v: k for k, v in REGIME_LABELS.items()}


class Predictor:
    def __init__(self):
        self._swing_model = None
        self._risk_model = None
        self._regime_model = None
        self._swing_features: Optional[List[str]] = None
        self._risk_features: Optional[List[str]] = None
        self._regime_features: Optional[List[str]] = None
        self._loaded = False

    def load_models(self) -> bool:
        self._swing_model = load_model("swing_classifier")
        self._risk_model = load_model("risk_scorer")
        self._regime_model = load_model("regime_classifier")

        self._swing_features = get_feature_names("swing_classifier")
        self._risk_features = get_feature_names("risk_scorer")
        self._regime_features = get_feature_names("regime_classifier")

        self._loaded = all([self._swing_model, self._risk_model, self._regime_model])
        if self._loaded:
            logger.info("All prediction models loaded successfully")
        else:
            logger.warning("Some models not available - using heuristic scoring")
        return self._loaded

    def predict_swing(self, features: pd.Series) -> float:
        """Return probability (0-1) that this setup hits target before stop loss."""
        if self._swing_model is None:
            return self._heuristic_swing_score(features)

        try:
            X = self._align_features(features, self._swing_features)
            prob = float(self._swing_model.predict_proba(X)[0][1])
            return round(prob, 4)
        except Exception as e:
            logger.debug(f"Swing prediction error: {e}")
            return self._heuristic_swing_score(features)

    def predict_risk(self, features: pd.Series) -> float:
        """Return risk score (0-1, higher = riskier)."""
        if self._risk_model is None:
            return self._heuristic_risk_score(features)

        try:
            X = self._align_features(features, self._risk_features)
            prob = float(self._risk_model.predict_proba(X)[0][1])
            return round(prob, 4)
        except Exception as e:
            logger.debug(f"Risk prediction error: {e}")
            return self._heuristic_risk_score(features)

    def predict_regime(self, features: pd.Series) -> Tuple[str, float]:
        """Return (regime_name, confidence)."""
        if self._regime_model is None:
            return self._heuristic_regime(features)

        try:
            X = self._align_features(features, self._regime_features)
            pred = int(self._regime_model.predict(X)[0])
            proba = self._regime_model.predict_proba(X)[0]
            confidence = float(proba[pred])
            return REGIME_LABELS.get(pred, "sideways"), round(confidence, 4)
        except Exception as e:
            logger.debug(f"Regime prediction error: {e}")
            return self._heuristic_regime(features)

    def compute_confidence(self, swing_prob: float, risk_score: float) -> float:
        """Aggregate confidence score from swing probability and risk."""
        raw = swing_prob * (1 - risk_score * 0.5)
        return round(min(max(raw, 0.0), 1.0), 4)

    def compute_opportunity_score(self, swing_prob: float, risk_score: float, regime: str) -> float:
        regime_multiplier = {
            "bull": 1.0,
            "sideways": 0.7,
            "bear": 0.4,
            "dangerous": 0.1,
        }.get(regime, 0.7)
        score = swing_prob * (1 - risk_score) * regime_multiplier
        return round(min(max(score, 0.0), 1.0), 4)

    def _align_features(self, features: pd.Series, expected_names: Optional[List[str]]) -> np.ndarray:
        if expected_names is None:
            return features.values.reshape(1, -1)

        aligned = pd.Series(0.0, index=expected_names)
        common = [f for f in expected_names if f in features.index]
        aligned[common] = features[common]
        return aligned.values.reshape(1, -1)

    def _heuristic_swing_score(self, features: pd.Series) -> float:
        score = 0.5
        rsi = features.get("1h_rsi", 50)
        macd_bullish = features.get("1h_macd_bullish", 0)
        trend_aligned = features.get("1h_trend_aligned", 0)
        volume_ratio = features.get("1h_volume_ratio", 1)
        above_vwap = features.get("1h_above_vwap", 0)
        btc_strength = features.get("btc_recent_strength", 0)
        bullish_struct = features.get("bullish_structure", 0)
        bb_pct = features.get("1h_bb_pct", 0.5)

        if 35 <= rsi <= 65:
            score += 0.05
        if rsi > 50:
            score += 0.05
        if macd_bullish:
            score += 0.08
        if trend_aligned:
            score += 0.1
        if volume_ratio > 1.3:
            score += 0.07
        if above_vwap:
            score += 0.05
        if btc_strength > 0:
            score += 0.05
        if bullish_struct:
            score += 0.1
        if 0.3 <= bb_pct <= 0.7:
            score += 0.03
        if rsi > 70 or rsi < 25:
            score -= 0.1

        return round(min(max(score, 0.1), 0.9), 4)

    def _heuristic_risk_score(self, features: pd.Series) -> float:
        risk = 0.3
        atr_pct = features.get("1h_atr_pct", 0.02)
        bb_bw = features.get("1h_bb_bw", 0.05)
        rsi = features.get("1h_rsi", 50)
        volume_ratio = features.get("1h_volume_ratio", 1)

        if atr_pct > 0.04:
            risk += 0.2
        if bb_bw > 0.1:
            risk += 0.15
        if rsi > 75 or rsi < 25:
            risk += 0.15
        if volume_ratio > 3:
            risk += 0.1

        return round(min(max(risk, 0.1), 0.9), 4)

    def _heuristic_regime(self, features: pd.Series) -> Tuple[str, float]:
        btc_strength = features.get("btc_recent_strength", 0)
        trend_aligned = features.get("1h_trend_aligned", 0)
        above_vwap = features.get("1h_above_vwap", 0)
        atr_pct = features.get("1h_atr_pct", 0.02)

        if atr_pct > 0.05:
            return "dangerous", 0.7
        if btc_strength > 0.02 and trend_aligned and above_vwap:
            return "bull", 0.7
        if btc_strength < -0.02:
            return "bear", 0.65
        return "sideways", 0.6


_predictor: Optional[Predictor] = None


def get_predictor() -> Predictor:
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
        _predictor.load_models()
    return _predictor
