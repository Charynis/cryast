import requests
from typing import Optional, Dict

from config import CACHE_TTL_SENTIMENT
from data.data_cache import cache
from utils.logger import get_logger

logger = get_logger(__name__)


def get_fear_greed_index() -> Optional[Dict]:
    cache_key = "fear_greed"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if data and "data" in data and data["data"]:
            entry = data["data"][0]
            result = {
                "value": int(entry["value"]),
                "classification": entry["value_classification"],
            }
            cache.set(cache_key, result, CACHE_TTL_SENTIMENT)
            return result
    except Exception as e:
        logger.warning(f"Fear & Greed API error: {e}")
    return None


def get_fear_greed_value() -> int:
    data = get_fear_greed_index()
    return data["value"] if data else 50  # default neutral
