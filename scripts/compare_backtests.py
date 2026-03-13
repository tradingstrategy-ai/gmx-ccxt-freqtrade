#!/usr/bin/env python3
"""Compare multiple Freqtrade backtest results with interactive Plotly charts.

Generates:
  1. Equity curve overlay with drawdown subplot
  2. Exit reasons grouped bar chart
  3. Monthly returns heatmaps (one per strategy)
  4. Prints a side-by-side comparison table to stdout

Usage:
    # Compare 2 or more backtest result files (.json or .zip)
    python scripts/compare_backtests.py \\
        user_data/backtest_results/backtest-result-2026-03-12_14-57-15.json \\
        user_data/backtest_results/backtest-result-2026-03-12_15-00-48.json \\
        user_data/backtest_results/backtest-result-2026-03-12_15-03-38.json

    # Override output directory (default: same dir as first input file)
    python scripts/compare_backtests.py --output-dir /tmp/charts \\
        user_data/backtest_results/*.json

    # Auto-extract .zip files
    python scripts/compare_backtests.py \\
        user_data/backtest_results/backtest-result-2026-03-12_14-57-15.zip

    # Open charts in browser after generation
    python scripts/compare_backtests.py --open \\
        user_data/backtest_results/*.json
"""

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLORS = [
    '#4ECDC4',  # teal
    '#FF6B6B',  # coral
    '#45B7D1',  # sky blue
    '#FFA07A',  # light salmon
    '#98D8C8',  # mint
    '#F7DC6F',  # gold
    '#BB8FCE',  # lavender
    '#85C1E9',  # powder blue
]


def load_backtest(path: Path) -> dict[str, dict]:
    """Load a freqtrade backtest result file (.json or .zip).

    :param path: Path to the backtest result file.
    :returns: Dict mapping strategy name to its result dict.
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If the file format is unrecognised.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as zf:
            json_names = [n for n in zf.namelist() if n.endswith('.json') and '_config' not in n]
            if not json_names:
                raise ValueError(f"No result JSON found in {path}")
            with zf.open(json_names[0]) as f:
                data = json.load(f)
    elif path.suffix == '.json':
        with open(path) as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    if 'strategy' in data:
        return data['strategy']

    # Old format: top-level key is strategy name
    strategies = {}
    for key, val in data.items():
        if isinstance(val, dict) and 'trades' in val:
            strategies[key] = val
    if not strategies:
        raise ValueError(f"No strategy data found in {path}")
    return strategies


def build_equity_df(strat_data: dict, name: str) -> pd.DataFrame:
    """Build an equity curve DataFrame from strategy backtest data.

    :param strat_data: Strategy result dict containing trades and starting_balance.
    :param name: Strategy name for labelling.
    :returns: DataFrame with date, equity, drawdown_pct columns.
    """
    trades = strat_data['trades']
    starting_balance = strat_data['starting_balance']

    trades_sorted = sorted(trades, key=lambda t: t['close_date'])

    records = [{'date': trades_sorted[0]['open_date'], 'equity': starting_balance}]
    cumulative = starting_balance
    for t in trades_sorted:
        cumulative += t['profit_abs']
        records.append({'date': t['close_date'], 'equity': cumulative})

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['peak'] = df['equity'].cummax()
    df['drawdown_pct'] = ((df['equity'] - df['peak']) / df['peak']) * 100
    df['strategy'] = name
    return df


def plot_equity_curves(strategies: dict[str, dict], output_dir: Path) -> Path:
    """Generate interactive equity curve + drawdown chart.

    :param strategies: Dict mapping strategy name to its result dict.
    :param output_dir: Directory to save the HTML file.
    :returns: Path to the generated HTML file.
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Equity Curve (USDC)', 'Drawdown (%)'),
        vertical_spacing=0.12,
        row_heights=[0.65, 0.35],
    )

    for i, (name, strat_data) in enumerate(strategies.items()):
        color = COLORS[i % len(COLORS)]
        df = build_equity_df(strat_data, name)

        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['equity'],
                name=name, line=dict(color=color, width=2),
                hovertemplate='%{y:,.0f} USDC<extra>' + name + '</extra>',
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['drawdown_pct'],
                name=f'{name} DD', line=dict(color=color, width=1.5),
                showlegend=False, fill='tozeroy',
                hovertemplate='%{y:.1f}%<extra>' + name + '</extra>',
            ),
            row=2, col=1,
        )

    fig.update_layout(
        title='Strategy Comparison — Equity Curves & Drawdowns',
        height=800, width=1200,
        template='plotly_dark',
        legend=dict(x=0.01, y=0.98),
        hovermode='x unified',
    )
    fig.update_yaxes(title_text='Balance (USDC)', row=1, col=1)
    fig.update_yaxes(title_text='Drawdown %', row=2, col=1)
    fig.update_xaxes(title_text='Date', row=2, col=1)

    out = output_dir / 'equity_comparison.html'
    fig.write_html(str(out))
    return out


def plot_exit_reasons(strategies: dict[str, dict], output_dir: Path) -> Path:
    """Generate exit reasons grouped bar chart.

    :param strategies: Dict mapping strategy name to its result dict.
    :param output_dir: Directory to save the HTML file.
    :returns: Path to the generated HTML file.
    """
    fig = go.Figure()

    for i, (name, strat_data) in enumerate(strategies.items()):
        color = COLORS[i % len(COLORS)]
        ers = strat_data.get('exit_reason_summary', [])
        reasons = [e.get('key', e.get('exit_reason', '?')) for e in ers]
        counts = [e['trades'] for e in ers]
        fig.add_trace(go.Bar(name=name, x=reasons, y=counts, marker_color=color))

    fig.update_layout(
        title='Exit Reasons by Strategy',
        barmode='group',
        height=500, width=1200,
        template='plotly_dark',
        xaxis_title='Exit Reason',
        yaxis_title='Trade Count',
    )

    out = output_dir / 'exit_reasons_comparison.html'
    fig.write_html(str(out))
    return out


def plot_monthly_returns(strategies: dict[str, dict], output_dir: Path) -> Path:
    """Generate monthly returns heatmap for each strategy.

    :param strategies: Dict mapping strategy name to its result dict.
    :param output_dir: Directory to save the HTML file.
    :returns: Path to the generated HTML file.
    """
    n = len(strategies)
    names = list(strategies.keys())

    fig = make_subplots(
        rows=n, cols=1,
        subplot_titles=[f'{name} — Monthly Returns (%)' for name in names],
        vertical_spacing=0.08,
    )

    for i, (name, strat_data) in enumerate(strategies.items()):
        trades = pd.DataFrame(strat_data['trades'])
        trades['close_date'] = pd.to_datetime(trades['close_date'], utc=True)
        trades['year'] = trades['close_date'].dt.year
        trades['month'] = trades['close_date'].dt.month
        starting_balance = strat_data['starting_balance']

        monthly = trades.groupby(['year', 'month'])['profit_abs'].sum().reset_index()
        monthly['return_pct'] = (monthly['profit_abs'] / starting_balance) * 100

        pivot = monthly.pivot(index='month', columns='year', values='return_pct').fillna(0)
        pivot = pivot.reindex(range(1, 13), fill_value=0)

        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        fig.add_trace(
            go.Heatmap(
                z=pivot.values,
                x=[str(y) for y in pivot.columns],
                y=month_labels,
                colorscale='RdYlGn',
                zmid=0,
                text=pivot.values.round(1),
                texttemplate='%{text}',
                showscale=(i == 0),
                hovertemplate='%{y} %{x}: %{z:.1f}%<extra>' + name + '</extra>',
            ),
            row=i + 1, col=1,
        )

    fig.update_layout(
        height=300 * n + 100,
        width=1200,
        template='plotly_dark',
        title='Monthly Returns Heatmaps',
    )

    out = output_dir / 'monthly_returns_comparison.html'
    fig.write_html(str(out))
    return out


def print_comparison_table(strategies: dict[str, dict]) -> None:
    """Print a side-by-side comparison table to stdout.

    :param strategies: Dict mapping strategy name to its result dict.
    """
    metrics = [
        ('Total Trades', 'total_trades', '{:,}'),
        ('Long / Short', None, None),
        ('Win Rate', 'winrate', '{:.1%}'),
        ('Wins / Losses', None, None),
        ('Total Profit %', 'profit_total', '{:.2%}'),
        ('Total Profit USDC', 'profit_total_abs', '{:,.0f}'),
        ('Long Profit USDC', 'profit_total_long_abs', '{:,.0f}'),
        ('Short Profit USDC', 'profit_total_short_abs', '{:,.0f}'),
        ('CAGR', 'cagr', '{:.1%}'),
        ('Avg Profit/Trade', 'profit_mean', '{:.2%}'),
        ('Profit Factor', 'profit_factor', '{:.2f}'),
        ('Sharpe', 'sharpe', '{:.2f}'),
        ('Sortino', 'sortino', '{:.2f}'),
        ('Calmar', 'calmar', '{:.2f}'),
        ('Max DD %', 'max_drawdown_account', '{:.1%}'),
        ('Max DD USDC', 'max_drawdown_abs', '{:,.0f}'),
        ('DD Duration', 'drawdown_duration', '{}'),
        ('Avg Hold Time', 'holding_avg', '{}'),
        ('Final Balance', 'final_balance', '{:,.0f}'),
        ('Trades/Day', 'trades_per_day', '{:.1f}'),
    ]

    names = list(strategies.keys())
    col_width = max(20, max(len(n) for n in names) + 2)
    label_width = 22

    # Header
    header = f"{'Metric':<{label_width}}" + ''.join(f'{n:>{col_width}}' for n in names)
    print(f"\n{'=' * len(header)}")
    print(header)
    print(f"{'=' * len(header)}")

    for label, key, fmt in metrics:
        row = f'{label:<{label_width}}'

        for name in names:
            s = strategies[name]

            if label == 'Long / Short':
                val = f"{s.get('trade_count_long', 0)} / {s.get('trade_count_short', 0)}"
            elif label == 'Wins / Losses':
                val = f"{s.get('wins', 0)} / {s.get('losses', 0)}"
            elif key and key in s:
                val = fmt.format(s[key])
            else:
                val = 'N/A'

            row += f'{val:>{col_width}}'

        print(row)

    print(f"{'=' * len(header)}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Compare Freqtrade backtest results with interactive Plotly charts.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        'files', nargs='+', type=Path,
        help='Backtest result files (.json or .zip)',
    )
    parser.add_argument(
        '--output-dir', '-o', type=Path, default=None,
        help='Output directory for charts (default: same as first input file)',
    )
    parser.add_argument(
        '--open', action='store_true', dest='open_browser',
        help='Open charts in browser after generation',
    )
    args = parser.parse_args()

    output_dir = args.output_dir or args.files[0].parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all strategies
    all_strategies = {}
    for path in args.files:
        try:
            loaded = load_backtest(path)
            all_strategies.update(loaded)
            for name in loaded:
                print(f"Loaded: {name} from {path.name}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Warning: {e}", file=sys.stderr)

    if not all_strategies:
        print("Error: No strategy data loaded.", file=sys.stderr)
        sys.exit(1)

    # Generate charts
    equity_path = plot_equity_curves(all_strategies, output_dir)
    print(f"Saved: {equity_path}")

    exit_path = plot_exit_reasons(all_strategies, output_dir)
    print(f"Saved: {exit_path}")

    monthly_path = plot_monthly_returns(all_strategies, output_dir)
    print(f"Saved: {monthly_path}")

    # Print comparison table
    print_comparison_table(all_strategies)

    if args.open_browser:
        for p in [equity_path, exit_path, monthly_path]:
            subprocess.Popen(['open', str(p)])


if __name__ == '__main__':
    main()
