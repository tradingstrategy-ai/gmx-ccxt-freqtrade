# Quick Start: ADX Strategy with Equity Curves

Get up and running with the ADX Momentum strategy and visualize results in under 15 minutes.

## Prerequisites

Install system dependencies first:

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt install -y python3-pip python3-venv python3-dev python3-pandas git curl
```

**macOS:**
```bash
brew install gettext libomp
```

**For other systems**, see [Freqtrade installation requirements](https://www.freqtrade.io/en/stable/installation/#requirements).

---

## Step 1: Setup Environment (3 mins)

```bash
# Clone project (if not done already)
git clone https://github.com/yourusername/freqtrade-gmx-demo.git
cd freqtrade-gmx-demo
git submodule update --init --recursive

# Clone freqtrade (naming is important to avoid Python import conflicts)
git clone https://github.com/freqtrade/freqtrade.git freqtrade-develop

# Create and activate virtual environment in main project directory
uv venv .venv
source .venv/bin/activate  # Linux/macOS (.venv\Scripts\activate on Windows)

# Install freqtrade
uv pip install -r freqtrade-develop/requirements.txt
uv pip install -e freqtrade-develop/

# Install GMX integration from local submodule (includes freqtrade integration)
uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"

# Verify installation
./freqtrade-gmx --version
```

**Why these steps?**
- We install from the **local submodule** (`deps/web3-ethereum-defi`) because the PyPI version doesn't include the freqtrade integration yet
- We use the **freqtrade-gmx wrapper script** to avoid Python import conflicts with the `freqtrade/` directory

## Step 2: Download Data (2-3 min)

```bash
# Download 3 months of 1h data for ETH/USDC
./freqtrade-gmx download-data \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --exchange gmx \
  --timeframe 1h \
  --timerange 20250101-20250401
```

## Step 3: Run Backtest (1-2 min)

```bash
# Run backtest with verbose output
./freqtrade-gmx backtesting \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --timeframe 1h \
  --timerange 20250101-20250401 \
  -vv
```

**What you'll see:**

```py
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃    Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃         Drawdown ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ ADXMomentum │     59 │        -0.08 │          -0.672 │        -0.67 │      1:58:00 │   18     0    41  30.5 │ 2.09 USDC  2.06% │
└─────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┴──────────────────┘
```

## Step 4: Generate Visualizations (3 mins)

### Option 1: Freqtrade Built-in (Interactive HTML)

```bash
# Generate interactive profit plot (equity curve, drawdowns)
./freqtrade-gmx plot-profit \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json

# Generate interactive candlestick charts with indicators
./freqtrade-gmx plot-dataframe \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --indicators1 adx plus_di minus_di \
  --indicators2 mom
```

**Output:** Interactive HTML files in `user_data/plot/`

### Option 2: Custom Python Script (PNG Images)

```bash
# Activate virtual environment
source .venv/bin/activate

# Find latest backtest results
ls -lt user_data/backtest_results/ | head -5

# Generate equity curve and monthly returns heatmap
python scripts/plot_equity.py user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.json
```

**Output:**
- `user_data/backtest_results/equity_curve.png`
- `user_data/backtest_results/monthly_returns.png`

## How the ADXMomentum Strategy Works

Trend-following momentum strategy that enters long positions during strong upward trends and exits when momentum reverses.

### Entry Conditions (All must be true):

1. **ADX > 25**: Strong trend present (not range-bound)
2. **MOM > 0**: Positive momentum (price increasing)
3. **+DI > 25**: Strong upward directional movement
4. **+DI > -DI**: Upward direction stronger than downward

### Exit Conditions (All must be true):

1. **ADX > 25**: Still in trending market
2. **MOM < 0**: Momentum turned negative
3. **-DI > 25**: Strong downward directional movement
4. **+DI < -DI**: Downward direction stronger than upward


### Strategy Logic:

This strategy enters when a strong uptrend is confirmed by multiple indicators agreeing, and exits when momentum reverses. It's designed to capture the middle of trends while avoiding false breakouts in ranging markets.

## Understanding the Results

### The Equity Curve Shows:

1. **Blue line** = Your account balance over time
2. **Green dashed line** = Peak balance (all-time high)
3. **Red shaded area** = Drawdown from peak


### Test Different Timeframes

```bash
# 4h timeframe (longer holds)
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 4h \
  --timerange 20250101-20250401

# Compare results
```

### Test Different Date Ranges

```bash
# Q1 2025
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange 20250101-20250401

# Q2 2025 (out-of-sample)
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange 20250401-20250701
```


## Common Issues

### No Trades Generated

**Solution:** Market may be range-bound. Try:
- Different date range (look for trending periods)
- Lower ADX threshold: `(dataframe['adx'] > 20)`

### Too Many Losing Trades

**Solution:** You suck. Give up.


## Full Workflow Example

```bash
# 1. Setup (if not done)
# See Step 1 above

# 2. Download 6 months of data
./freqtrade-gmx download-data \
  --exchange gmx \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange 20250101-20250701

# 3. Backtest first 3 months
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange 20250101-20250401 \
  -vv

# 4. Generate equity curve
source .venv/bin/activate
python scripts/plot_equity.py user_data/backtest_results/backtest-result-*.json

# 5. Analyze results
# - Check win rate (aim for 40-55%)
# - Check max drawdown (keep < 20%)
# - Look for smooth upward equity curve

# 6. Test out-of-sample (last 3 months)
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange 20250401-20250701 \
  -vv

# 7. Compare results
# - Similar performance = robust strategy
# - Worse performance = may be overfit
```

## Resources

- **[Equity Curves Guide](equity-curves.md)** - Advanced plotting and analysis
- **[GMX Specifics](gmx-specifics.md)** - GMX trading considerations

## Quick Commands Cheat Sheet

```bash
# Data download
./freqtrade-gmx download-data \
  --exchange gmx \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timeframe 1h \
  --timerange YYYYMMDD-YYYYMMDD

# Backtest
./freqtrade-gmx backtesting \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --timerange YYYYMMDD-YYYYMMDD

# Visualizations (Freqtrade built-in)
./freqtrade-gmx plot-profit \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json
./freqtrade-gmx plot-dataframe \
  --strategy ADXMomentum \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --indicators1 adx plus_di minus_di

# Visualizations (Custom Python)
source .venv/bin/activate
python scripts/plot_equity.py user_data/backtest_results/backtest-result-*.json

# List backtest results
ls -lt user_data/backtest_results/
```

## Getting Help

If something isn't working:

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Verify venv activated: `which python` (should show `.venv/bin/python`)
3. Verify data downloaded: `ls user_data/data/gmx/`
4. Run with verbose output: add `-vvv` flag to commands
