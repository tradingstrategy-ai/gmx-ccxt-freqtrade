# Quick Start: ADX Strategy with Equity Curves

Get up and running with the ADX Momentum strategy and visualize results in under 10 minutes.

## Step 1: Build Container (1 min)

```bash
docker-compose build adxmomentum_gmx
```

## Step 2: Download Data (2-3 min)

```bash
# Download 3 months of 1h data for ETH/USDC
make data CONTAINER=adxmomentum_gmx TIMEFRAME=1h TIMERANGE=20250101-20250401
```

## Step 3: Run Backtest (1-2 min)

```bash
# Run backtest with verbose output
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401 VERBOSE=-vv
```

**What you'll see:**
```
========================================= BACKTEST REPORT =========================================
|      Pair |   Entries |   Avg Profit % |   Cum Profit % |   Tot Profit USDC |   Tot Profit % |
|-----------+-----------+----------------+----------------+-------------------+----------------|
| ETH/USDC  |        23 |           2.15 |          49.45 |            494.50 |           4.95 |
|     TOTAL |        23 |           2.15 |          49.45 |            494.50 |           4.95 |
...
```

## Step 4: Generate Equity Curve (1 min)

### Method 1: Freqtrade Built-in

```bash
docker-compose run --rm adxmomentum_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum \
  --timerange 20250101-20250401 \
  -p ETH/USDC:USDC \
  --indicators1 adx,plus_di,minus_di \
  --indicators2 mom
```

**Open:** `user_data/plot/freqtrade-plot-ETH_USDC_USDC-1h.html`

### Method 2: Custom Python Script

```bash
# Find latest backtest results
ls -lt user_data/backtest_results/ | head -5

# Plot equity curve
python scripts/plot_equity.py user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.json
```

**Output:** `user_data/backtest_results/equity_curve.png`

## Understanding the Results

### The Equity Curve Shows:

1. **Blue line** = Your account balance over time
2. **Green dashed line** = Peak balance (all-time high)
3. **Red shaded area** = Drawdown from peak

### Key Metrics to Check:

**Good ADX Strategy:**
- Win rate: 40-55%
- Profit factor: > 1.5
- Max drawdown: < 20%
- Average profit per trade: > 2-3%

**Warning Signs:**
- Win rate < 30% (too many losers)
- Max drawdown > 25% (too risky)
- Equity curve flat or declining (not profitable)

## Next Steps

### 1. Understand the Strategy

**Key points:**
- ADX > 25 = Strong trend
- +DI > -DI = Bullish
- MOM > 0 = Positive momentum
- All conditions must be true to enter

### 2. Optimize Parameters

Try different values:

```python
# Edit user_data/strategies/ADXMomentum.py

# More conservative (fewer trades)
(dataframe['adx'] > 30)  # Instead of 25

# Take profits faster
minimal_roi = {"0": 0.03}  # Instead of 0.05

# Tighter stop loss
stoploss = -0.15  # Instead of -0.25
```

Re-run backtest after each change.

### 3. Test Different Timeframes

```bash
# 4h timeframe (longer holds)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=4h TIMERANGE=20250101-20250401

# Compare results
```

### 4. Test Different Date Ranges

```bash
# Q1 2025
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401

# Q2 2025 (out-of-sample)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250401-20250701
```

**Good strategy:** Performs similarly in both periods
**Overfit strategy:** Great in Q1, poor in Q2

## Common Issues

### No Trades Generated

**Solution:** Market may be range-bound. Try:
- Different date range (look for trending periods)
- Lower ADX threshold: `(dataframe['adx'] > 20)`

### Too Many Losing Trades

**Solution:** Strategy catching false breakouts. Try:
- Higher ADX threshold: `(dataframe['adx'] > 30)`
- Use 4h timeframe instead of 1h
- Tighten stop loss

### Equity Curve Very Volatile

**Solution:** High leverage or risky periods. Try:
- Reduce position size in config
- Tighter stop loss
- Skip volatile market periods

## Full Workflow Example

```bash
# 1. Build
docker-compose build adxmomentum_gmx

# 2. Download 6 months of data
make data CONTAINER=adxmomentum_gmx TIMEFRAME=1h TIMERANGE=20250101-20250701

# 3. Backtest first 3 months
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401 VERBOSE=-vv

# 4. Generate equity curve
python scripts/plot_equity.py user_data/backtest_results/backtest-result-*.json

# 5. Analyze results
# - Check win rate (aim for 40-55%)
# - Check max drawdown (keep < 20%)
# - Look for smooth upward equity curve

# 6. Test out-of-sample (last 3 months)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250401-20250701 VERBOSE=-vv

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
make data CONTAINER=adxmomentum_gmx TIMERANGE=YYYYMMDD-YYYYMMDD

# Backtest
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=YYYYMMDD-YYYYMMDD

# Plot with Freqtrade
docker-compose run --rm adxmomentum_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum --timerange YYYYMMDD-YYYYMMDD -p ETH/USDC:USDC

# Custom equity curve
python scripts/plot_equity.py user_data/backtest_results/backtest-result-*.json

# List backtest results
ls -lt user_data/backtest_results/
```

## Getting Help

If something isn't working:

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Verify data downloaded: `ls user_data/data/gmx/`
3. Check container built: `docker images | grep adxmomentum`
4. Run with verbose output: `VERBOSE=-vvv`
