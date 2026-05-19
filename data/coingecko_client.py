import requests
from typing import List, Dict, Optional

from config import CACHE_TTL_COINGECKO, TOP_COINS_COUNT, MIN_VOLUME_24H_USD, EXCLUDED_SYMBOLS, QUOTE_CURRENCY
from data.data_cache import cache
from utils.logger import get_logger

logger = get_logger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def _get(endpoint: str, params: dict = None) -> Optional[dict]:
    try:
        resp = requests.get(f"{COINGECKO_BASE}{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"CoinGecko error {endpoint}: {e}")
        return None


def get_top_coins(count: int = TOP_COINS_COUNT) -> List[Dict]:
    cache_key = f"cg_top_coins:{count}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = []
    per_page = min(count, 250)
    pages = (count + per_page - 1) // per_page

    for page in range(1, pages + 1):
        data = _get("/coins/markets", {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": False,
        })
        if not data:
            break

        for coin in data:
            symbol = f"{coin['symbol'].upper()}/{QUOTE_CURRENCY}"
            if symbol in EXCLUDED_SYMBOLS:
                continue
            volume = coin.get("total_volume") or 0
            if volume < MIN_VOLUME_24H_USD:
                continue
            result.append({
                "symbol": symbol,
                "coingecko_id": coin["id"],
                "name": coin["name"],
                "market_cap_rank": coin.get("market_cap_rank"),
                "market_cap_usd": coin.get("market_cap"),
                "volume_24h_usd": volume,
                "price_change_24h": coin.get("price_change_percentage_24h", 0),
                "current_price": coin.get("current_price"),
            })

    cache.set(cache_key, result, CACHE_TTL_COINGECKO)
    return result


def get_global_data() -> Optional[Dict]:
    cache_key = "cg_global"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get("/global")
    if data and "data" in data:
        result = data["data"]
        cache.set(cache_key, result, CACHE_TTL_COINGECKO)
        return result
    return None


def get_btc_dominance() -> Optional[float]:
    data = get_global_data()
    if data:
        return data.get("market_cap_percentage", {}).get("btc")
    return None


def get_total_market_cap() -> Optional[float]:
    data = get_global_data()
    if data:
        mcap = data.get("total_market_cap", {}).get("usd")
        return mcap / 1e9 if mcap else None  # in billions
    return None
