import json
from datetime import datetime
from typing import List, Optional, Dict, Any

import database.db_manager as db


def save_prediction(pred: Dict[str, Any]) -> int:
    data = {
        "symbol": pred["symbol"],
        "created_at": db.now_str(),
        "entry_price_low": pred["entry_price_low"],
        "entry_price_high": pred["entry_price_high"],
        "stop_loss": pred["stop_loss"],
        "target_1": pred["target_1"],
        "target_2": pred.get("target_2"),
        "swing_probability": pred["swing_probability"],
        "confidence_score": pred["confidence_score"],
        "risk_score": pred["risk_score"],
        "regime_at_entry": pred["regime_at_entry"],
        "rr_ratio": pred["rr_ratio"],
        "expected_gain_pct": pred["expected_gain_pct"],
        "expected_duration_h": pred["expected_duration_h"],
        "setup_type": pred["setup_type"],
        "reason_json": json.dumps(pred.get("reasons", [])),
        "status": "active",
    }
    return db.insert("predictions", data)


def get_active_predictions() -> List[Dict]:
    rows = db.fetchall("SELECT * FROM predictions WHERE status = 'active' ORDER BY created_at DESC")
    return [_row_to_dict(r) for r in rows]


def get_prediction_by_id(pred_id: int) -> Optional[Dict]:
    row = db.fetchone("SELECT * FROM predictions WHERE id = ?", (pred_id,))
    return _row_to_dict(row) if row else None


def get_prediction_history(limit: int = 50) -> List[Dict]:
    rows = db.fetchall(
        "SELECT * FROM predictions WHERE status != 'active' ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    return [_row_to_dict(r) for r in rows]


def close_prediction(pred_id: int, outcome: str, exit_price: float, profit_pct: float):
    entry_time_row = db.fetchone("SELECT created_at FROM predictions WHERE id = ?", (pred_id,))
    duration_h = 0
    if entry_time_row:
        try:
            created = datetime.strptime(entry_time_row["created_at"], "%Y-%m-%d %H:%M:%S")
            duration_h = (datetime.utcnow() - created).total_seconds() / 3600
        except Exception:
            pass

    db.update("predictions", {
        "status": "completed",
        "outcome": outcome,
        "actual_exit_price": exit_price,
        "actual_profit_pct": profit_pct,
        "closed_at": db.now_str(),
        "time_to_outcome_h": round(duration_h, 1),
    }, "id = ?", (pred_id,))


def invalidate_prediction(pred_id: int, reason: str):
    db.update("predictions", {
        "status": "invalidated",
        "outcome": "invalidated",
        "closed_at": db.now_str(),
    }, "id = ?", (pred_id,))


def save_monitor_log(log: Dict[str, Any]) -> int:
    data = {
        "prediction_id": log["prediction_id"],
        "checked_at": db.now_str(),
        "current_price": log["current_price"],
        "current_profit_pct": log["current_profit_pct"],
        "swing_probability": log["swing_probability"],
        "trade_status": log["trade_status"],
        "momentum_score": log.get("momentum_score"),
        "volume_score": log.get("volume_score"),
        "btc_influence_score": log.get("btc_influence_score"),
        "invalidation_flags": json.dumps(log.get("invalidation_flags", [])),
        "recommended_action": log.get("recommended_action"),
    }
    return db.insert("monitoring_log", data)


def get_latest_monitor_log(pred_id: int) -> Optional[Dict]:
    row = db.fetchone(
        "SELECT * FROM monitoring_log WHERE prediction_id = ? ORDER BY checked_at DESC LIMIT 1",
        (pred_id,)
    )
    return _row_to_dict(row) if row else None


def _row_to_dict(row) -> Dict:
    if row is None:
        return {}
    d = dict(row)
    if "reason_json" in d and d["reason_json"]:
        try:
            d["reasons"] = json.loads(d["reason_json"])
        except Exception:
            d["reasons"] = []
    if "invalidation_flags" in d and d["invalidation_flags"]:
        try:
            d["invalidation_flags"] = json.loads(d["invalidation_flags"])
        except Exception:
            d["invalidation_flags"] = []
    return d
