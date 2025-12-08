# Generating Equity Curves

Equity curves visualize your account balance over time during backtests, helping you understand drawdowns, volatility, and overall performance trajectory.

## Table of Contents

- [Using Freqtrade's Built-in Plots](#using-freqtrades-built-in-plots)
- [Plotting with freqtrade plot-dataframe](#plotting-with-freqtrade-plot-dataframe)
- [Custom Python Scripts](#custom-python-scripts)
- [Analyzing Equity Curves](#analyzing-equity-curves)

## Using Freqtrade's Built-in Plots

Freqtrade can generate equity curves and other plots automatically after backtesting.

### Method 1: Generate During Backtest

```bash
# Run backtest with plotting enabled
docker-compose run --rm pingpong_gmx backtrade \
  --strategy ADXMomentum \
  --timerange 20250101-20250201 \
  --export trades \
  --export-filename user_data/backtest_results/adx_backtest.json
```

### Method 2: Generate from Existing Results

```bash
# Generate plots from saved backtest results
docker-compose run --rm pingpong_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum \
  --timerange 20250101-20250201 \
  -p ETH/USDC:USDC
```

**Output location:** `user_data/plot/`

**Generated files:**
- `freqtrade-plot-ETH_USDC_USDC-1h.html` - Interactive chart with equity curve
- Entry/exit points marked on price chart
- Indicators overlayed

### Method 3: Plot Profit

For a pure equity curve visualization:

```bash
docker-compose run --rm pingpong_gmx freqtrade plot-profit \
  --timerange 20250101-20250201 \
  --export-filename user_data/backtest_results/adx_backtest.json
```

**Output:** `user_data/plot/freqtrade-profit-plot.html`

**Shows:**
- Cumulative profit over time
- Drawdown visualization
- Per-trade profit markers
- Daily/weekly profit aggregates

## Plotting with freqtrade plot-dataframe

The `plot-dataframe` command creates detailed charts with price action, indicators, and trade markers.

### Basic Usage

```bash
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=20250101-20250301

# Then plot
docker-compose run --rm adxmomentum_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum \
  --timerange 20250101-20250301 \
  -p ETH/USDC:USDC
```

### Advanced Options

```bash
docker-compose run --rm adxmomentum_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum \
  --timerange 20250101-20250301 \
  -p ETH/USDC:USDC \
  --indicators1 adx,plus_di,minus_di \
  --indicators2 mom \
  --plot-limit 500  # Last 500 candles only
```

**Indicators:**
- `--indicators1`: Main plot (overlayed on price)
- `--indicators2`: Sub-plot (separate panel below)

### Viewing the Plots

Open the generated HTML file in your browser:

```bash
# macOS
open user_data/plot/freqtrade-plot-ETH_USDC_USDC-1h.html

# Linux
xdg-open user_data/plot/freqtrade-plot-ETH_USDC_USDC-1h.html

# Or copy to host and open manually
```

## Custom Python Scripts

For more control, create custom equity curve plots using the backtest results JSON.

### Read Backtest Results

```python
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Load backtest results
with open('user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.json') as f:
    results = json.load(f)

# Extract trades
trades_df = pd.DataFrame(results['trades'])

# Convert timestamps
trades_df['open_date'] = pd.to_datetime(trades_df['open_date'])
trades_df['close_date'] = pd.to_datetime(trades_df['close_date'])

print(f"Total trades: {len(trades_df)}")
print(f"Starting balance: {results['starting_balance']}")
```

### Create Equity Curve

```python
# Calculate cumulative profit
trades_df = trades_df.sort_values('close_date')
trades_df['cumulative_profit'] = trades_df['profit_abs'].cumsum()
trades_df['equity'] = results['starting_balance'] + trades_df['cumulative_profit']

# Plot equity curve
plt.figure(figsize=(12, 6))
plt.plot(trades_df['close_date'], trades_df['equity'], linewidth=2)
plt.axhline(y=results['starting_balance'], color='gray', linestyle='--', label='Starting Balance')
plt.xlabel('Date')
plt.ylabel('Account Balance (USDC)')
plt.title('Equity Curve - ADXMomentum Strategy')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('equity_curve.png', dpi=300)
plt.show()

print(f"Final equity: ${trades_df['equity'].iloc[-1]:.2f}")
print(f"Total profit: ${trades_df['cumulative_profit'].iloc[-1]:.2f}")
```

### Add Drawdown Visualization

```python
# Calculate running maximum (peak equity)
trades_df['peak_equity'] = trades_df['equity'].cummax()

# Calculate drawdown (distance from peak)
trades_df['drawdown'] = trades_df['equity'] - trades_df['peak_equity']
trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['peak_equity']) * 100

# Plot equity with drawdown shading
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Equity curve
ax1.plot(trades_df['close_date'], trades_df['equity'], linewidth=2, label='Equity')
ax1.plot(trades_df['close_date'], trades_df['peak_equity'],
         linewidth=1, linestyle='--', color='green', alpha=0.5, label='Peak Equity')
ax1.set_ylabel('Account Balance (USDC)')
ax1.set_title('Equity Curve with Drawdowns')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Drawdown
ax2.fill_between(trades_df['close_date'], trades_df['drawdown_pct'], 0,
                  color='red', alpha=0.3)
ax2.plot(trades_df['close_date'], trades_df['drawdown_pct'],
         linewidth=1, color='red')
ax2.set_ylabel('Drawdown (%)')
ax2.set_xlabel('Date')
ax2.grid(True, alpha=0.3)
ax2.invert_yaxis()  # Drawdowns go down

plt.tight_layout()
plt.savefig('equity_with_drawdown.png', dpi=300)
plt.show()

# Print drawdown stats
max_dd = trades_df['drawdown_pct'].min()
print(f"Maximum drawdown: {max_dd:.2f}%")
```

### Monthly Returns Heatmap

```python
import seaborn as sns

# Extract month and year
trades_df['year'] = trades_df['close_date'].dt.year
trades_df['month'] = trades_df['close_date'].dt.month

# Calculate monthly returns
monthly_returns = trades_df.groupby(['year', 'month'])['profit_abs'].sum().reset_index()
monthly_returns['return_pct'] = (monthly_returns['profit_abs'] / results['starting_balance']) * 100

# Pivot for heatmap
returns_pivot = monthly_returns.pivot(index='month', columns='year', values='return_pct')

# Plot heatmap
plt.figure(figsize=(10, 6))
sns.heatmap(returns_pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            cbar_kws={'label': 'Return (%)'})
plt.title('Monthly Returns Heatmap')
plt.ylabel('Month')
plt.xlabel('Year')
plt.tight_layout()
plt.savefig('monthly_returns.png', dpi=300)
plt.show()
```

## Analyzing Equity Curves

### What to Look For

**1. Smooth vs Choppy**
- Smooth upward curve = consistent profitability
- Choppy/volatile = inconsistent, high risk
- Flat periods = strategy not trading or breaking even

**2. Drawdown Patterns**
- Shallow drawdowns (< 10%) = good risk management
- Deep drawdowns (> 20%) = review strategy or reduce leverage
- Quick recovery = resilient strategy
- Long recovery = concerning, may indicate market regime change

**3. Slope Changes**
- Consistent slope = strategy adapts to market conditions
- Steepening = possibly entering favorable conditions (or getting lucky)
- Flattening = less profitable, market conditions changed

**4. Comparison to Buy-and-Hold**
```python
# Load OHLCV data
ohlcv_df = pd.read_json('user_data/data/gmx/ETH_USDC_USDC-1h.json')
ohlcv_df['date'] = pd.to_datetime(ohlcv_df['date'], unit='ms')

# Calculate buy-and-hold equity
start_price = ohlcv_df.iloc[0]['close']
ohlcv_df['bh_equity'] = results['starting_balance'] * (ohlcv_df['close'] / start_price)

# Plot comparison
plt.figure(figsize=(12, 6))
plt.plot(trades_df['close_date'], trades_df['equity'],
         linewidth=2, label='ADXMomentum Strategy')
plt.plot(ohlcv_df['date'], ohlcv_df['bh_equity'],
         linewidth=2, alpha=0.7, label='Buy & Hold')
plt.xlabel('Date')
plt.ylabel('Account Balance (USDC)')
plt.title('Strategy vs Buy & Hold')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('strategy_vs_buyhold.png', dpi=300)
plt.show()
```

### Red Flags in Equity Curves

❌ **Exponential growth at the end** - Likely overfit or lucky outlier trades
❌ **Single vertical jump** - One massive winning trade carries entire strategy
❌ **Long flat periods followed by crash** - Strategy stopped working, didn't exit
❌ **Consistent stair-step down** - Losing strategy, stop using it

✅ **Gradual upward trend** - Sustainable edge
✅ **Drawdowns recover within reasonable time** - Resilient
✅ **Multiple profit cycles visible** - Works in different conditions

## Complete Example Script

Create `scripts/plot_equity.py`:

```python
#!/usr/bin/env python3
"""
Generate equity curve from Freqtrade backtest results

Usage:
    python scripts/plot_equity.py user_data/backtest_results/backtest-result-2025-12-08_12-34-56.json
"""

import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_equity_curve(results_file):
    # Load results
    with open(results_file) as f:
        results = json.load(f)

    if not results.get('trades'):
        print("No trades found in results!")
        return

    # Process trades
    trades_df = pd.DataFrame(results['trades'])
    trades_df['close_date'] = pd.to_datetime(trades_df['close_date'])
    trades_df = trades_df.sort_values('close_date')

    # Calculate equity
    starting_balance = results['starting_balance']
    trades_df['cumulative_profit'] = trades_df['profit_abs'].cumsum()
    trades_df['equity'] = starting_balance + trades_df['cumulative_profit']
    trades_df['peak_equity'] = trades_df['equity'].cummax()
    trades_df['drawdown_pct'] = ((trades_df['equity'] - trades_df['peak_equity'])
                                  / trades_df['peak_equity'] * 100)

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                     gridspec_kw={'height_ratios': [3, 1]})

    # Equity curve
    ax1.plot(trades_df['close_date'], trades_df['equity'],
             linewidth=2.5, color='#2E86AB', label='Equity')
    ax1.plot(trades_df['close_date'], trades_df['peak_equity'],
             linewidth=1, linestyle='--', color='green', alpha=0.5,
             label='Peak')
    ax1.axhline(y=starting_balance, color='gray', linestyle=':',
                alpha=0.5, label='Start')

    ax1.set_ylabel('Account Balance (USDC)', fontsize=12)
    ax1.set_title(f'Equity Curve - {results.get("strategy_name", "Unknown")}',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Drawdown
    ax2.fill_between(trades_df['close_date'], trades_df['drawdown_pct'], 0,
                     color='red', alpha=0.3)
    ax2.plot(trades_df['close_date'], trades_df['drawdown_pct'],
             linewidth=1.5, color='darkred')
    ax2.set_ylabel('Drawdown (%)', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.invert_yaxis()

    plt.tight_layout()

    # Save
    output_path = Path(results_file).parent / 'equity_curve.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Equity curve saved to: {output_path}")

    # Stats
    final_equity = trades_df['equity'].iloc[-1]
    total_profit = final_equity - starting_balance
    total_return = (total_profit / starting_balance) * 100
    max_drawdown = trades_df['drawdown_pct'].min()

    print(f"\n{'='*50}")
    print(f"  Starting Balance:  ${starting_balance:,.2f}")
    print(f"  Final Equity:      ${final_equity:,.2f}")
    print(f"  Total Profit:      ${total_profit:,.2f}")
    print(f"  Total Return:      {total_return:.2f}%")
    print(f"  Max Drawdown:      {max_drawdown:.2f}%")
    print(f"  Total Trades:      {len(trades_df)}")
    print(f"{'='*50}\n")

    plt.show()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python plot_equity.py <backtest_results.json>")
        sys.exit(1)

    plot_equity_curve(sys.argv[1])
```

Make it executable and use:

```bash
chmod +x scripts/plot_equity.py

# Plot results
python scripts/plot_equity.py user_data/backtest_results/backtest-result-2025-12-08_12-34-56.json
```

### Running the Script - Complete Example

Here's a complete workflow from backtest to equity curve visualization:

```bash
# 1. Run backtest for ADXMomentum strategy
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=20250101-20250401 VERBOSE=-vv

# 2. Find the backtest results file (it has a timestamp in the name)
ls -lt user_data/backtest_results/

# You'll see something like:
# backtest-result-2025-12-08_14-23-45.json

# 3. Generate equity curve with the script
python scripts/plot_equity.py user_data/backtest_results/backtest-result-2025-12-08_14-23-45.json
```

**Expected output:**

```
✓ Equity curve saved to: user_data/backtest_results/equity_curve.png

==================================================
  Starting Balance:  $10,000.00
  Final Equity:      $10,494.50
  Total Profit:      $494.50
  Total Return:      4.95%
  Max Drawdown:      -8.23%
  Total Trades:      23
==================================================
```

**Generated visualization:**

![ADX Strategy Equity Curve](equity_curve_adx.png)

The chart shows:
- **Blue line**: Your account balance over time
- **Green dashed line**: Peak equity (all-time high)
- **Red shaded area**: Drawdown from peak (bottom panel)

This visualization immediately shows you:
- Strategy profitability (upward trend = profitable)
- Risk level (shallow drawdowns = lower risk)
- Consistency (smooth curve = consistent performance)
- Recovery time (how quickly equity recovers after drawdowns)

## Resources

- [Freqtrade Plotting Documentation](https://www.freqtrade.io/en/stable/plotting/)
- [Matplotlib Documentation](https://matplotlib.org/stable/contents.html)
- [Pandas Time Series](https://pandas.pydata.org/docs/user_guide/timeseries.html)
