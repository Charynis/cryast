import time
import ccxt
import pandas as pd
from typing import List, Optional, Dict, Any

from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, EXCHANGE_ID,
    CACHE_TTL_OHLCV, CACHE_TTL_TICKER, QUOTE_CURRENCY
)
from data.data_cache import cache
from utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeClient:
    def __init__(self):
        self._exchange = ccxt.binance({
            "apiKey": BINANCE_API_KEY or None,
            "secret": BINANCE_API_SECRET or None,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        self._rate_limit_delay = 0.25  # seconds between calls

    def _throttle(self):
        time.sleep(self._rate_limit_delay)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            self._throttle()
            raw = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw:
                return None

            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            df.sort_index(inplace=True)

            cache.set(cache_key, df, CACHE_TTL_OHLCV)
            return df

        except ccxt.NetworkError as e:
            logger.warning(f"Network error fetching {symbol} {timeframe}: {e}")
            return None
        except ccxt.ExchangeError as e:
            logger.warning(f"Exchange error fetching {symbol} {timeframe}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {symbol} {timeframe}: {e}")
            return None

    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        cache_key = f"ticker:{symbol}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            self._throttle()
            ticker = self._exchange.fetch_ticker(symbol)
            cache.set(cache_key, ticker, CACHE_TTL_TICKER)
            return ticker
        except Exception as e:
            logger.warning(f"Ticker fetch error for {symbol}: {e}")
            return None

    def fetch_all_tickers(self, symbols: List[str]) -> Dict[str, float]:
        result = {}
        try:
            self._throttle()
            tickers = self._exchange.fetch_tickers(symbols)
            for sym, ticker in tickers.items():
                if ticker.get("last"):
                    result[sym] = float(ticker["last"])
                    cache.set_price(sym, float(ticker["last"]))
        except Exception as e:
            logger.warning(f"Batch ticker fetch error: {e}")
            for sym in symbols:
                t = self.fetch_ticker(sym)
                if t and t.get("last"):
                    result[sym] = float(t["last"])
        return result

    def get_markets(self) -> Dict[str, Any]:
        cache_key = "markets"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            markets = self._exchange.load_markets()
            cache.set(cache_key, markets, 3600)
            return markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            return {}

    def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch perpetual futures funding rate."""
        try:
            futures_exchange = ccxt.binance({
                "apiKey": BINANCE_API_KEY or None,
                "secret": BINANCE_API_SECRET or None,
                "enableRateLimit": True,
                "options": {"defaultType": "future"},
            })
            self._throttle()
            fr = futures_exchange.fetch_funding_rate(symbol)
            return fr.get("fundingRate")
        except Exception:
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        price = cache.get_price(symbol)
        if price:
            return price
        ticker = self.fetch_ticker(symbol)
        if ticker:
            return ticker.get("last")
        return None


_client: Optional[ExchangeClient] = None


def get_exchange_client() -> ExchangeClient:
    global _client
    if _client is None:
        _client = ExchangeClient()
    return _client
