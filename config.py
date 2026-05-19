import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).parent

# Database
DB_PATH = BASE_DIR / "data_store" / "trading_assistant.db"
MODELS_DIR = BASE_DIR / "models_store"
LOGS_DIR = BASE_DIR / "logs"

# Exchange
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
EXCHANGE_ID = "binance"
QUOTE_CURRENCY = "USDT"

# Scanning
TOP_COINS_COUNT = 100
MIN_VOLUME_24H_USD = 5_000_000
MIN_MARKET_CAP_USD = 50_000_000
EXCLUDED_SYMBOLS = {"USDT/USDT", "BUSD/USDT", "USDC/USDT", "TUSD/USDT", "DAI/USDT"}

# Trading parameters
MIN_RR_RATIO = 1.8
TARGET_PCT_CONSERVATIVE = 0.04
TARGET_PCT_NORMAL = 0.06
STOP_LOSS_ATR_MULTIPLIER = 1.5
TARGET_ATR_MULTIPLIER = 3.0
MAX_TRADE_DURATION_HOURS = 96  # 4 days
MIN_CONFIDENCE_SCORE = 0.55

# Timeframes
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
PRIMARY_TIMEFRAME = "1h"
CANDLES_PER_TIMEFRAME = {
    "15m": 300,
    "1h": 200,
    "4h": 120,
    "1d": 60,
}

# Monitoring
MONITOR_INTERVAL_MINUTES = 20
WEBSOCKET_RECONNECT_DELAY = 5

# ML Training
TRAINING_HISTORY_DAYS = 365
LABEL_TARGET_PCT = 0.05
LABEL_SL_PCT = 0.025
LABEL_WINDOW_1H = 96  # 4 days in 1h candles
MIN_AUC_THRESHOLD = 0.55
TOP_RECOMMENDATIONS = 5

# Cache TTL (seconds)
CACHE_TTL_TICKER = 30
CACHE_TTL_OHLCV = 300
CACHE_TTL_COINGECKO = 900
CACHE_TTL_SENTIMENT = 1800

# Regime thresholds
DANGER_FEAR_GREED_MAX = 20   # extreme fear
DANGER_BTC_DROP_4H = 0.04   # 4% drop in 4h = danger
SIDEWAYS_ATR_RATIO = 0.5    # low ATR relative to historical = sideways

# Invalidation thresholds
INVALIDATION_SL_BREACH_FACTOR = 0.995  # price within 0.5% of stop loss = danger
INVALIDATION_VOLUME_COLLAPSE_RATIO = 0.30
INVALIDATION_BTC_DROP_THRESHOLD = 0.03
