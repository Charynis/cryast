import threading
import time
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL."""

    def __init__(self):
        self._store: dict = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int):
        with self._lock:
            self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def set_price(self, symbol: str, price: float):
        """Dedicated method for live price updates (no TTL expiry - always fresh from WS)."""
        with self._lock:
            self._store[f"price:{symbol}"] = (price, time.time() + 60)

    def get_price(self, symbol: str) -> Optional[float]:
        return self.get(f"price:{symbol}")

    def get_all_prices(self) -> dict:
        with self._lock:
            result = {}
            now = time.time()
            for key, (value, expires_at) in list(self._store.items()):
                if key.startswith("price:") and now <= expires_at:
                    result[key[6:]] = value
            return result


# Global shared cache instance
cache = TTLCache()
