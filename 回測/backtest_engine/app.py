"""
回測終端 — Trading Terminal Style UI

啟動: cd 回測/ && python -m streamlit run backtest_engine/app.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from backtest_engine.data_loader import (
    load_and_resample,
    list_available_symbols,
    find_data_file,
)
from backtest_engine.engine import run_backtest
from backtest_engine.strategy import (
    BuyAndHold,
    SMACrossover,
    MACDStrategy,
    BollingerBands,
)

# ─── Config ────────────────────────────────────

st.set_page_config(
    page_title="Backtest Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).parent.parent
CACHE_DIR = DATA_DIR / ".ohlcv_cache"

# ─── Design System ─────────────────────────────

# Colors
C = {
    'bg':       '#0a0e17',
    'surface':  '#111827',
    'surface2': '#1a2234',
    'border':   '#1e293b',
    'text':     '#e2e8f0',
    'muted':    '#64748b',
    'green':    '#10b981',
    'red':      '#ef4444',
    'blue':     '#3b82f6',
    'amber':    '#f59e0b',
    'cyan':     '#06b6d4',
    'purple':   '#8b5cf6',
}

st.markdown(f"""<style>
/* ── Reset Streamlit chrome ── */
.stApp {{ background: {C['bg']}; }}
header[data-testid="stHeader"] {{ display: none; }}
div[data-testid="stSidebarCollapsedControl"] {{ display: none; }}
.block-container {{ padding: 0.8rem 1.2rem 0 1.2rem; max-width: 100%; }}

/* ── Typography ── */
.stApp, .stApp * {{ color: {C['text']}; }}

/* ── Top bar ── */
.topbar {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px;
    background: {C['surface']};
    border-bottom: 1px solid {C['border']};
    border-radius: 6px;
    margin-bottom: 8px;
}}
.topbar .logo {{
    font-size: 15px; font-weight: 700; letter-spacing: 1px;
    color: {C['cyan']};
    white-space: nowrap;
}}
.topbar .sep {{ color: {C['border']}; margin: 0 4px; }}

/* ── Metric strip ── */
.metric-strip {{
    display: flex; gap: 2px; margin: 6px 0 8px 0;
    flex-wrap: wrap;
}}
.metric-card {{
    flex: 1 1 0;
    min-width: 120px;
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 10px 14px;
}}
.metric-card .label {{
    font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.8px;
    color: {C['muted']};
    margin-bottom: 2px;
}}
.metric-card .value {{
    font-size: 20px; font-weight: 700;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    letter-spacing: -0.5px;
}}
.metric-card .value.pos {{ color: {C['green']}; }}
.metric-card .value.neg {{ color: {C['red']}; }}
.metric-card .value.neu {{ color: {C['text']}; }}

/* ── Chart panel ── */
.chart-panel {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 4px;
    margin-bottom: 6px;
}}
.chart-panel .panel-header {{
    font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.8px;
    color: {C['muted']};
    padding: 8px 12px 0 12px;
}}

/* ── Control row ── */
.ctrl-row {{
    display: flex; align-items: flex-end; gap: 8px;
    padding: 8px 16px;
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    margin-bottom: 6px;
    flex-wrap: wrap;
}}
.ctrl-group {{
    display: flex; flex-direction: column; gap: 2px;
}}
.ctrl-group .ctrl-label {{
    font-size: 9px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    color: {C['muted']};
}}

/* ── Secondary metrics table ── */
.metrics-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
}}
.metrics-table td {{
    padding: 6px 12px;
    border-bottom: 1px solid {C['border']};
}}
.metrics-table td:first-child {{
    color: {C['muted']};
    font-size: 11px;
    width: 45%;
}}
.metrics-table td:last-child {{
    text-align: right; font-weight: 600;
}}

/* ── Streamlit widget overrides ── */
div[data-testid="stSelectbox"] > div > div {{
    background: {C['surface2']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
}}
div[data-testid="stNumberInput"] > div > div > input {{
    background: {C['surface2']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
}}
button[kind="primary"] {{
    background: {C['cyan']} !important;
    color: {C['bg']} !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 4px !important;
}}
button[kind="primary"]:hover {{
    background: #22d3ee !important;
}}
div[data-testid="stSlider"] > div > div > div {{
    color: {C['cyan']} !important;
}}

/* ── Status bar ── */
.status-bar {{
    display: flex; justify-content: space-between;
    padding: 6px 12px;
    font-size: 10px; color: {C['muted']};
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    border-top: 1px solid {C['border']};
    background: {C['surface']};
    border-radius: 0 0 6px 6px;
}}

/* hide default streamlit metric styling */
div[data-testid="stMetric"] {{ display: none; }}
/* hide decoration */
div[data-testid="stDecoration"] {{ display: none; }}
</style>""", unsafe_allow_html=True)


# ─── Data ──────────────────────────────────────

symbols_map = list_available_symbols(DATA_DIR)
all_symbols = sorted(symbols_map.keys())

CATEGORIES = {
    "All":         all_symbols,
    "FX Major":    [s for s in ['EURUSD','USDJPY','GBPUSD','AUDUSD','USDCHF','USDCAD','NZDUSD'] if s in symbols_map],
    "Commodities": [s for s in ['XAUUSD','XAGUSD','USOIL','UKOIL','NATGAS'] if s in symbols_map],
    "Indices":     [s for s in ['US500','US100','US30','DE40','JP225','HK50','CN50','UK100'] if s in symbols_map],
    "FX Cross":    [s for s in all_symbols if s not in ['EURUSD','USDJPY','GBPUSD','AUDUSD','USDCHF','USDCAD','NZDUSD',
                    'XAUUSD','XAGUSD','USOIL','UKOIL','NATGAS','US500','US100','US30','DE40','JP225','HK50','CN50','UK100']],
}

FREQ_OPTIONS = ['1min', '5min', '15min', '1h', '4h', '1D']
STRATEGY_OPTIONS = ['Buy & Hold', 'SMA Crossover', 'MACD', 'Bollinger Bands']


@st.cache_data(show_spinner=False)
def load_data(symbol: str, year: str, freq: str) -> pd.DataFrame:
    path = find_data_file(DATA_DIR, symbol, year)
    return load_and_resample(path, freq, cache_dir=CACHE_DIR)


# ─── Top Bar ───────────────────────────────────

st.markdown(
    '<div class="topbar">'
    '<span class="logo">BACKTEST TERMINAL</span>'
    '<span class="sep">|</span>'
    '<span style="font-size:12px;color:#94a3b8;">Vectorized Engine — Tick-Level Data</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ─── Control Row ───────────────────────────────

c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1, 1.5, 2])

with c1:
    cat = st.selectbox("Asset Class", list(CATEGORIES.keys()), index=0, label_visibility="collapsed")
    symbol = st.selectbox("Symbol", CATEGORIES[cat], index=0, label_visibility="collapsed")

with c2:
    available_years = symbols_map.get(symbol, ['24'])
    year = st.selectbox("Year", available_years, format_func=lambda y: f"20{y}", label_visibility="collapsed")
    freq = st.selectbox("Timeframe", FREQ_OPTIONS, index=3, label_visibility="collapsed")

with c3:
    strat_name = st.selectbox("Strategy", STRATEGY_OPTIONS, index=2, label_visibility="collapsed")
    cost_bp = st.number_input("Cost (bp)", value=0.0, min_value=0.0, max_value=20.0, step=0.5, label_visibility="collapsed")
    commission = cost_bp / 10000

with c4:
    if strat_name == 'SMA Crossover':
        p1, p2 = st.columns(2)
        sma_fast = p1.number_input("Fast", value=20, min_value=2, max_value=500, key="sma_f")
        sma_slow = p2.number_input("Slow", value=50, min_value=2, max_value=500, key="sma_s")
        strategy = SMACrossover(fast=sma_fast, slow=sma_slow)
    elif strat_name == 'MACD':
        p1, p2, p3 = st.columns(3)
        mf = p1.number_input("F", value=12, min_value=2, max_value=200, key="m_f")
        ms = p2.number_input("S", value=26, min_value=2, max_value=200, key="m_s")
        mg = p3.number_input("Sig", value=9, min_value=2, max_value=100, key="m_g")
        strategy = MACDStrategy(fast=mf, slow=ms, signal_period=mg)
    elif strat_name == 'Bollinger Bands':
        p1, p2 = st.columns(2)
        bbp = p1.number_input("Period", value=20, min_value=2, max_value=500, key="bb_p")
        bbs = p2.number_input("Std", value=2.0, min_value=0.5, max_value=5.0, step=0.1, key="bb_s")
        strategy = BollingerBands(period=bbp, num_std=bbs)
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        strategy = BuyAndHold()

with c5:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("RUN BACKTEST", type="primary", use_container_width=True)


# ─── Execute ───────────────────────────────────

if run or 'result' not in st.session_state:
    t0 = time.perf_counter()
    prices = load_data(symbol, year, freq)
    t_load = time.perf_counter() - t0

    t1 = time.perf_counter()
    result = run_backtest(prices=prices, strategy=strategy, symbol=symbol, freq=freq, commission=commission)
    t_bt = time.perf_counter() - t1

    st.session_state.update(result=result, t_load=t_load, t_bt=t_bt)

result = st.session_state.get('result')
if not result:
    st.stop()

m = result.metrics
t_load = st.session_state.get('t_load', 0)
t_bt = st.session_state.get('t_bt', 0)


# ─── Metric Strip ─────────────────────────────

def _mc(label: str, value: str, sentiment: str = 'neu') -> str:
    return (
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value {sentiment}">{value}</div>'
        f'</div>'
    )

ar_s = 'pos' if m['annualized_return'] >= 0 else 'neg'
mdd_s = 'neg' if m['max_drawdown'] < -0.05 else ('pos' if m['max_drawdown'] > -0.02 else 'neu')
sh_s = 'pos' if m['sharpe_ratio'] > 1 else ('neg' if m['sharpe_ratio'] < 0 else 'neu')
so_s = 'pos' if m['sortino_ratio'] > 1.5 else ('neg' if m['sortino_ratio'] < 0 else 'neu')
wr_s = 'pos' if m['win_rate'] > 0.55 else ('neg' if m['win_rate'] < 0.45 else 'neu')

strip = '<div class="metric-strip">'
strip += _mc('Annual Return', f"{m['annualized_return']:+.2%}", ar_s)
strip += _mc('Max Drawdown', f"{m['max_drawdown']:+.2%}", mdd_s)
strip += _mc('Sharpe Ratio', f"{m['sharpe_ratio']:.2f}", sh_s)
strip += _mc('Sortino Ratio', f"{m['sortino_ratio']:.2f}", so_s)
strip += _mc('Win Rate', f"{m['win_rate']:.1%}", wr_s)
strip += _mc('Calmar', f"{m['calmar_ratio']:.2f}", 'pos' if m['calmar_ratio'] > 1 else 'neu')
strip += _mc('Profit Factor', f"{m['profit_factor']:.2f}", 'pos' if m['profit_factor'] > 1.5 else 'neu')
strip += _mc('Trades', f"{m.get('total_trades', 0):.0f}", 'neu')
strip += '</div>'
st.markdown(strip, unsafe_allow_html=True)


# ─── Charts ────────────────────────────────────

# Plotly template
_LAYOUT = dict(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor=C['surface'],
    font=dict(family="'SF Mono','Cascadia Code','Consolas',monospace", size=11, color=C['muted']),
    margin=dict(l=55, r=12, t=8, b=28),
    xaxis=dict(gridcolor=C['border'], zeroline=False),
    yaxis=dict(gridcolor=C['border'], zeroline=False),
    hoverlabel=dict(bgcolor=C['surface2'], font_size=11),
)


def chart_price(result) -> go.Figure:
    """Main price chart with candlesticks, signals, and volume proxy."""
    p = result.prices
    s = result.signals

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.65, 0.15, 0.20],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=p.index, open=p['open'], high=p['high'], low=p['low'], close=p['close'],
        name='', showlegend=False,
        increasing=dict(line=dict(color=C['green'], width=1), fillcolor='rgba(16,185,129,0.4)'),
        decreasing=dict(line=dict(color=C['red'], width=1), fillcolor='rgba(239,68,68,0.4)'),
    ), row=1, col=1)

    # Buy/sell markers
    sd = s.diff()
    buys = p.loc[sd > 0, 'low']
    sells = p.loc[sd < 0, 'high']

    if len(buys) > 0:
        fig.add_trace(go.Scatter(
            x=buys.index, y=buys.values * 0.9985,
            mode='markers', name='Long',
            marker=dict(symbol='triangle-up', size=7, color=C['green'],
                        line=dict(width=0)),
            hovertemplate='LONG @ %{y:.2f}<extra></extra>',
        ), row=1, col=1)

    if len(sells) > 0:
        fig.add_trace(go.Scatter(
            x=sells.index, y=sells.values * 1.0015,
            mode='markers', name='Short',
            marker=dict(symbol='triangle-down', size=7, color=C['red'],
                        line=dict(width=0)),
            hovertemplate='SHORT @ %{y:.2f}<extra></extra>',
        ), row=1, col=1)

    # Tick volume bar (proxy)
    if 'tick_count' in p.columns:
        colors = [C['green'] if p['close'].iloc[i] >= p['open'].iloc[i] else C['red']
                  for i in range(len(p))]
        fig.add_trace(go.Bar(
            x=p.index, y=p['tick_count'], name='Ticks',
            marker_color=colors, opacity=0.35, showlegend=False,
        ), row=2, col=1)

    # Equity overlay
    eq = result.equity_curve
    fig.add_trace(go.Scatter(
        x=eq.index, y=eq.values,
        mode='lines', name='Equity',
        line=dict(color=C['cyan'], width=1.5),
    ), row=3, col=1)

    # Drawdown fill
    peak = eq.cummax()
    dd_pct = (eq - peak) / peak * 100
    fig.add_trace(go.Scatter(
        x=dd_pct.index, y=dd_pct.values,
        mode='lines', name='Drawdown',
        line=dict(color=C['red'], width=0.8),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.15)',
        showlegend=False,
        yaxis='y4',
    ), row=3, col=1)

    fig.update_layout(
        **_LAYOUT,
        height=580,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.01, xanchor='left', x=0,
            font=dict(size=10), bgcolor='rgba(0,0,0,0)',
        ),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text='', row=1, col=1, gridcolor=C['border'])
    fig.update_yaxes(title_text='', row=2, col=1, gridcolor=C['border'], showticklabels=False)
    fig.update_yaxes(title_text='', row=3, col=1, gridcolor=C['border'])
    for i in range(1, 4):
        fig.update_xaxes(gridcolor=C['border'], row=i, col=1)

    return fig


def chart_returns_distribution(result) -> go.Figure:
    """Returns distribution histogram."""
    rets = result.returns.values
    rets = rets[rets != 0]  # skip flat periods

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=rets * 100,
        nbinsx=80,
        marker_color=C['blue'],
        opacity=0.7,
        name='Returns',
        hovertemplate='%{x:.2f}%: %{y} bars<extra></extra>',
    ))

    # VaR lines
    var_95 = np.percentile(rets, 5) * 100
    var_99 = np.percentile(rets, 1) * 100
    for val, label, color in [(var_95, 'VaR 95%', C['amber']), (var_99, 'VaR 99%', C['red'])]:
        fig.add_vline(x=val, line=dict(color=color, width=1, dash='dash'),
                      annotation=dict(text=f'{label}: {val:.2f}%', font=dict(size=9, color=color)))

    fig.update_layout(**_LAYOUT, height=260, showlegend=False,
                      xaxis_title='Return %', yaxis_title='Count')
    return fig


def chart_monthly_heatmap(result) -> go.Figure | None:
    """Monthly returns heatmap."""
    rets = result.returns.copy()
    rets.index = rets.index.tz_localize(None) if rets.index.tz else rets.index
    monthly = rets.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    if len(monthly) < 2:
        return None

    mdf = pd.DataFrame({'year': monthly.index.year, 'month': monthly.index.month, 'ret': monthly.values * 100})
    pivot = mdf.pivot_table(index='year', columns='month', values='ret')
    names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    pivot.columns = [names[c-1] for c in pivot.columns]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=[str(y) for y in pivot.index],
        colorscale=[[0,'#7f1d1d'],[0.35,'#991b1b'],[0.45,'#1e293b'],[0.55,'#1e293b'],[0.65,'#065f46'],[1,'#064e3b']],
        zmid=0,
        text=np.round(pivot.values, 1), texttemplate='%{text:+.1f}',
        textfont=dict(size=11, family="'SF Mono','Consolas',monospace"),
        hovertemplate='%{y} %{x}: %{z:+.2f}%<extra></extra>',
        colorbar=dict(title='%', len=0.8),
    ))
    fig.update_layout(**_LAYOUT, height=180)
    return fig


def chart_cumulative_comparison(result) -> go.Figure:
    """Strategy vs buy-and-hold cumulative comparison."""
    bh_rets = result.prices['close'].pct_change().fillna(0)
    bh_cum = (1 + bh_rets).cumprod()
    strat_cum = result.equity_curve / result.equity_curve.iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=strat_cum.index, y=(strat_cum - 1) * 100,
        mode='lines', name=result.strategy_name,
        line=dict(color=C['cyan'], width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=bh_cum.index, y=(bh_cum - 1) * 100,
        mode='lines', name='Buy & Hold',
        line=dict(color=C['muted'], width=1, dash='dot'),
    ))
    fig.add_hline(y=0, line=dict(color=C['border'], width=0.5))

    fig.update_layout(
        **_LAYOUT, height=260,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, font=dict(size=10), bgcolor='rgba(0,0,0,0)'),
        yaxis_title='Return %',
    )
    return fig


# ─── Layout ────────────────────────────────────

# Main chart
st.markdown('<div class="chart-panel"><div class="panel-header">Price Action & Signals</div>', unsafe_allow_html=True)
st.plotly_chart(chart_price(result), width='stretch')
st.markdown('</div>', unsafe_allow_html=True)

# Bottom row: 3 panels
left, mid, right = st.columns([1, 1, 1])

with left:
    st.markdown('<div class="chart-panel"><div class="panel-header">Strategy vs Buy & Hold</div>', unsafe_allow_html=True)
    st.plotly_chart(chart_cumulative_comparison(result), width='stretch')
    st.markdown('</div>', unsafe_allow_html=True)

with mid:
    st.markdown('<div class="chart-panel"><div class="panel-header">Returns Distribution</div>', unsafe_allow_html=True)
    st.plotly_chart(chart_returns_distribution(result), width='stretch')
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    hm = chart_monthly_heatmap(result)
    if hm:
        st.markdown('<div class="chart-panel"><div class="panel-header">Monthly Returns</div>', unsafe_allow_html=True)
        st.plotly_chart(hm, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Extended metrics table
        st.markdown('<div class="chart-panel"><div class="panel-header">Extended Metrics</div>', unsafe_allow_html=True)
        table = '<table class="metrics-table">'
        rows = [
            ('Total Return', f"{m['total_return']:+.2%}"),
            ('Ann. Volatility', f"{m['annualized_volatility']:.2%}"),
            ('Calmar Ratio', f"{m['calmar_ratio']:.2f}"),
            ('Profit Factor', f"{m['profit_factor']:.2f}"),
            ('Max Consec. Losses', f"{m['max_consecutive_losses']:.0f}"),
            ('Total Bars', f"{m['total_periods']:.0f}"),
        ]
        for label, val in rows:
            table += f'<tr><td>{label}</td><td>{val}</td></tr>'
        table += '</table>'
        st.markdown(table, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ─── Status Bar ────────────────────────────────

st.markdown(
    f'<div class="status-bar">'
    f'<span>{result.symbol} · {result.strategy_name} · {result.freq} · 20{year}</span>'
    f'<span>{len(result.prices):,} bars · load {t_load:.2f}s · backtest {t_bt*1000:.0f}ms</span>'
    f'</div>',
    unsafe_allow_html=True,
)
