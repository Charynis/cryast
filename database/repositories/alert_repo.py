from typing import Dict, List, Optional

import database.db_manager as db


def save_alert(alert: Dict) -> int:
    data = {
        "prediction_id": alert.get("prediction_id"),
        "created_at": db.now_str(),
        "alert_type": alert["alert_type"],
        "severity": alert["severity"],
        "message": alert["message"],
        "symbol": alert["symbol"],
        "dismissed": 0,
    }
    return db.insert("alerts", data)


def get_active_alerts(limit: int = 20) -> List[Dict]:
    rows = db.fetchall(
        "SELECT * FROM alerts WHERE dismissed = 0 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    return [dict(r) for r in rows]


def get_all_alerts(limit: int = 100) -> List[Dict]:
    rows = db.fetchall(
        "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    return [dict(r) for r in rows]


def dismiss_alert(alert_id: int):
    db.update("alerts", {"dismissed": 1, "dismissed_at": db.now_str()}, "id = ?", (alert_id,))


def dismiss_all_alerts():
    db.execute("UPDATE alerts SET dismissed = 1, dismissed_at = ? WHERE dismissed = 0", (db.now_str(),))


def save_regime(regime_data: Dict) -> int:
    data = {
        "detected_at": db.now_str(),
        "regime": regime_data["regime"],
        "confidence": regime_data["confidence"],
        "btc_price": regime_data.get("btc_price"),
        "btc_dominance": regime_data.get("btc_dominance"),
        "fear_greed_index": regime_data.get("fear_greed_index"),
        "total_market_cap_b": regime_data.get("total_market_cap_b"),
        "danger_flags": str(regime_data.get("danger_flags", [])),
    }
    return db.insert("regime_history", data)


def get_latest_regime() -> Optional[Dict]:
    row = db.fetchone("SELECT * FROM regime_history ORDER BY detected_at DESC LIMIT 1")
    return dict(row) if row else None
