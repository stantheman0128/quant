"""
視覺化模組 — Plotly 互動式圖表，輸出 standalone HTML

包含:
1. Equity Curve + Drawdown
2. 價格圖 + 買賣信號標記
3. 月度報酬熱力圖
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .metrics import format_metrics


def _make_equity_chart(result) -> go.Figure:
    """Equity curve + drawdown 疊圖"""
    eq = result.equity_curve
    peak = eq.cummax()
    drawdown = (eq - peak) / peak * 100  # 百分比

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=["Equity Curve", "Drawdown (%)"],
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=eq.index, y=eq.values,
            mode='lines',
            name='Equity',
            line=dict(color='#2196F3', width=1.5),
        ),
        row=1, col=1,
    )

    # Drawdown
    fig.add_trace(
        go.Scatter(
            x=drawdown.index, y=drawdown.values,
            mode='lines',
            fill='tozeroy',
            name='Drawdown',
            line=dict(color='#F44336', width=1),
            fillcolor='rgba(244, 67, 54, 0.3)',
        ),
        row=2, col=1,
    )

    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(l=60, r=30, t=40, b=30),
    )
    fig.update_yaxes(title_text="Capital", row=1, col=1)
    fig.update_yaxes(title_text="DD %", row=2, col=1)

    return fig


def _make_price_signals_chart(result) -> go.Figure:
    """價格圖 + 買賣信號標記"""
    prices = result.prices
    signals = result.signals

    fig = go.Figure()

    # 價格線
    fig.add_trace(
        go.Scatter(
            x=prices.index, y=prices['close'],
            mode='lines',
            name='Close',
            line=dict(color='#607D8B', width=1),
        )
    )

    # 買入信號（signal 從非 1 變成 1）
    sig_diff = signals.diff()
    buy_mask = (sig_diff == 1) | ((sig_diff == 2))  # 0→1 或 -1→1
    sell_mask = (sig_diff == -1) | ((sig_diff == -2))  # 0→-1 或 1→-1

    buy_points = prices.loc[buy_mask, 'close']
    sell_points = prices.loc[sell_mask, 'close']

    if len(buy_points) > 0:
        fig.add_trace(
            go.Scatter(
                x=buy_points.index, y=buy_points.values,
                mode='markers',
                name='Buy',
                marker=dict(symbol='triangle-up', size=8, color='#4CAF50'),
            )
        )

    if len(sell_points) > 0:
        fig.add_trace(
            go.Scatter(
                x=sell_points.index, y=sell_points.values,
                mode='markers',
                name='Sell',
                marker=dict(symbol='triangle-down', size=8, color='#F44336'),
            )
        )

    fig.update_layout(
        title="Price & Signals",
        height=400,
        margin=dict(l=60, r=30, t=40, b=30),
        xaxis_rangeslider_visible=False,
    )

    return fig


def _make_monthly_heatmap(result) -> go.Figure:
    """月度報酬熱力圖"""
    returns = result.returns.copy()
    returns.index = returns.index.tz_localize(None) if returns.index.tz else returns.index

    # 按月聚合報酬
    monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)

    if len(monthly) < 2:
        # 數據太少，跳過
        fig = go.Figure()
        fig.add_annotation(text="數據不足，無法產生月度熱力圖", showarrow=False)
        return fig

    # 整理成 year × month 矩陣
    monthly_df = pd.DataFrame({
        'year': monthly.index.year,
        'month': monthly.index.month,
        'return': monthly.values * 100,  # 百分比
    })
    pivot = monthly_df.pivot_table(index='year', columns='month', values='return')
    pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot.columns)]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[str(y) for y in pivot.index],
        colorscale='RdYlGn',
        zmid=0,
        text=np.round(pivot.values, 1),
        texttemplate="%{text:.1f}%",
        textfont=dict(size=11),
        hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title="Monthly Returns (%)",
        height=250,
        margin=dict(l=60, r=30, t=40, b=30),
    )

    return fig


def generate_report(result, output_path: str | Path) -> None:
    """
    產生完整的 HTML 回測報告。

    包含: 績效摘要表 + equity curve + drawdown + 價格信號圖 + 月度熱力圖
    """
    output_path = Path(output_path)

    # 產生三張圖
    equity_fig = _make_equity_chart(result)
    price_fig = _make_price_signals_chart(result)
    monthly_fig = _make_monthly_heatmap(result)

    # 績效指標 HTML
    metrics_html = format_metrics(result.metrics).replace('\n', '<br>')

    # 組合 HTML
    header = f"{result.symbol} | {result.strategy_name} | {result.freq}"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>回測報告 — {header}</title>
    <style>
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #16213e, #0f3460);
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            color: #e94560;
        }}
        .header p {{
            margin: 5px 0 0;
            color: #a0a0a0;
        }}
        .metrics-box {{
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.8;
            white-space: pre;
        }}
        .chart-container {{
            background: #16213e;
            border-radius: 12px;
            padding: 10px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{header}</h1>
        <p>Vectorized Backtest Report</p>
    </div>
    <div class="metrics-box">{metrics_html}<br>  Total Trades            {result.metrics.get('total_trades', 0):>10.0f}</div>
    <div class="chart-container">{equity_fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>
    <div class="chart-container">{price_fig.to_html(full_html=False, include_plotlyjs=False)}</div>
    <div class="chart-container">{monthly_fig.to_html(full_html=False, include_plotlyjs=False)}</div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')
