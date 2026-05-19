import json
import threading
import time
import websocket
from typing import List, Callable, Optional

from data.data_cache import cache
from utils.logger import get_logger

logger = get_logger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream"


class WebSocketManager:
    """Manages Binance WebSocket mini-ticker streams for live price updates."""

    def __init__(self):
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._symbols: List[str] = []
        self._running = False
        self._reconnect_delay = 5
        self._on_price_callbacks: List[Callable] = []
        self._stop_event = threading.Event()

    def add_price_callback(self, callback: Callable):
        self._on_price_callbacks.append(callback)

    def connect(self, symbols: List[str]):
        """Connect to WebSocket streams for the given symbols."""
        self._symbols = symbols
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"WebSocket manager started for {len(symbols)} symbols")

    def disconnect(self):
        self._running = False
        self._stop_event.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        logger.info("WebSocket manager stopped")

    def _build_stream_url(self) -> str:
        streams = "/".join(
            f"{sym.replace('/', '').lower()}@miniTicker"
            for sym in self._symbols[:50]  # Binance allows ~50 streams per connection
        )
        return f"{BINANCE_WS_BASE}?streams={streams}"

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "data" in data:
                ticker = data["data"]
                raw_symbol = ticker.get("s", "")  # e.g. "SOLUSDT"
                price = float(ticker.get("c", 0))  # close price
                if raw_symbol and price > 0:
                    symbol = raw_symbol[:-4] + "/USDT" if raw_symbol.endswith("USDT") else raw_symbol
                    cache.set_price(symbol, price)
                    for cb in self._on_price_callbacks:
                        try:
                            cb(symbol, price)
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"WS message parse error: {e}")

    def _on_error(self, ws, error):
        logger.warning(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code}")

    def _on_open(self, ws):
        logger.info("WebSocket connection established")

    def _run_loop(self):
        while self._running and not self._stop_event.is_set():
            try:
                url = self._build_stream_url()
                self._ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"WebSocket run error: {e}")

            if self._running and not self._stop_event.is_set():
                logger.info(f"Reconnecting WebSocket in {self._reconnect_delay}s...")
                time.sleep(self._reconnect_delay)

    def update_symbols(self, symbols: List[str]):
        if set(symbols) == set(self._symbols):
            return
        self._symbols = symbols
        if self._ws:
            self._ws.close()  # triggers reconnect with new symbols
