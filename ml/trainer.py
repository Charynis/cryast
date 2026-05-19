import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.preprocessing import LabelEncoder

from config import TRAINING_HISTORY_DAYS, LABEL_TARGET_PCT, LABEL_SL_PCT, LABEL_WINDOW_1H
from data.exchange_client import get_exchange_client
from features.feature_builder import build_feature_matrix_for_training
from ml.label_builder import build_labels_for_df, build_regime_label
from ml.model_registry import save_model, all_models_exist
from utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_MODELS = ["swing_classifier", "risk_scorer", "regime_classifier"]

TRAINING_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "MATIC/USDT", "UNI/USDT", "LTC/USDT", "ATOM/USDT", "FIL/USDT",
    "NEAR/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "INJ/USDT",
]


def models_need_training() -> bool:
    return not all_models_exist(REQUIRED_MODELS)


def train_all_models(progress_callback: Optional[Callable] = None):
    """Full training pipeline. Downloads historical data, builds features/labels, trains models."""
    logger.info("Starting model training pipeline...")

    client = get_exchange_client()
    all_features = []
    all_labels_swing = []
    all_labels_risk = []
    btc_dfs = []

    total_symbols = len(TRAINING_SYMBOLS)
    for i, symbol in enumerate(TRAINING_SYMBOLS):
        if progress_callback:
            progress_callback(f"Fetching data: {symbol} ({i+1}/{total_symbols})", i / total_symbols)

        df = client.fetch_ohlcv(symbol, "1h", limit=min(TRAINING_HISTORY_DAYS * 24, 1500))
        if df is None or len(df) < 200:
            logger.warning(f"Insufficient data for {symbol}, skipping")
            continue

        if symbol == "BTC/USDT":
            btc_dfs.append(df.copy())

        logger.info(f"  {symbol}: {len(df)} candles")
        time.sleep(0.3)

        try:
            features = build_feature_matrix_for_training(df, prefix="1h_")
            labels_swing = build_labels_for_df(df, LABEL_TARGET_PCT, LABEL_SL_PCT, LABEL_WINDOW_1H)

            labels_risk = pd.Series(0, index=df.index, name="risk_label")
            close = df["close"]
            for j in range(len(df)):
                if j < 10:
                    continue
                vol = close.pct_change().iloc[max(0, j-10):j].std()
                labels_risk.iloc[j] = 1 if vol > 0.03 else 0

            common_idx = features.index.intersection(labels_swing.index)
            if len(common_idx) < 50:
                continue

            features_aligned = features.loc[common_idx]
            labels_swing_aligned = labels_swing.loc[common_idx]
            labels_risk_aligned = labels_risk.loc[common_idx]

            all_features.append(features_aligned)
            all_labels_swing.append(labels_swing_aligned)
            all_labels_risk.append(labels_risk_aligned)

        except Exception as e:
            logger.warning(f"Feature/label building failed for {symbol}: {e}")
            continue

    if not all_features:
        logger.error("No training data collected. Aborting training.")
        return False

    if progress_callback:
        progress_callback("Assembling training dataset...", 0.7)

    X = pd.concat(all_features, ignore_index=True)
    y_swing = pd.concat(all_labels_swing, ignore_index=True)
    y_risk = pd.concat(all_labels_risk, ignore_index=True)

    X = X.replace([np.inf, -np.inf], 0).fillna(0)

    logger.info(f"Training dataset: {len(X)} samples, {X.shape[1]} features")
    logger.info(f"Swing label balance: {y_swing.value_counts().to_dict()}")

    feature_names = list(X.columns)

    if progress_callback:
        progress_callback("Training swing trade classifier (XGBoost)...", 0.75)
    _train_swing_classifier(X, y_swing, feature_names)

    if progress_callback:
        progress_callback("Training risk scorer (LightGBM)...", 0.85)
    _train_risk_scorer(X, y_risk, feature_names)

    if progress_callback:
        progress_callback("Training regime classifier...", 0.92)
    _train_regime_classifier(btc_dfs if btc_dfs else all_features[:1])

    if progress_callback:
        progress_callback("Training complete!", 1.0)

    logger.info("All models trained successfully.")
    return True


def _train_swing_classifier(X: pd.DataFrame, y: pd.Series, feature_names: List[str]):
    try:
        import xgboost as xgb
    except ImportError:
        logger.warning("XGBoost not available, using LightGBM fallback")
        return _train_swing_classifier_lgbm(X, y, feature_names)

    pos = y.sum()
    neg = len(y) - pos
    scale_pw = neg / (pos + 1e-10)

    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pw,
        use_label_encoder=False,
        eval_metric="auc",
        early_stopping_rounds=30,
        n_jobs=-1,
        verbosity=0,
    )

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_pred_proba = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred_proba)
    logger.info(f"Swing classifier AUC: {auc:.4f}")

    save_model("swing_classifier", model, feature_names, {"auc": auc, "n_samples": len(X)})


def _train_swing_classifier_lgbm(X: pd.DataFrame, y: pd.Series, feature_names: List[str]):
    import lightgbm as lgb

    pos = y.sum()
    neg = len(y) - pos
    scale_pw = neg / (pos + 1e-10)

    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        scale_pos_weight=scale_pw,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])

    y_pred_proba = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred_proba)
    logger.info(f"Swing classifier (LightGBM) AUC: {auc:.4f}")

    save_model("swing_classifier", model, feature_names, {"auc": auc, "n_samples": len(X)})


def _train_risk_scorer(X: pd.DataFrame, y: pd.Series, feature_names: List[str]):
    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("LightGBM not available, skipping risk scorer")
        return

    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_pred_proba = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred_proba)
    logger.info(f"Risk scorer AUC: {auc:.4f}")

    save_model("risk_scorer", model, feature_names, {"auc": auc, "n_samples": len(X)})


def _train_regime_classifier(btc_dfs: List[pd.DataFrame]):
    try:
        from catboost import CatBoostClassifier
    except ImportError:
        logger.warning("CatBoost not available, using LightGBM for regime")
        _train_regime_lgbm(btc_dfs)
        return

    from features.feature_builder import build_feature_matrix_for_training
    from ml.label_builder import build_regime_label

    all_X = []
    all_y = []

    for df in btc_dfs:
        if len(df) < 100:
            continue
        features = build_feature_matrix_for_training(df, prefix="1h_")
        labels = [build_regime_label(df, i) for i in range(len(df))]
        labels_series = pd.Series(labels, index=df.index, name="regime")

        common_idx = features.index.intersection(labels_series.index)
        all_X.append(features.loc[common_idx])
        all_y.append(labels_series.loc[common_idx])

    if not all_X:
        return

    X = pd.concat(all_X, ignore_index=True).replace([np.inf, -np.inf], 0).fillna(0)
    y = pd.concat(all_y, ignore_index=True)

    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    model = CatBoostClassifier(
        iterations=200,
        depth=6,
        learning_rate=0.1,
        verbose=0,
    )
    model.fit(X_train, y_train)

    acc = accuracy_score(y_val, model.predict(X_val))
    logger.info(f"Regime classifier accuracy: {acc:.4f}")

    save_model("regime_classifier", model, list(X.columns), {"accuracy": acc, "n_samples": len(X)})


def _train_regime_lgbm(btc_dfs: List[pd.DataFrame]):
    try:
        import lightgbm as lgb
    except ImportError:
        return

    from features.feature_builder import build_feature_matrix_for_training
    from ml.label_builder import build_regime_label

    all_X, all_y = [], []
    for df in btc_dfs:
        if len(df) < 100:
            continue
        features = build_feature_matrix_for_training(df, prefix="1h_")
        labels = pd.Series([build_regime_label(df, i) for i in range(len(df))], index=df.index)
        common_idx = features.index.intersection(labels.index)
        all_X.append(features.loc[common_idx])
        all_y.append(labels.loc[common_idx])

    if not all_X:
        return

    X = pd.concat(all_X, ignore_index=True).replace([np.inf, -np.inf], 0).fillna(0)
    y = pd.concat(all_y, ignore_index=True)

    model = lgb.LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, n_jobs=-1, verbose=-1)
    model.fit(X, y)

    save_model("regime_classifier", model, list(X.columns), {"n_samples": len(X)})
    logger.info("Regime classifier (LightGBM) trained")
