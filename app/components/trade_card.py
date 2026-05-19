import streamlit as st
from typing import Dict

from app.styles import status_class


def render_trade_card(rec: Dict, index: int = 0):
    """Render a trade recommendation card."""
    symbol = rec.get("symbol", "").replace("/USDT", "")
    confidence = rec.get("confidence_score", 0)
    swing_prob = rec.get("swing_probability", 0)
    risk_score = rec.get("risk_score", 0)

    entry_low = rec.get("entry_price_low", 0)
    entry_high = rec.get("entry_price_high", 0)
    stop_loss = rec.get("stop_loss", 0)
    target_1 = rec.get("target_1", 0)
    target_2 = rec.get("target_2")
    rr = rec.get("rr_ratio", 0)
    gain = rec.get("expected_gain_pct", 0)
    duration = rec.get("expected_duration_h", 24)
    setup_type = rec.get("setup_type", "momentum").replace("_", " ").title()
    reasons = rec.get("reasons", [])

    risk_label = "Low" if risk_score < 0.35 else ("Medium" if risk_score < 0.65 else "High")
    risk_color = "#3FB950" if risk_score < 0.35 else ("#E3B341" if risk_score < 0.65 else "#F85149")

    duration_str = f"{duration}h" if duration < 24 else f"{duration//24}d {duration%24}h"

    st.markdown(f"""
    <div class="trade-card">
        <div class="trade-card-header">
            <span class="coin-symbol">#{index+1} {symbol}</span>
            <span class="confidence-badge">Confidence {confidence*100:.0f}%</span>
        </div>
        <div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
            <span style="background:#21262D; color:#8B949E; padding:3px 10px; border-radius:12px; font-size:0.8rem;">
                📊 {setup_type}
            </span>
            <span style="background:#21262D; color:{risk_color}; padding:3px 10px; border-radius:12px; font-size:0.8rem;">
                ⚡ Risk: {risk_label}
            </span>
            <span style="background:#21262D; color:#8B949E; padding:3px 10px; border-radius:12px; font-size:0.8rem;">
                ⏱ {duration_str}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns([1, 1, 1, 1, 1])
    with cols[0]:
        st.metric("Entry Zone", f"${entry_low:,.4g}–${entry_high:,.4g}")
    with cols[1]:
        st.metric("Stop Loss", f"${stop_loss:,.4g}", delta=f"{(stop_loss/entry_high-1)*100:.1f}%", delta_color="inverse")
    with cols[2]:
        st.metric("Target 1", f"${target_1:,.4g}", delta=f"+{gain:.1f}%")
    with cols[3]:
        if target_2:
            t2_gain = (target_2 - entry_high) / entry_high * 100
            st.metric("Target 2", f"${target_2:,.4g}", delta=f"+{t2_gain:.1f}%")
        else:
            st.metric("Target 2", "—")
    with cols[4]:
        st.metric("R:R Ratio", f"{rr:.1f}:1")

    col_prob, col_reasons = st.columns([1, 2])
    with col_prob:
        st.markdown("**Hit Probability**")
        st.progress(swing_prob, text=f"{swing_prob*100:.0f}%")
    with col_reasons:
        st.markdown("**Setup Thesis**")
        for r in reasons[:4]:
            st.markdown(f"✓ {r}")

    st.markdown("---")


def render_active_trade_card(pred: Dict, status_info: Dict):
    """Render an active trade monitoring card."""
    symbol = pred.get("symbol", "").replace("/USDT", "")
    status = status_info.get("status", "Stable")
    current_price = status_info.get("current_price", 0)
    profit_pct = status_info.get("current_profit_pct", 0)
    swing_prob = status_info.get("swing_probability", 0.5)
    action = status_info.get("recommended_action", "hold").replace("_", " ").title()
    flags = status_info.get("invalidation_flags", [])

    profit_color = "#3FB950" if profit_pct >= 0 else "#F85149"
    profit_sign = "+" if profit_pct >= 0 else ""

    scss = status_class(status)

    st.markdown(f"""
    <div class="trade-card">
        <div class="trade-card-header">
            <span class="coin-symbol">{symbol}</span>
            <span class="status-badge {scss}">{status}</span>
        </div>
        <div style="display:flex; gap:16px; align-items:center; margin-bottom:12px;">
            <span style="font-size:1.3rem; font-weight:700; color:{profit_color};">
                {profit_sign}{profit_pct:.2f}%
            </span>
            <span style="color:#8B949E;">@ ${current_price:,.4g}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Target 1", f"${status_info.get('target_1', 0):,.4g}")
    with c2:
        st.metric("Stop Loss", f"${status_info.get('stop_loss', 0):,.4g}")
    with c3:
        st.progress(swing_prob, text=f"Hit prob: {swing_prob*100:.0f}%")

    if flags:
        st.markdown(f"**⚠ Flags:** {', '.join(flags[:3])}")

    st.markdown(f"**Suggested Action:** `{action}`")
    st.markdown("---")
