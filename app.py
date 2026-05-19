"""
Crypto Swing Trading Assistant
Entry point — run with:  streamlit run app.py
"""
import sys
import atexit
import threading
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app.styles import DARK_THEME_CSS, regime_class, status_class
from app.components.trade_card import render_trade_card, render_active_trade_card
from app.components.charts import (
    equity_curve_chart, win_loss_pie, regime_history_chart,
    setup_type_performance_chart, confidence_calibration_chart,
)
from database.db_manager import run_migrations
from database.repositories.trade_repo import get_active_predictions, get_prediction_history
from database.repositories.performance_repo import (
    get_latest_metrics, get_all_completed_predictions, compute_and_save_metrics
)
from database.repositories.alert_repo import (
    get_active_alerts, get_all_alerts, dismiss_alert, dismiss_all_alerts, save_regime
)
from ml.trainer import models_need_training, train_all_models
from ml.predictor import get_predictor
from core.engine import MainEngine
from utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Swing Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state initialization (runs once per session)
# ─────────────────────────────────────────────
def initialize_session():
    if st.session_state.get("_initialized"):
        return

    logger.info("Initializing application session...")
    run_migrations()

    st.session_state._training_progress = 0.0
    st.session_state._training_message = ""
    st.session_state._training_complete = False
    st.session_state._training_failed = False

    if models_need_training():
        st.session_state._needs_training = True
    else:
        st.session_state._needs_training = False
        get_predictor()

    engine = MainEngine()
    st.session_state.engine = engine

    def shutdown_engine():
        if hasattr(st.session_state, "engine"):
            st.session_state.engine.shutdown()

    atexit.register(shutdown_engine)
    st.session_state._initialized = True


# ─────────────────────────────────────────────
# Training flow
# ─────────────────────────────────────────────
def run_training_ui():
    st.title("📈 Crypto Swing Trading Assistant")
    st.markdown("---")
    st.subheader("🤖 First-Time ML Model Training")
    st.info(
        "No trained models found. The system will now download ~1 year of historical data "
        "from Binance and train the prediction models. This takes **5–20 minutes** depending "
        "on your internet connection. This only happens once."
    )

    if not st.session_state.get("_training_started"):
        if st.button("🚀 Start Training", type="primary"):
            st.session_state._training_started = True
            st.rerun()
        return

    progress_bar = st.progress(st.session_state._training_progress, text=st.session_state._training_message or "Starting...")
    status_placeholder = st.empty()

    if not st.session_state.get("_training_thread_started"):
        def training_callback(msg, pct):
            st.session_state._training_message = msg
            if pct is not None:
                st.session_state._training_progress = pct

        def run_training():
            try:
                success = train_all_models(progress_callback=training_callback)
                st.session_state._training_complete = success
                if success:
                    get_predictor()
                    st.session_state._needs_training = False
            except Exception as e:
                logger.error(f"Training failed: {e}", exc_info=True)
                st.session_state._training_failed = True
                st.session_state._training_message = f"Training failed: {e}"

        t = threading.Thread(target=run_training, daemon=True)
        t.start()
        st.session_state._training_thread_started = True

    progress_bar.progress(
        st.session_state._training_progress,
        text=st.session_state._training_message or "Training in progress..."
    )

    if st.session_state._training_complete:
        st.success("✅ Models trained successfully! Refreshing...")
        st.balloons()
        st.rerun()
    elif st.session_state._training_failed:
        st.error(f"❌ {st.session_state._training_message}")
        st.warning("The app will use heuristic scoring as fallback. You can retry training later.")
        if st.button("Continue without ML models"):
            st.session_state._needs_training = False
            st.rerun()
    else:
        st_autorefresh(interval=2000, key="training_refresh")


# ─────────────────────────────────────────────
# Engine startup flow
# ─────────────────────────────────────────────
def run_analysis_ui():
    engine: MainEngine = st.session_state.engine

    if not st.session_state.get("_analysis_started"):
        st.session_state._analysis_started = True
        threading.Thread(target=engine.initialize, daemon=True).start()

    if engine.is_analyzing():
        st.title("📈 Crypto Swing Trading Assistant")
        st.markdown("---")
        st.subheader("🔍 Analyzing Market...")
        prog = engine.get_progress()
        msg = engine.get_status_message()
        st.progress(prog, text=msg)
        st_autorefresh(interval=1500, key="analysis_refresh")
        return

    render_main_dashboard(engine)


# ─────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────
def render_main_dashboard(engine: MainEngine):
    # Auto-refresh every 30 seconds for live updates
    st_autorefresh(interval=30_000, key="dashboard_refresh")

    regime = engine.get_regime()
    recommendations = engine.get_recommendations()
    active_trades = get_active_predictions()
    alerts = get_active_alerts(limit=10)

    # ─── Sidebar ───
    with st.sidebar:
        st.markdown("## 📈 Swing Assistant")
        st.markdown("---")

        if regime:
            regime_name = regime.get("regime", "unknown").upper()
            icon = regime.get("icon", "⚪")
            conf = regime.get("confidence", 0)
            st.markdown(f"### {icon} Market: {regime_name}")
            st.markdown(f"Confidence: **{conf*100:.0f}%**")

            fg = regime.get("fear_greed_index")
            if fg is not None:
                fg_label = "Extreme Fear" if fg < 25 else "Fear" if fg < 45 else "Neutral" if fg < 55 else "Greed" if fg < 75 else "Extreme Greed"
                fg_color = "#F85149" if fg < 25 else "#E3B341" if fg < 45 else "#8B949E" if fg < 55 else "#3FB950" if fg < 75 else "#00C853"
                st.markdown(f"F&G Index: <span style='color:{fg_color};font-weight:700;'>{fg} ({fg_label})</span>", unsafe_allow_html=True)

            dom = regime.get("btc_dominance")
            if dom:
                st.markdown(f"BTC Dominance: **{dom:.1f}%**")

        st.markdown("---")
        st.markdown(f"**Active Trades:** {len(active_trades)}")
        st.markdown(f"**Recommendations:** {len(recommendations)}")

        if st.button("🔄 Refresh Analysis", use_container_width=True):
            engine.force_refresh()
            st.rerun()

        st.markdown("---")
        metrics_all = get_latest_metrics("all_time")
        if metrics_all:
            st.markdown("### 📊 Quick Stats")
            st.markdown(f"Win Rate: **{metrics_all.get('win_rate', 0)*100:.0f}%**")
            st.markdown(f"Profit Factor: **{metrics_all.get('profit_factor', 0):.2f}**")
            st.markdown(f"Total Trades: **{metrics_all.get('total_predictions', 0)}**")

    # ─── Alert Banner ───
    critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
    if critical_alerts:
        for alert in critical_alerts[:3]:
            st.markdown(f"""
            <div class="alert-item alert-critical">
                🚨 <strong>{alert['symbol']}</strong>: {alert['message']}
            </div>
            """, unsafe_allow_html=True)

    # ─── Main tabs ───
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌍 Market Overview",
        "🎯 Top Opportunities",
        "📊 Active Trades",
        "📋 Trade History",
        "📈 Analytics",
        "🔔 Alerts",
    ])

    with tab1:
        render_market_overview(regime, engine)

    with tab2:
        render_opportunities(recommendations, regime)

    with tab3:
        render_active_trades(active_trades, engine)

    with tab4:
        render_prediction_history()

    with tab5:
        render_analytics()

    with tab6:
        render_alerts(alerts)


# ─────────────────────────────────────────────
# Tab: Market Overview
# ─────────────────────────────────────────────
def render_market_overview(regime, engine):
    st.header("🌍 Market Overview")

    if not regime:
        st.warning("Market data loading...")
        return

    regime_name = regime.get("regime", "unknown")
    color_cls = f"regime-{regime_name}"
    flags = regime.get("danger_flags", [])

    st.markdown(f"""
    <div class="regime-banner {color_cls}">
        {regime.get('icon','⚪')} <strong>Market Regime: {regime_name.upper()}</strong>
        &nbsp;&nbsp;|&nbsp;&nbsp; Confidence: {regime.get('confidence',0)*100:.0f}%
        {'&nbsp;&nbsp;|&nbsp;&nbsp; ⚠ ' + ', '.join(flags[:2]) if flags else ''}
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        btc_price = regime.get("btc_price")
        st.metric("BTC Price", f"${btc_price:,.0f}" if btc_price else "—")
    with col2:
        dom = regime.get("btc_dominance")
        st.metric("BTC Dominance", f"{dom:.1f}%" if dom else "—")
    with col3:
        fg = regime.get("fear_greed_index")
        st.metric("Fear & Greed", str(fg) if fg is not None else "—")
    with col4:
        mcap = regime.get("total_market_cap_b")
        st.metric("Total Market Cap", f"${mcap:.0f}B" if mcap else "—")

    if not regime.get("is_tradeable"):
        st.error("🚨 **DANGEROUS MARKET CONDITIONS** — Trading is not recommended. The system will not generate new recommendations until conditions improve.")

    from database.repositories.alert_repo import get_latest_regime
    import database.db_manager as db
    regime_rows = db.fetchall("SELECT * FROM regime_history ORDER BY detected_at DESC LIMIT 30")
    if regime_rows:
        st.plotly_chart(regime_history_chart([dict(r) for r in regime_rows]), use_container_width=True)


# ─────────────────────────────────────────────
# Tab: Top Opportunities
# ─────────────────────────────────────────────
def render_opportunities(recommendations, regime):
    st.header("🎯 Top Trading Opportunities")

    if not regime or not regime.get("is_tradeable"):
        st.error("🚨 Market conditions are currently dangerous. No trade recommendations.")
        st.markdown("The AI has detected unfavorable conditions. Recommendations will resume when the market stabilizes.")
        return

    if not recommendations:
        st.info("No high-quality opportunities found in the current market scan. The AI prioritizes quality over quantity.")
        return

    st.markdown(f"**{len(recommendations)} high-confidence setups identified** — refreshed {engine_last_refresh()}")
    st.markdown("---")

    for i, rec in enumerate(recommendations):
        render_trade_card(rec, i)


def engine_last_refresh():
    try:
        engine: MainEngine = st.session_state.engine
        last = engine._last_analysis
        if last:
            from datetime import datetime
            delta = datetime.utcnow() - last
            mins = int(delta.total_seconds() / 60)
            return f"{mins}m ago" if mins > 0 else "just now"
    except Exception:
        pass
    return "—"


# ─────────────────────────────────────────────
# Tab: Active Trades
# ─────────────────────────────────────────────
def render_active_trades(active_trades, engine: MainEngine):
    st.header("📊 Active Trade Monitoring")

    if not active_trades:
        st.info("No active trades being monitored. Recommendations appear above once generated.")
        return

    st.markdown(f"Monitoring **{len(active_trades)} active setups** — checked every 20 minutes")

    all_statuses = engine.get_all_trade_statuses()

    requires_attention = []
    normal = []
    for pred in active_trades:
        status_info = all_statuses.get(pred["id"], {})
        if status_info.get("requires_attention"):
            requires_attention.append((pred, status_info))
        else:
            normal.append((pred, status_info))

    if requires_attention:
        st.subheader("⚠ Requires Attention")
        for pred, status_info in requires_attention:
            render_active_trade_card(pred, status_info)

    if normal:
        st.subheader("✓ On Track")
        for pred, status_info in normal:
            render_active_trade_card(pred, status_info)


# ─────────────────────────────────────────────
# Tab: Prediction History
# ─────────────────────────────────────────────
def render_prediction_history():
    st.header("📋 Prediction History")

    history = get_prediction_history(limit=50)
    if not history:
        st.info("No completed predictions yet.")
        return

    import pandas as pd

    display_data = []
    for p in history:
        profit = p.get("actual_profit_pct")
        outcome = p.get("outcome", "—")
        icon = "✅" if outcome == "target_1_hit" else "❌" if outcome == "stop_hit" else "⚠" if outcome == "invalidated" else "—"
        display_data.append({
            "": icon,
            "Symbol": p.get("symbol", "").replace("/USDT", ""),
            "Entry": f"${p.get('entry_price_high', 0):,.4g}",
            "Target": f"${p.get('target_1', 0):,.4g}",
            "SL": f"${p.get('stop_loss', 0):,.4g}",
            "R:R": f"{p.get('rr_ratio', 0):.1f}",
            "Confidence": f"{(p.get('confidence_score', 0) or 0)*100:.0f}%",
            "P&L": f"{'+' if (profit or 0) >= 0 else ''}{profit:.1f}%" if profit is not None else "—",
            "Outcome": outcome.replace("_", " ").title() if outcome else "—",
            "Duration": f"{p.get('time_to_outcome_h', 0):.0f}h" if p.get("time_to_outcome_h") else "—",
            "Date": (p.get("closed_at") or p.get("created_at") or "")[:16],
        })

    df = pd.DataFrame(display_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# Tab: Analytics
# ─────────────────────────────────────────────
def render_analytics():
    st.header("📈 Performance Analytics")

    metrics_all = get_latest_metrics("all_time")
    metrics_30d = get_latest_metrics("30d")
    completed = get_all_completed_predictions()

    if not metrics_all and not completed:
        st.info("No completed trades yet. Performance analytics will appear here once trades are tracked.")
        return

    if not metrics_all and completed:
        metrics_all = compute_and_save_metrics("all_time")

    period_tab, history_tab, calibration_tab = st.tabs(["All Time", "30 Days", "Model Accuracy"])

    def render_metrics_tab(metrics):
        if not metrics:
            st.info("No data for this period.")
            return

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")
        col2.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
        col3.metric("Avg Profit", f"{metrics.get('avg_profit_pct', 0):.1f}%")
        col4.metric("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0):.1f}%")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Total Trades", metrics.get("total_predictions", 0))
        col6.metric("Completed", metrics.get("completed_trades", 0))
        col7.metric("Wins", metrics.get("wins", 0))
        col8.metric("Losses", metrics.get("losses", 0))

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                win_loss_pie(metrics.get("wins", 0), metrics.get("losses", 0), metrics.get("invalidations", 0)),
                use_container_width=True
            )
        with col_b:
            st.plotly_chart(equity_curve_chart(completed), use_container_width=True)

        if metrics.get("best_setup_type"):
            st.markdown(f"**Best setup:** `{metrics['best_setup_type']}`")
        if metrics.get("worst_setup_type"):
            st.markdown(f"**Weakest setup:** `{metrics['worst_setup_type']}`")

    with period_tab:
        render_metrics_tab(metrics_all)

    with history_tab:
        render_metrics_tab(metrics_30d)

    with calibration_tab:
        st.plotly_chart(setup_type_performance_chart(completed), use_container_width=True)
        st.plotly_chart(confidence_calibration_chart(completed), use_container_width=True)


# ─────────────────────────────────────────────
# Tab: Alerts
# ─────────────────────────────────────────────
def render_alerts(active_alerts):
    st.header("🔔 Alerts & Notifications")

    if st.button("Dismiss All Alerts"):
        dismiss_all_alerts()
        st.rerun()

    all_alerts = get_all_alerts(limit=50)
    if not all_alerts:
        st.info("No alerts yet.")
        return

    severity_class = {"critical": "alert-critical", "warning": "alert-warning", "info": "alert-info"}
    severity_icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}

    for alert in all_alerts[:30]:
        sev = alert.get("severity", "info")
        cls = severity_class.get(sev, "alert-info")
        icon = severity_icon.get(sev, "ℹ️")
        dismissed = alert.get("dismissed", 0)
        dim = "opacity: 0.5;" if dismissed else ""

        col_msg, col_btn = st.columns([8, 1])
        with col_msg:
            st.markdown(f"""
            <div class="alert-item {cls}" style="{dim}">
                {icon} <strong>{alert['symbol']}</strong>: {alert['message']}
                <span style="color:#8B949E; font-size:0.75rem; margin-left:8px;">
                    {(alert.get('created_at') or '')[:16]}
                </span>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if not dismissed:
                if st.button("✕", key=f"dismiss_{alert['id']}"):
                    dismiss_alert(alert["id"])
                    st.rerun()


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
initialize_session()

if st.session_state.get("_needs_training"):
    run_training_ui()
else:
    run_analysis_ui()
