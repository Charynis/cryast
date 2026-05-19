SCHEMA_MIGRATIONS = [
    # Migration 001 - Initial schema
    """
    CREATE TABLE IF NOT EXISTS predictions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol              TEXT NOT NULL,
        created_at          DATETIME NOT NULL,
        entry_price_low     REAL NOT NULL,
        entry_price_high    REAL NOT NULL,
        stop_loss           REAL NOT NULL,
        target_1            REAL NOT NULL,
        target_2            REAL,
        swing_probability   REAL NOT NULL,
        confidence_score    REAL NOT NULL,
        risk_score          REAL NOT NULL,
        regime_at_entry     TEXT NOT NULL,
        rr_ratio            REAL NOT NULL,
        expected_gain_pct   REAL NOT NULL,
        expected_duration_h INTEGER NOT NULL,
        setup_type          TEXT NOT NULL,
        reason_json         TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'active',
        outcome             TEXT,
        actual_entry_price  REAL,
        actual_exit_price   REAL,
        actual_profit_pct   REAL,
        closed_at           DATETIME,
        time_to_outcome_h   REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id       INTEGER NOT NULL REFERENCES predictions(id),
        checked_at          DATETIME NOT NULL,
        current_price       REAL NOT NULL,
        current_profit_pct  REAL NOT NULL,
        swing_probability   REAL NOT NULL,
        trade_status        TEXT NOT NULL,
        momentum_score      REAL,
        volume_score        REAL,
        btc_influence_score REAL,
        invalidation_flags  TEXT,
        recommended_action  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id       INTEGER REFERENCES predictions(id),
        created_at          DATETIME NOT NULL,
        alert_type          TEXT NOT NULL,
        severity            TEXT NOT NULL,
        message             TEXT NOT NULL,
        symbol              TEXT NOT NULL,
        dismissed           INTEGER NOT NULL DEFAULT 0,
        dismissed_at        DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS regime_history (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        detected_at         DATETIME NOT NULL,
        regime              TEXT NOT NULL,
        confidence          REAL NOT NULL,
        btc_price           REAL,
        btc_dominance       REAL,
        fear_greed_index    INTEGER,
        total_market_cap_b  REAL,
        danger_flags        TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS performance_metrics (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        computed_at         DATETIME NOT NULL,
        period              TEXT NOT NULL,
        total_predictions   INTEGER NOT NULL,
        completed_trades    INTEGER NOT NULL,
        wins                INTEGER NOT NULL,
        losses              INTEGER NOT NULL,
        invalidations       INTEGER NOT NULL,
        win_rate            REAL NOT NULL,
        avg_profit_pct      REAL NOT NULL,
        avg_loss_pct        REAL NOT NULL,
        profit_factor       REAL NOT NULL,
        max_drawdown_pct    REAL NOT NULL,
        avg_rr_achieved     REAL NOT NULL,
        avg_duration_h      REAL NOT NULL,
        best_setup_type     TEXT,
        worst_setup_type    TEXT,
        model_accuracy      REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ohlcv_cache (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol      TEXT NOT NULL,
        timeframe   TEXT NOT NULL,
        open_time   DATETIME NOT NULL,
        open        REAL NOT NULL,
        high        REAL NOT NULL,
        low         REAL NOT NULL,
        close       REAL NOT NULL,
        volume      REAL NOT NULL,
        cached_at   DATETIME NOT NULL,
        UNIQUE(symbol, timeframe, open_time)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS coin_universe (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        updated_at      DATETIME NOT NULL,
        symbol          TEXT NOT NULL,
        coingecko_id    TEXT,
        market_cap_rank INTEGER,
        market_cap_usd  REAL,
        volume_24h_usd  REAL,
        is_active       INTEGER NOT NULL DEFAULT 1
    )
    """,
    """CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status)""",
    """CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol)""",
    """CREATE INDEX IF NOT EXISTS idx_monitoring_prediction ON monitoring_log(prediction_id, checked_at)""",
    """CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup ON ohlcv_cache(symbol, timeframe, open_time)""",
    """CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(dismissed, created_at)""",
]
