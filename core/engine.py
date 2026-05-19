import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable

from config import MONITOR_INTERVAL_MINUTES
from core.regime_detector import detect_market_regime
from core.market_scanner import scan_market
from core.invalidation_engine import check_invalidation, STATUS_EXIT
from database.repositories.trade_repo import (
    save_prediction, get_active_predictions, close_prediction,
    invalidate_prediction, save_monitor_log
)
from database.repositories.alert_repo import save_alert, save_regime
from database.repositories.performance_repo import compute_and_save_metrics
from data.exchange_client import get_exchange_client
from data.websocket_manager import WebSocketManager
from ml.predictor import get_predictor
from utils.logger import get_logger

logger = get_logger(__name__)


class MainEngine:
    """Central orchestrator for market analysis, monitoring, and recommendations."""

    def __init__(self):
        self._regime: Optional[Dict] = None
        self._recommendations: List[Dict] = []
        self._active_trade_status: Dict[int, Dict] = {}
        self._last_analysis: Optional[datetime] = None
        self._analyzing = False
        self._ws_manager: Optional[WebSocketManager] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []
        self._status_message: str = "Initializing..."
        self._progress: float = 0.0

    def add_progress_callback(self, cb: Callable):
        self._progress_callbacks.append(cb)

    def _report_progress(self, msg: str, pct: float = None):
        self._status_message = msg
        if pct is not None:
            self._progress = pct
        for cb in self._progress_callbacks:
            try:
                cb(msg, pct)
            except Exception:
                pass
        logger.info(f"Progress [{pct or 0:.0%}]: {msg}")

    def initialize(self):
        """Run full startup analysis pipeline."""
        self._analyzing = True
        self._report_progress("Detecting market regime...", 0.1)

        try:
            regime = detect_market_regime()
            with self._lock:
                self._regime = regime

            save_regime(regime)
            self._report_progress(f"Market regime: {regime['regime'].upper()}", 0.25)

            if regime["is_tradeable"]:
                self._report_progress("Scanning market for opportunities...", 0.3)

                def scan_progress(msg, pct):
                    self._report_progress(msg, 0.3 + pct * 0.5)

                recommendations = scan_market(regime, scan_progress)
                with self._lock:
                    self._recommendations = recommendations

                for rec in recommendations:
                    save_prediction(rec)

                self._report_progress(f"Found {len(recommendations)} opportunities", 0.82)
            else:
                self._report_progress("Market dangerous - no recommendations generated", 0.82)

            self._report_progress("Loading active trades...", 0.88)
            active = get_active_predictions()
            symbols = list(set(r["symbol"] for r in recommendations + active))

            self._report_progress("Starting WebSocket streams...", 0.92)
            self._start_websocket(symbols)

            self._report_progress("Starting trade monitor...", 0.96)
            self._start_monitor_thread()

            self._last_analysis = datetime.utcnow()
            self._report_progress("Ready", 1.0)

        except Exception as e:
            logger.error(f"Engine initialization error: {e}", exc_info=True)
            self._report_progress(f"Error: {e}", 1.0)
        finally:
            self._analyzing = False

    def _start_websocket(self, symbols: List[str]):
        try:
            self._ws_manager = WebSocketManager()
            self._ws_manager.connect(symbols[:50])
        except Exception as e:
            logger.warning(f"WebSocket start failed: {e}")

    def _start_monitor_thread(self):
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="trade-monitor",
        )
        self._monitor_thread.start()

    def _monitor_loop(self):
        interval = MONITOR_INTERVAL_MINUTES * 60
        logger.info(f"Monitor thread started (interval={MONITOR_INTERVAL_MINUTES}min)")

        while not self._stop_event.is_set():
            try:
                self._run_monitor_cycle()
            except Exception as e:
                logger.error(f"Monitor cycle error: {e}", exc_info=True)
            self._stop_event.wait(interval)

    def _run_monitor_cycle(self):
        active_predictions = get_active_predictions()
        if not active_predictions:
            return

        logger.info(f"Monitoring {len(active_predictions)} active trades...")
        client = get_exchange_client()
        updated_statuses = {}

        for pred in active_predictions:
            pred_id = pred["id"]
            symbol = pred["symbol"]

            result = check_invalidation(pred)
            updated_statuses[pred_id] = result

            current_price = result["current_price"]
            profit_pct = result["current_profit_pct"]

            if current_price >= pred["target_1"] * 0.999:
                close_prediction(pred_id, "target_1_hit", current_price, profit_pct)
                save_alert({
                    "prediction_id": pred_id,
                    "alert_type": "target_hit",
                    "severity": "info",
                    "message": f"{symbol}: Target 1 reached! Profit: +{profit_pct:.1f}%",
                    "symbol": symbol,
                })
                logger.info(f"{symbol}: Target 1 hit at {current_price}")
                continue

            if result["is_invalidated"]:
                invalidate_prediction(pred_id, "invalidated_by_engine")
                save_alert({
                    "prediction_id": pred_id,
                    "alert_type": "invalidation",
                    "severity": "critical",
                    "message": f"{symbol}: Trade invalidated. Flags: {', '.join(result['invalidation_flags'][:3])}",
                    "symbol": symbol,
                })
                continue

            if result["requires_attention"]:
                severity = "warning" if result["status"] != "Exit Suggested" else "critical"
                save_alert({
                    "prediction_id": pred_id,
                    "alert_type": "status_change",
                    "severity": severity,
                    "message": f"{symbol}: Status changed to {result['status']}. Action: {result['recommended_action']}",
                    "symbol": symbol,
                })

            save_monitor_log({
                "prediction_id": pred_id,
                "current_price": current_price,
                "current_profit_pct": profit_pct,
                "swing_probability": result["swing_probability"],
                "trade_status": result["status"],
                "invalidation_flags": result["invalidation_flags"],
                "recommended_action": result["recommended_action"],
            })

        with self._lock:
            self._active_trade_status.update(updated_statuses)

        compute_and_save_metrics("all_time")
        compute_and_save_metrics("30d")
        logger.info("Monitor cycle complete")

    def shutdown(self):
        logger.info("Shutting down engine...")
        self._stop_event.set()
        if self._ws_manager:
            self._ws_manager.disconnect()

    def get_regime(self) -> Optional[Dict]:
        with self._lock:
            return self._regime

    def get_recommendations(self) -> List[Dict]:
        with self._lock:
            return list(self._recommendations)

    def get_trade_status(self, pred_id: int) -> Optional[Dict]:
        with self._lock:
            return self._active_trade_status.get(pred_id)

    def get_all_trade_statuses(self) -> Dict[int, Dict]:
        with self._lock:
            return dict(self._active_trade_status)

    def is_analyzing(self) -> bool:
        return self._analyzing

    def get_status_message(self) -> str:
        return self._status_message

    def get_progress(self) -> float:
        return self._progress

    def force_refresh(self):
        if not self._analyzing:
            threading.Thread(target=self.initialize, daemon=True).start()


_engine: Optional[MainEngine] = None


def get_engine() -> MainEngine:
    global _engine
    if _engine is None:
        _engine = MainEngine()
    return _engine
