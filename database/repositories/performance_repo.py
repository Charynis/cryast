from typing import Dict, Optional, List
from datetime import datetime, timedelta

import database.db_manager as db
from utils.math_helpers import compute_profit_factor, compute_max_drawdown
import pandas as pd


def compute_and_save_metrics(period: str = "all_time"):
    if period == "all_time":
        rows = db.fetchall("SELECT * FROM predictions WHERE status != 'active'")
    elif period == "30d":
        cutoff = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        rows = db.fetchall("SELECT * FROM predictions WHERE status != 'active' AND created_at >= ?", (cutoff,))
    elif period == "7d":
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        rows = db.fetchall("SELECT * FROM predictions WHERE status != 'active' AND created_at >= ?", (cutoff,))
    else:
        rows = []

    if not rows:
        return None

    completed = [r for r in rows if dict(r).get("status") == "completed"]
    invalidations = [r for r in rows if dict(r).get("status") == "invalidated"]

    wins = [r for r in completed if (dict(r).get("actual_profit_pct") or 0) > 0]
    losses = [r for r in completed if (dict(r).get("actual_profit_pct") or 0) <= 0]

    profits = [(dict(r).get("actual_profit_pct") or 0) for r in wins]
    loss_vals = [(dict(r).get("actual_profit_pct") or 0) for r in losses]

    win_rate = len(wins) / len(completed) if completed else 0.0
    avg_profit = sum(profits) / len(profits) if profits else 0.0
    avg_loss = sum(loss_vals) / len(loss_vals) if loss_vals else 0.0
    pf = compute_profit_factor(profits, loss_vals)

    equity = pd.Series([0.0] + [(dict(r).get("actual_profit_pct") or 0) for r in completed]).cumsum()
    max_dd = compute_max_drawdown(equity)

    durations = [(dict(r).get("time_to_outcome_h") or 0) for r in completed]
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    rr_vals = [(dict(r).get("rr_ratio") or 0) for r in completed]
    avg_rr = sum(rr_vals) / len(rr_vals) if rr_vals else 0.0

    setup_wins: Dict[str, int] = {}
    setup_losses: Dict[str, int] = {}
    for r in completed:
        rd = dict(r)
        st = rd.get("setup_type", "unknown")
        if (rd.get("actual_profit_pct") or 0) > 0:
            setup_wins[st] = setup_wins.get(st, 0) + 1
        else:
            setup_losses[st] = setup_losses.get(st, 0) + 1

    best_setup = max(setup_wins, key=setup_wins.get) if setup_wins else None
    worst_setup = max(setup_losses, key=setup_losses.get) if setup_losses else None

    high_conf = [r for r in completed if (dict(r).get("confidence_score") or 0) >= 0.6]
    high_conf_wins = [r for r in high_conf if (dict(r).get("actual_profit_pct") or 0) > 0]
    model_acc = len(high_conf_wins) / len(high_conf) if high_conf else 0.0

    data = {
        "computed_at": db.now_str(),
        "period": period,
        "total_predictions": len(rows),
        "completed_trades": len(completed),
        "wins": len(wins),
        "losses": len(losses),
        "invalidations": len(invalidations),
        "win_rate": round(win_rate, 4),
        "avg_profit_pct": round(avg_profit, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": pf,
        "max_drawdown_pct": max_dd,
        "avg_rr_achieved": round(avg_rr, 2),
        "avg_duration_h": round(avg_dur, 1),
        "best_setup_type": best_setup,
        "worst_setup_type": worst_setup,
        "model_accuracy": round(model_acc, 4),
    }
    db.insert("performance_metrics", data)
    return data


def get_latest_metrics(period: str = "all_time") -> Optional[Dict]:
    row = db.fetchone(
        "SELECT * FROM performance_metrics WHERE period = ? ORDER BY computed_at DESC LIMIT 1",
        (period,)
    )
    return dict(row) if row else None


def get_all_completed_predictions() -> List[Dict]:
    rows = db.fetchall(
        "SELECT * FROM predictions WHERE status = 'completed' ORDER BY closed_at DESC"
    )
    return [dict(r) for r in rows]
