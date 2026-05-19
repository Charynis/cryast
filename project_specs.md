Build a local desktop AI-powered crypto swing trading assistant application that runs entirely on my PC and ONLY works while the application is open. The app should NOT require cloud infrastructure, 24/7 servers, or continuous background execution. When the app is closed, all monitoring and processing should stop completely.

The primary goal of the app is:

1. Minimize losses aggressively
2. Maximize risk-adjusted profit
3. Identify high-probability swing trading opportunities
4. Continuously validate previous predictions while the app is running

The app is NOT an auto-trading bot. It is an intelligent AI-assisted decision-support and market analysis platform for crypto swing trading.

The app should analyze the crypto market and recommend the TOP 3–5 best swing trading opportunities for the current day.

Trading style:

* Swing trading only
* Maximum holding time: 4 days
* Typical holding time: few hours to 4 days
* Main focus: strong momentum continuation trades with controlled risk
* Goal is NOT unrealistic fixed daily returns
* Goal IS consistent profitable opportunities with minimized drawdowns

The app should be designed to run efficiently on:

* Ryzen 7 7435
* RTX 2070 GPU
* 16GB RAM

The system should be optimized for local inference and moderate ML workloads only.

========================
CORE FEATURES
=============

1. DAILY MARKET ANALYSIS ENGINE

When the app opens:

* Fetch latest market data from exchanges
* Analyze overall crypto market conditions
* Analyze BTC trend and market dominance
* Scan top 50–200 crypto coins
* Detect momentum, volatility, liquidity, and trend strength
* Detect dangerous market conditions
* Rank the best swing trading opportunities

The app must generate:

* Top 3–5 crypto trade recommendations
* Confidence score for each recommendation
* Entry zone
* Stop loss
* Take profit targets
* Expected profit percentage
* Risk/reward ratio
* Estimated trade duration
* Trade setup explanation

Example output:

Coin: SOL
Confidence: 84%
Entry Zone: $182–184
Stop Loss: $178
Target 1: $190
Target 2: $197
Expected Gain: 4–8%
Trade Duration: 1–3 days
Risk Level: Medium
Reason:

* strong momentum
* increasing volume
* bullish market structure
* BTC support
* breakout confirmation

========================
2. MARKET REGIME DETECTION
==========================

The AI must first classify the current market condition before recommending trades.

Detect:

* Bullish trending market
* Bearish market
* Sideways/ranging market
* High volatility market
* Dangerous market conditions
* Low liquidity conditions
* Potential manipulation conditions

The app should reduce or avoid recommendations during dangerous conditions.

The app must be capable of outputting:

* “No high-quality opportunities today”
  if market conditions are poor.

========================
3. ACTIVE TRADE MONITORING SYSTEM
=================================

The app must continuously monitor ALL previous trade recommendations WHILE the app is open.

Every 15–30 minutes:

* Recheck active trades
* Reanalyze momentum
* Recheck BTC market influence
* Recheck trend strength
* Recheck volatility changes
* Recheck volume continuation
* Detect setup invalidation

The app must determine whether the original trade thesis is still valid.

Possible statuses:

* Strong
* Stable
* Weakening
* Dangerous
* Exit Suggested

Example:

SOL
Status: Strong
Current Profit: +3.8%
Target Probability: 79%

LINK
Status: Weakening
Momentum slowing
Suggested Action:
Tighten stop loss

ADA
Status: Exit Suggested
Trend invalidated

========================
4. TRADE INVALIDATION ENGINE
============================

This is one of the MOST IMPORTANT systems.

The AI must detect when a previously recommended trade is no longer valid.

Invalidation conditions may include:

* Support breakdown
* Momentum reversal
* BTC weakness
* Volume collapse
* Volatility spike
* Trend structure failure
* Strong bearish divergence
* Whale sell pressure
* Market regime deterioration

When invalidation is detected:

* Generate alert immediately
* Suggest stop loss tightening
* Suggest partial exit or full exit

========================
5. PREDICTION VALIDATION SYSTEM
===============================

The app must track whether predictions succeeded or failed.

For every completed trade recommendation:
Store:

* Entry price
* Exit price
* Target hit or stop loss hit
* Actual profit/loss %
* Time taken
* Confidence score
* Final outcome

Example:

SOL Prediction
✔ Successful
Profit: +5.1%
Duration: 21 hours

LINK Prediction
✘ Invalidated
Loss Avoided: -1.4%

The app must maintain historical prediction performance statistics.

========================
6. PERFORMANCE ANALYTICS DASHBOARD
==================================

Track:

* Win rate
* Average profit
* Average loss
* Maximum drawdown
* Profit factor
* Total predictions
* Prediction accuracy
* Best-performing setup types
* Worst-performing setup types

The dashboard should visually show:

* Successful predictions
* Failed predictions
* Active trades
* Market conditions
* Risk exposure

========================
7. AI / ML REQUIREMENTS
=======================

The app should use PRETRAINED machine learning models initially.

DO NOT build:

* autonomous AGI
* fully self-learning live systems
* high-frequency trading systems
* continuous GPU training systems

Preferred ML models:

* XGBoost (primary)
* LightGBM
* CatBoost
* Optional small LSTM later

Primary prediction objectives:

* Probability of successful swing trade
* Confidence score
* Risk score
* Market regime classification

DO NOT predict exact future prices.

Instead predict:

* probability of target hit before stop loss
* expected risk-adjusted opportunity quality

========================
8. FEATURE ENGINEERING
======================

Use technical and structural market features.

Required indicators:

* RSI
* MACD
* EMA
* SMA
* ATR
* Bollinger Bands
* VWAP
* OBV
* Momentum indicators
* Volume analysis

Required market features:

* Trend strength
* Volatility expansion
* Support/resistance
* Liquidity analysis
* BTC correlation
* Multi-timeframe momentum

Use multi-timeframe analysis:

* 15m
* 1h
* 4h
* 1d

========================
9. DATA SOURCES
===============

Use:

* Binance API
* CCXT

Fetch:

* OHLCV candles
* Volume
* Funding rates
* Open interest
* Top coin market data

========================
10. SOFTWARE STACK
==================

Backend:

* Python

ML:

* XGBoost
* LightGBM
* Scikit-learn
* Pandas
* NumPy

Frontend:
Preferred:

* Streamlit desktop dashboard

Optional:

* PyQt6

Database:

* SQLite initially

Store:

* predictions
* trade history
* performance metrics
* monitoring logs

========================
11. USER INTERFACE REQUIREMENTS
===============================

The app should look modern, clean, and professional.

Main dashboard sections:

1. Market Overview
2. Top Opportunities
3. Active Trade Monitoring
4. Prediction History
5. Performance Analytics
6. AI Confidence Metrics
7. Alerts & Notifications

The dashboard must visually highlight:

* profitable trades
* weakening setups
* dangerous conditions
* exit suggestions

========================
12. SYSTEM BEHAVIOR
===================

The app should ONLY run while open.

When app opens:

* fetch fresh market data
* analyze market
* generate recommendations
* load previous active trades
* start monitoring

When app closes:

* all monitoring stops
* all processing stops
* no background services remain running

========================
13. IMPORTANT STRATEGIC PHILOSOPHY
==================================

The app must prioritize:

* avoiding bad trades
* minimizing drawdowns
* protecting capital
* selecting only high-confidence setups

The app should NOT overtrade.

The AI must be capable of deciding:

* “No high-quality setups currently available.”

The system should prioritize:

* consistency
* survivability
* risk-adjusted profitability

over unrealistic high-return predictions.

========================
14. FUTURE-READY ARCHITECTURE
=============================

Structure the codebase so future upgrades are easy.

Future upgrade possibilities:

* adaptive retraining
* sentiment analysis
* on-chain analytics
* transformer models
* reinforcement learning
* cloud syncing
* mobile alerts

But the INITIAL version should remain lightweight, stable, local-first, and optimized for the current hardware.                                                                                           ======================== 15. FREE APIs & DATA PROVIDERS
Use FREE or free-tier APIs wherever possible.
Primary exchange/data provider:

1. Binance API

* Main source for:
   * OHLCV candles
   * volume
   * ticker data
   * order book data
   * futures funding rates
   * open interest
* Documentation: https://binance-docs.github.io/apidocs/spot/en/
Use CCXT library for simplified exchange integration: 2. CCXT

* Unified crypto exchange API library
* Supports Binance and multiple exchanges
* GitHub: https://github.com/ccxt/ccxt
Market metadata: 3. CoinGecko API

* Coin rankings
* market cap
* trending coins
* circulating supply
* volume rankings
* Free API: https://www.coingecko.com/en/api
Optional additional market data: 4. CryptoCompare API

* Historical market data
* Price aggregation
* Free tier available: https://min-api.cryptocompare.com/
Optional sentiment/news APIs: 5. CryptoPanic API

* Crypto news aggregation
* Market sentiment influence
* https://cryptopanic.com/developers/api/

1. Alternative.me Fear & Greed Index API

* Market sentiment indicator
* Free: https://alternative.me/crypto/fear-and-greed-index/
Optional on-chain analytics (future upgrade): 7. Glassnode

* Whale movement
* Exchange inflows/outflows
* On-chain metrics
* Limited free tier: https://glassnode.com/

1. Dune Analytics

* Blockchain analytics
* Wallet analysis
* On-chain dashboards
* https://dune.com/
======================== 16. REAL-TIME DATA REQUIREMENTS
Use WebSockets wherever possible for live updates while the app is open.
Use Binance WebSocket streams for:

* live price updates
* live volume updates
* order book changes
Fallback to REST APIs when WebSockets unavailable.
======================== 17. API OPTIMIZATION REQUIREMENTS
The app should:

* minimize unnecessary API calls
* cache data locally while app is running
* avoid hitting rate limits
* gracefully handle API failures
* automatically reconnect WebSocket streams
* use asynchronous requests where possible
======================== 18. LOCAL DATA STORAGE
Store locally using SQLite:

* fetched market data
* prediction history
* active trades
* AI confidence history
* performance metrics
Allow reuse of recent 
 data to improve speed when reopening app.