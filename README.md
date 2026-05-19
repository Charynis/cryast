# Crypto Swing Trading Assistant

A local desktop AI-powered crypto swing trading assistant. Runs entirely on your PC using Streamlit — no cloud infrastructure, no background services, no auto-trading. When you close the app, everything stops.

## What It Does

- Scans the top 100 crypto coins and ranks the **top 3–5 swing trade opportunities** for the day
- Detects the current **market regime** (Bull / Bear / Sideways / Dangerous) before recommending anything
- **Monitors active trades** every 20 minutes while the app is open
- Fires **invalidation alerts** when a trade setup breaks down (support lost, momentum reversal, BTC weakness, etc.)
- Tracks **prediction history** and measures real win rate, profit factor, and model accuracy over time

## Screenshot Overview

| Tab | Description |
|-----|-------------|
| 🌍 Market Overview | BTC price, dominance, Fear & Greed index, market regime |
| 🎯 Top Opportunities | Ranked trade cards with entry zone, stop loss, targets, R:R |
| 📊 Active Trades | Live monitoring status: Strong / Stable / Weakening / Exit Suggested |
| 📋 Trade History | All past predictions with outcomes (hit / stopped / invalidated) |
| 📈 Analytics | Win rate, profit factor, equity curve, confidence calibration |
| 🔔 Alerts | Invalidation and status-change notifications |

## Hardware Requirements

Optimized for:
- CPU: Ryzen 7 7435 (or equivalent)
- GPU: RTX 2070 (ML inference uses CPU; GPU optional for future LSTM upgrade)
- RAM: 16 GB

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| ML | XGBoost, LightGBM, CatBoost |
| Features | pandas-ta (RSI, MACD, EMA, ATR, BB, VWAP, OBV) |
| Data | Binance API via CCXT, CoinGecko, Alternative.me |
| Real-time | Binance WebSocket mini-ticker streams |
| Database | SQLite (WAL mode) |
| Background | Python threading (daemon threads, stops on app close) |

---

## Installation

### Prerequisites

- Python 3.10+
- macOS / Linux / Windows
- Internet connection (for Binance API)

### macOS — XGBoost dependency

XGBoost requires OpenMP on macOS. Install it first:

```bash
brew install libomp
```

### Setup

```bash
# Clone or navigate to the project
cd crypto_assistant

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### API Keys (optional)

Binance public endpoints work without API keys. Keys give higher rate limits.

```bash
cp .env.example .env
# Edit .env and add your keys (optional)
```

---

## Running the App

```bash
# Using the launch script (handles venv automatically)
./run.sh

# Or manually
source .venv/bin/activate
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## First Launch: ML Model Training

On first launch the app detects no trained models and shows a training screen.

Click **Start Training** — the pipeline will:

1. Download ~1,000 hourly candles per coin from Binance for 20 top coins
2. Compute 38+ technical features per candle (RSI, MACD, EMA, ATR, BB, VWAP, OBV, structure, BTC correlation)
3. Build binary swing-trade labels: *did price hit +5% before hitting −2.5% stop?*
4. Train three models:
   - **XGBoost** — swing trade success probability
   - **LightGBM** — risk score
   - **CatBoost** — market regime classifier (Bull / Bear / Sideways / Dangerous)
5. Save models to `models_store/`

**Training time:** ~5–15 minutes depending on internet speed.

Models are saved permanently. Training only runs once unless you delete `models_store/`.

---

## How It Works

### Startup Sequence (every time you open the app)

```
1. Load trained ML models
2. Detect market regime (BTC data + Fear & Greed index)
3. If dangerous → show warning, skip recommendations
4. Fetch top 100 coins from CoinGecko
5. For each coin: fetch 4 timeframes (15m, 1h, 4h, 1d) from Binance
6. Compute features → ML scores → rank by opportunity score
7. Filter: min R:R 1.8, min confidence 55%, min volume $5M/day
8. Generate top 3–5 recommendations with entry/SL/targets
9. Start WebSocket streams for live prices
10. Start background monitor thread (checks every 20 min)
```

### Trade Recommendations

Each recommendation includes:

```
Coin: SOL
Confidence: 84%
Entry Zone: $182–184
Stop Loss: $178        (ATR-based, 1.5× ATR below entry)
Target 1: $190         (2:1 R:R minimum)
Target 2: $197         (3.5:1 R:R)
Expected Gain: 4–8%
Trade Duration: 1–3 days
Risk Level: Medium
Setup: Momentum / Breakout / Pullback / Trend Continuation

Reasons:
  ✓ MACD bullish momentum
  ✓ Price above key EMAs
  ✓ Volume expansion detected
  ✓ Higher highs & higher lows
  ✓ BTC showing strength
```

### Market Regime Detection

The regime classifier runs on BTC data before scanning individual coins.

| Regime | Behavior |
|--------|----------|
| 🟢 Bull | Full scan, normal recommendations |
| 🟡 Sideways | Scan runs, stricter filters |
| 🔴 Bear | Scan runs, higher confidence threshold |
| 🚨 Dangerous | Scan skipped — "No recommendations today" |

Dangerous conditions are triggered by: extreme fear (F&G < 20), BTC dropping >4% in 4h, or 2+ warning flags simultaneously.

### Trade Invalidation Engine

Every 20 minutes the monitor re-evaluates each active trade. It checks:

| Condition | Trigger |
|-----------|---------|
| Support breakdown | Price crosses below last swing low |
| Momentum reversal | 4h RSI < 40 + MACD bearish cross |
| BTC weakness | BTC drops >3% in 4h while coin stagnant |
| Volume collapse | Current volume < 30% of 20-period average |
| Volatility spike | ATR expands to >1.8× 20-period average |
| Trend structure failed | Lower highs + lower lows on 4h chart |

Possible trade statuses:

| Status | Meaning | Action |
|--------|---------|--------|
| **Strong** | Setup holding, momentum intact | Hold |
| **Stable** | On track, no flags | Hold |
| **Weakening** | 1 warning flag | Consider tightening stop loss |
| **Dangerous** | 2+ warning flags | Partial exit |
| **Exit Suggested** | Critical invalidation | Exit |

---

## Project Structure

```
crypto_assistant/
├── app.py                          # Streamlit entry point, all 6 dashboard tabs
├── config.py                       # Central configuration (thresholds, API, paths)
├── requirements.txt
├── run.sh                          # One-click launch script
│
├── core/
│   ├── engine.py                   # Main orchestrator (startup, monitoring, shutdown)
│   ├── regime_detector.py          # Market regime classification
│   ├── market_scanner.py           # Scan top coins, score and rank opportunities
│   └── invalidation_engine.py      # Detect when a trade thesis breaks
│
├── ml/
│   ├── trainer.py                  # Full training pipeline
│   ├── predictor.py                # Model inference (swing prob, risk, regime)
│   ├── label_builder.py            # Build binary labels from historical OHLCV
│   └── model_registry.py           # Save/load models (joblib)
│
├── features/
│   ├── technical_indicators.py     # RSI, MACD, EMA, ATR, BB, VWAP, OBV, StochRSI
│   └── feature_builder.py          # Combine multi-timeframe features into one vector
│
├── data/
│   ├── exchange_client.py          # Binance REST via CCXT (OHLCV, tickers)
│   ├── websocket_manager.py        # Binance WebSocket live price streams
│   ├── coingecko_client.py         # CoinGecko (top coins, market cap, BTC dominance)
│   ├── sentiment_client.py         # Alternative.me Fear & Greed index
│   └── data_cache.py               # Thread-safe in-memory TTL cache
│
├── database/
│   ├── db_manager.py               # SQLite connection (WAL mode), migrations
│   ├── schema.py                   # All CREATE TABLE statements
│   └── repositories/
│       ├── trade_repo.py           # Predictions, monitoring logs CRUD
│       ├── performance_repo.py     # Win rate, profit factor, drawdown metrics
│       └── alert_repo.py           # Alerts and regime history
│
├── monitoring/
│   └── event_bus.py                # Thread-safe queue (background → UI events)
│
├── app/
│   ├── styles.py                   # Dark theme CSS
│   └── components/
│       ├── trade_card.py           # Trade recommendation + active trade cards
│       └── charts.py               # Plotly charts (equity curve, win/loss, calibration)
│
├── models_store/                   # Trained model files (auto-created, gitignored)
├── data_store/                     # SQLite database (auto-created)
└── logs/                           # Rotating log files (auto-created)
```

---

## Configuration

All tunable parameters are in [config.py](config.py):

```python
TOP_COINS_COUNT = 100           # How many coins to scan
MIN_VOLUME_24H_USD = 5_000_000  # Minimum daily volume filter
MIN_RR_RATIO = 1.8              # Minimum risk:reward to recommend a trade
MIN_CONFIDENCE_SCORE = 0.55     # Minimum ML confidence threshold
MONITOR_INTERVAL_MINUTES = 20   # How often to re-check active trades
LABEL_TARGET_PCT = 0.05         # Training label: 5% gain target
LABEL_SL_PCT = 0.025            # Training label: 2.5% stop loss
```

---

## Data Sources

| Source | Used For | Cost |
|--------|----------|------|
| [Binance API](https://binance-docs.github.io/apidocs/spot/en/) | OHLCV candles, live prices, WebSocket | Free |
| [CoinGecko API](https://www.coingecko.com/en/api) | Top coins list, market cap, BTC dominance | Free |
| [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/) | Fear & Greed index | Free |

---

## Troubleshooting

**XGBoost fails on macOS (`libomp` missing)**
```bash
brew install libomp
```

**Streamlit email prompt blocks startup**
```bash
# Add to ~/.streamlit/config.toml
[browser]
gatherUsageStats = false
```

**Binance rate limit errors**
Add API keys to `.env` — authenticated requests have higher limits. The app throttles requests and caches responses to minimize API calls.

**Training takes too long**
Reduce `TRAINING_HISTORY_DAYS` in `config.py` (default: 365). Setting it to 180 roughly halves training time.

---

## Trading Philosophy

This tool is built around **capital preservation first**:

- The AI will output "No high-quality opportunities today" rather than force bad trades
- Every recommendation requires R:R ≥ 1.8 minimum
- Dangerous market conditions suppress all recommendations
- Trade monitoring actively looks for exit signals, not just entry validation
- ML labels are built conservatively: timeout = loss (not "no outcome")

**This is a decision-support tool, not an auto-trading bot.** All trade decisions are yours.

---

## Future Upgrades (architecture is ready)

- Sentiment analysis (CryptoPanic news feed)
- On-chain analytics (Glassnode whale flows)
- LSTM / transformer models for sequence learning
- Adaptive monthly retraining
- Mobile push alerts
- Cloud sync for multi-device access
