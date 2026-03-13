#!/usr/bin/env python3
"""
Generate an interactive Plotly equity curve from Freqtrade backtest results.

Accepts both raw .json and .zip backtest result files. Opens the chart in the
default browser as a self-contained HTML file saved alongside the input.

Usage::

    python scripts/plot_equity_plotly.py user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.zip
    python scripts/plot_equity_plotly.py user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.json
"""

import json
import sys
import webbrowser
import zipfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_backtest_json(path: Path) -> dict:
    """Load backtest result JSON from a .zip or .json file.

    :param path: Path to the backtest result file (.zip or .json).
    :return: Parsed JSON dict.
    """
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            json_name = next(n for n in z.namelist() if n.endswith(".json") and "config" not in n and "IchiV2" not in n and "_market" not in n)
            with z.open(json_name) as f:
                return json.load(f)
    with open(path) as f:
        return json.load(f)


def build_equity_chart(result_path: Path) -> Path:
    """Build an interactive Plotly equity curve HTML file.

    :param result_path: Path to backtest result (.zip or .json).
    :return: Path to the generated HTML file.
    """
    data = load_backtest_json(result_path)

    # Support both single-strategy and multi-strategy formats
    if "strategy" in data:
        strategy_name, s = next(iter(data["strategy"].items()))
    else:
        strategy_name = data.get("strategy_name", "Strategy")
        s = data

    trades = pd.DataFrame(s["trades"])
    if trades.empty:
        raise ValueError("No trades found in backtest result.")

    trades["close_date"] = pd.to_datetime(trades["close_date"], utc=True)
    trades = trades[trades["is_open"] == False].sort_values("close_date")

    starting_balance = s["starting_balance"]
    trades["equity"] = starting_balance + trades["profit_abs"].cumsum()
    trades["drawdown_pct"] = (trades["equity"] / trades["equity"].cummax() - 1) * 100

    trades["close_day"] = trades["close_date"].dt.floor("D")
    daily = trades.groupby("close_day")["profit_abs"].sum().reset_index()

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.04,
        subplot_titles=["Equity Curve", "Drawdown (%)", "Daily P&L (USDC)"],
    )

    fig.add_trace(
        go.Scatter(
            x=trades["close_date"],
            y=trades["equity"],
            mode="lines",
            name="Equity",
            line=dict(color="#00bfff", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,191,255,0.08)",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=trades["close_date"],
            y=trades["drawdown_pct"],
            mode="lines",
            name="Drawdown",
            line=dict(color="#ff4444", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(255,68,68,0.15)",
        ),
        row=2,
        col=1,
    )

    bar_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in daily["profit_abs"]]
    fig.add_trace(
        go.Bar(
            x=daily["close_day"],
            y=daily["profit_abs"],
            name="Daily P&L",
            marker_color=bar_colors,
            opacity=0.8,
        ),
        row=3,
        col=1,
    )

    title = (
        f"<b>{strategy_name} · {s.get('timerange', 'full range')}</b><br>"
        f"<span style='font-size:12px'>"
        f"Start: ${starting_balance:.0f}  →  "
        f"Final: ${s['final_balance']:.2f}  "
        f"(+{s['profit_total'] * 100:.1f}%)  |  "
        f"Trades: {s['total_trades']}  |  "
        f"Winrate: {s['winrate'] * 100:.1f}%  |  "
        f"Sharpe: {s['sharpe']:.2f}  |  "
        f"Sortino: {s['sortino']:.2f}  |  "
        f"Max DD: {s['max_drawdown_account'] * 100:.1f}%"
        f"</span>"
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        template="plotly_dark",
        height=820,
        showlegend=False,
        margin=dict(t=90, b=40, l=70, r=20),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="USDC", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="USDC", row=3, col=1)

    stem = result_path.stem.replace(".zip", "")
    out_path = result_path.parent / f"{stem}_equity.html"
    fig.write_html(str(out_path))
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/plot_equity_plotly.py <backtest-result.zip|.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    output = build_equity_chart(input_path)
    print(f"Saved: {output}")
    webbrowser.open(output.resolve().as_uri())
