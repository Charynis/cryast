DARK_THEME_CSS = """
<style>
/* ─── Global ─── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0D1117;
    color: #E6EDF3;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #161B22;
    border-right: 1px solid #30363D;
}
[data-testid="stSidebar"] .stMarkdown { color: #8B949E; }

/* ─── Headers ─── */
h1 { color: #58A6FF !important; font-weight: 700; letter-spacing: -0.5px; }
h2 { color: #79C0FF !important; font-weight: 600; }
h3 { color: #D2A8FF !important; font-weight: 600; }

/* ─── Metric tiles ─── */
[data-testid="metric-container"] {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #58A6FF;
    font-size: 1.6rem;
    font-weight: 700;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #8B949E;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ─── Cards ─── */
.trade-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
}
.trade-card:hover { border-color: #58A6FF; }
.trade-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}
.coin-symbol {
    font-size: 1.4rem;
    font-weight: 700;
    color: #E6EDF3;
}
.confidence-badge {
    background: #1F6FEB;
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* ─── Status badges ─── */
.status-strong   { background: #1A3D2B; color: #3FB950; border: 1px solid #3FB950; }
.status-stable   { background: #1C3048; color: #58A6FF; border: 1px solid #58A6FF; }
.status-weakening{ background: #3D2E0F; color: #E3B341; border: 1px solid #E3B341; }
.status-dangerous{ background: #3D1F00; color: #F0883E; border: 1px solid #F0883E; }
.status-exit     { background: #3D0B0B; color: #F85149; border: 1px solid #F85149; }
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ─── Regime banner ─── */
.regime-bull      { background: #1A3D2B; border-left: 4px solid #3FB950; }
.regime-bear      { background: #3D0B0B; border-left: 4px solid #F85149; }
.regime-sideways  { background: #3D2E0F; border-left: 4px solid #E3B341; }
.regime-dangerous { background: #3D1F00; border-left: 4px solid #F0883E; }
.regime-banner {
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-weight: 600;
}

/* ─── Alert banner ─── */
.alert-critical { background: #3D0B0B; border-left: 4px solid #F85149; }
.alert-warning  { background: #3D2E0F; border-left: 4px solid #E3B341; }
.alert-info     { background: #1C3048; border-left: 4px solid #58A6FF; }
.alert-item {
    padding: 10px 16px;
    border-radius: 6px;
    margin-bottom: 8px;
    font-size: 0.9rem;
}

/* ─── Progress bar ─── */
.stProgress > div > div { background: #58A6FF; }

/* ─── Tables ─── */
.stDataFrame { border: 1px solid #30363D; border-radius: 8px; }
.stDataFrame table { background: #161B22; }
.stDataFrame th { background: #21262D; color: #8B949E; font-size: 0.8rem; }
.stDataFrame td { color: #E6EDF3; }

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] { background: #161B22; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { color: #8B949E; }
.stTabs [aria-selected="true"] { color: #58A6FF !important; }

/* ─── Buttons ─── */
.stButton > button {
    background: #1F6FEB;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
}
.stButton > button:hover { background: #388BFD; }

/* ─── Separator ─── */
hr { border-color: #30363D; }

/* ─── Scrollbar ─── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0D1117; }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
</style>
"""


def status_class(status: str) -> str:
    mapping = {
        "Strong": "status-strong",
        "Stable": "status-stable",
        "Weakening": "status-weakening",
        "Dangerous": "status-dangerous",
        "Exit Suggested": "status-exit",
    }
    return mapping.get(status, "status-stable")


def regime_class(regime: str) -> str:
    return f"regime-{regime}"
