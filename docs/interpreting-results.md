# Interpreting Results

Understanding and analyzing backtest output to evaluate strategy performance.

## Table of Contents

- [Backtest Output Overview](#backtest-output-overview)
- [Key Metrics Explained](#key-metrics-explained)
- [Performance Analysis](#performance-analysis)
- [GMX-Specific Considerations](#gmx-specific-considerations)
- [Optimization Guidelines](#optimization-guidelines)

## Backtest Output Overview

After running a backtest, you'll see output like this:

```
========================================= BACKTEST REPORT =========================================
|      Pair |   Entries |   Avg Profit % |   Cum Profit % |   Tot Profit USDC |   Tot Profit % |   Avg Duration |   Win  Draw  Loss  Win% |
|-----------+-----------+----------------+----------------+-------------------+----------------+----------------+-------------------------|
| ETH/USDC  |        45 |           0.25 |          11.25 |            112.50 |           1.13 |        0:01:00 |    27     0    18  60.0 |
|     TOTAL |        45 |           0.25 |          11.25 |            112.50 |           1.13 |        0:01:00 |    27     0    18  60.0 |
========================================== SUMMARY METRICS =========================================
| Metric                      | Value                  |
|-----------------------------|------------------------|
| Backtesting from            | 2025-01-01 00:00:00    |
| Backtesting to              | 2025-02-01 00:00:00    |
| Max open trades             | 1                      |
|                             |                        |
| Total/Daily Avg Trades      | 45 / 1.45              |
| Starting balance            | 10000 USDC             |
| Final balance               | 10112.50 USDC          |
| Absolute profit             | 112.50 USDC            |
| Total profit %              | 1.13%                  |
| Avg. stake amount           | 1000 USDC              |
| Total trade volume          | 45000 USDC             |
|                             |                        |
| Long / Short                | 45 / 0                 |
| Total profit Long %         | 1.13%                  |
| Total profit Short %        | 0.00%                  |
|                             |                        |
| Best Pair                   | ETH/USDC 1.13%         |
| Worst Pair                  | ETH/USDC 1.13%         |
|                             |                        |
| Best trade                  | 2.50%                  |
| Worst trade                 | -1.20%                 |
| Best day                    | 8.75%                  |
| Worst day                   | -3.50%                 |
| Days win/draw/lose          | 18 / 8 / 5             |
| Avg. Duration Winners       | 0:01:00                |
| Avg. Duration Loser         | 0:01:00                |
|                             |                        |
| Max Consecutive Wins / Loss | 5 / 3                  |
| Rejected Entry signals      | 0                      |
| Entry/Exit Timeouts         | 0 / 0                  |
|                             |                        |
| Min balance                 | 9950 USDC              |
| Max balance                 | 10150 USDC             |
| Max % of account underwater | 2.5%                   |
| Absolute Drawdown (Account) | 2.5%                   |
| Drawdown                    | 50 USDC                |
| Drawdown high               | 150 USDC               |
| Drawdown low                | 100 USDC               |
| Drawdown Start              | 2025-01-15 14:35:00    |
| Drawdown End                | 2025-01-16 09:10:00    |
| Market change               | 5.2%                   |
```

## Key Metrics Explained

### Trading Performance

**Total/Daily Avg Trades**
- Total trades executed during backtest period
- Average trades per day
- Example: `45 / 1.45` = 45 trades over ~31 days

**Win Rate (Win%)**
- Percentage of profitable trades
- Formula: `(Winning trades / Total trades) × 100`
- Good: > 50%, Excellent: > 60%
- **Important**: High win rate doesn't guarantee profitability!

**Average Profit %**
- Average profit/loss per trade
- Should be positive and > trading fees (~0.08-0.12% on GMX)
- Minimum target: > 0.5% to cover fees + gas

**Total Profit %**
- Overall return on starting balance
- Most important metric for strategy evaluation
- Compare to buy-and-hold (see "Market change")

**Profit Factor**
- Ratio of gross profit to gross loss
- Formula: `Total profit from wins / Total loss from losses`
- > 1.0 = profitable, > 1.5 = good, > 2.0 = excellent

### Risk Metrics

**Max Drawdown**
- Largest peak-to-trough decline
- Shows worst-case scenario
- Target: < 20% for most strategies
- **Critical**: Ensure you can tolerate this drawdown psychologically

**Sharpe Ratio**
- Risk-adjusted return measure
- Higher = better risk-adjusted performance
- < 1 = poor, 1-2 = decent, > 2 = excellent
- Annualized: multiply by √trading_days

**Best/Worst Trade**
- Largest single win and loss
- Check if outliers significantly affect results
- Large outliers may indicate overfitting

**Max Consecutive Wins/Losses**
- Longest winning and losing streaks
- High loss streaks = psychologically difficult
- Plan for worst-case scenarios

### Duration Metrics

**Average Duration**
- Average time positions are held
- Shorter durations = more sensitive to gas costs
- Longer durations = more funding fee impact

**Avg Duration Winners vs Losers**
- Compare hold times for wins vs losses
- Winners held longer = "let winners run"
- Losers held longer = poor exit strategy

### Account Metrics

**Starting/Final Balance**
- Initial and ending account value
- Absolute profit = Final - Starting

**Min/Max Balance**
- Account value range during backtest
- Shows volatility and drawdown impact

**Max % Account Underwater**
- Worst unrealized loss relative to peak
- Different from drawdown (which uses realized balance)

## Performance Analysis

### Is This Strategy Viable?

Ask yourself:

**1. Is it profitable?**
- Total profit % > 0 ✅
- Average profit per trade > fees (0.5%+) ✅

**2. Is it consistent?**
- Win rate > 40-50% (or avg winners >> avg losers) ✅
- No extreme outliers driving all profit ✅
- Profit factor > 1.2 ✅

**3. Can you tolerate the risk?**
- Max drawdown within your comfort zone ✅
- Consecutive loss streaks manageable ✅
- Daily/weekly swings acceptable ✅

**4. Does it beat buy-and-hold?**
- Total profit % > Market change ✅
- Risk-adjusted (Sharpe ratio > 1) ✅

### Identifying Overfitting

**Warning signs:**

❌ **Too good to be true results**
- Win rate > 80%
- Profit factor > 5
- Near-zero drawdowns

❌ **Reliance on outliers**
- One or two trades account for most profit
- Remove best trade → strategy unprofitable

❌ **Not robust across timeframes**
- Works only on specific dates
- Fails on different date ranges

❌ **Too many parameters**
- 10+ optimized parameters
- Performs poorly when parameters slightly change

**Testing for overfitting:**

1. **Out-of-sample testing**
   ```bash
   # Train on Jan-Feb
   make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20250101-20250301

   # Test on Mar-Apr (never seen data)
   make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20250301-20250501
   ```

2. **Walk-forward analysis**
   - Optimize on period 1
   - Test on period 2
   - Re-optimize on period 2
   - Test on period 3
   - Repeat...

3. **Parameter sensitivity**
   - Change RSI period from 14 to 13 or 15
   - Strategy should still work (maybe slightly worse)

### Comparing Strategies

When comparing multiple strategies:

**Absolute metrics:**
- Total profit %
- Win rate
- Max drawdown

**Risk-adjusted metrics:**
- Sharpe ratio (higher = better)
- Profit factor (higher = better)
- Calmar ratio: `Return / Max Drawdown` (higher = better)

**Practical considerations:**
- Trade frequency (more trades = more gas costs)
- Average hold time (longer = more funding fees)
- Drawdown tolerance (can you handle it?)

**Example comparison:**

| Strategy | Profit % | Win% | Sharpe | Max DD | Trades | Avg Hold |
|----------|----------|------|--------|--------|--------|----------|
| Strategy A | 15% | 45% | 1.8 | 12% | 120 | 2h |
| Strategy B | 18% | 55% | 1.5 | 25% | 80 | 6h |

**Analysis:**
- Strategy A: Better risk-adjusted (higher Sharpe, lower drawdown)
- Strategy B: Higher absolute return but more volatile
- Choice depends on risk tolerance

## GMX-Specific Considerations

### Funding Fee Impact

Funding fees are **not automatically included** in standard Freqtrade backtests.

**Manual calculation:**

```python
# Assuming avg 0.01% per 8h funding
funding_periods = total_hours_held / 8
funding_cost = position_size × leverage × 0.01% × funding_periods

# Example: 10 trades, avg hold 24h each, 5x leverage, $1000 positions
total_funding = 10 × ($1000 × 5 × 0.01% × 3) = $15

# Reduce backtest profit by $15
```

**Rough estimates:**
- **< 8 hours hold**: Negligible (0-0.01%)
- **8-24 hours**: Low (0.01-0.03%)
- **1-3 days**: Moderate (0.03-0.15%)
- **> 1 week**: Significant (0.5-2%+)

**Strategies affected:**
- Long-term trend following ⚠️ High impact
- Swing trading (days) ⚠️ Moderate impact
- Day trading (hours) ✅ Low impact
- Scalping (minutes) ✅ Negligible impact

### Gas Cost Impact

Gas costs are **not included** in backtests either.

**Calculation:**

```python
# Arbitrum: ~$0.25 per trade (avg entry + exit = 2 transactions)
gas_per_trade = 0.50  # USD
total_gas = num_trades × gas_per_trade

# Example: 100 trades
total_gas = 100 × $0.50 = $50

# Reduce backtest profit by $50
```

**Impact by trade frequency:**

| Trades/Month | Gas Cost | Impact on $10k account |
|--------------|----------|------------------------|
| 10 | $5 | 0.05% |
| 50 | $25 | 0.25% |
| 100 | $50 | 0.50% |
| 500 | $250 | 2.50% |

**Strategies affected:**
- High frequency (> 100 trades/month) ⚠️ Significant
- Medium frequency (50-100) ⚠️ Moderate
- Low frequency (< 50) ✅ Minimal

### Trading Fee Reality Check

Backtest fees vs GMX reality:

**Freqtrade simulation:**
- Entry fee: 0.05% (typical)
- Exit fee: 0.05% (typical)
- Total: 0.10%

**GMX actual:**
- Entry: 0.04-0.07% (depends on pool balance)
- Exit: 0.04-0.07%
- Total: 0.08-0.14%

**Recommendation:** Set backtest fees to 0.06% each side (0.12% total) for conservative estimates.

```json
{
  "exchange": {
    "fee": 0.0006  // 0.06%
  }
}
```

### Liquidity Constraints

Backtests assume **infinite liquidity** - GMX does not!

**Reality check:**

```python
# Check if your position sizes are realistic
avg_position_size = 1000  # USDC
max_position_size = 5000  # USDC

# GMX ETH/USDC typical available liquidity: $500k-2M
# Your $5k position = 0.25-1% of liquidity ✅ OK

# But $100k position = 5-20% of liquidity ⚠️ High slippage!
```

**Safe position sizing:**
- < 1% of available liquidity: ✅ Minimal slippage
- 1-5%: ⚠️ Moderate slippage (0.1-0.5%)
- > 5%: ❌ High slippage (> 1%)

### Slippage Assumptions

Freqtrade default slippage may be too optimistic for GMX.

**Recommended slippage:**
- Small positions (< $10k): 0.05% (5 bps)
- Medium positions ($10k-50k): 0.10% (10 bps)
- Large positions (> $50k): 0.20-0.50% (20-50 bps)

```json
{
  "exchange": {
    "slippage": 0.05  // 0.05% = 5 basis points
  }
}
```

## Optimization Guidelines

### What to Optimize

**Good candidates:**
- Entry thresholds (RSI < 30 vs < 35)
- Exit thresholds (ROI targets)
- Indicator periods (EMA 10 vs 12 vs 15)
- Stoploss levels (-5% vs -10%)

**Bad candidates:**
- Too many parameters (> 5-7)
- Highly correlated parameters
- Parameters without logical basis

### Optimization Process

**1. Baseline**
```bash
# Run with default parameters
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20250101-20250301
```

**2. Single parameter sweep**
```python
# Test RSI thresholds: 25, 30, 35, 40
# Pick best performing value
```

**3. Multi-parameter optimization**
```bash
# Use Freqtrade hyperopt (advanced)
docker-compose run pingpong_gmx hyperopt \
  --hyperopt-loss SharpeHyperOptLoss \
  --strategy MyStrategy \
  --epochs 100
```

**4. Validate out-of-sample**
```bash
# Test optimized parameters on new data
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20250301-20250501
```

### Optimization Pitfalls

❌ **Optimizing on all available data**
- Always hold out 20-30% for validation

❌ **Chasing maximum profit**
- Optimize for Sharpe ratio or profit factor instead

❌ **Ignoring practical constraints**
- Don't optimize for 1000 trades/day (gas costs!)

❌ **Over-optimization**
- If performance degrades out-of-sample, reduce complexity

### Parameter Sensitivity

Good strategies are **robust** to small parameter changes:

```
RSI period 13: +12% profit
RSI period 14: +15% profit ✅
RSI period 15: +13% profit
```

Bad (overfit) strategies are **fragile**:

```
RSI period 13: -5% profit
RSI period 14: +25% profit ❌ (only works here!)
RSI period 15: -2% profit
```

## Result Files

Backtest results are saved to `user_data/backtest_results/`:

```bash
# List recent backtests
ls -lt user_data/backtest_results/

# View detailed results
cat user_data/backtest_results/backtest-result-2025-12-08_12-34-56.json | jq
```

**Files created:**
- `.json` - Full trade list with entry/exit prices, P&L, timestamps
- `.meta.json` - Metadata (strategy name, timeframe, date range, config)

**Analyzing trade data:**

```python
import json
import pandas as pd

# Load results
with open('user_data/backtest_results/backtest-result-2025-12-08_12-34-56.json') as f:
    data = json.load(f)

# Convert to DataFrame
trades = pd.DataFrame(data['trades'])

# Analyze
print(f"Total trades: {len(trades)}")
print(f"Winners: {len(trades[trades['profit_abs'] > 0])}")
print(f"Average profit: {trades['profit_ratio'].mean():.2%}")
```

## Quick Checklist

Before deploying a strategy live, verify:

- ✅ Positive total profit over multiple months
- ✅ Win rate > 40% OR profit factor > 1.5
- ✅ Max drawdown < 20% (or your tolerance)
- ✅ Sharpe ratio > 1.0
- ✅ Performance holds out-of-sample
- ✅ Not reliant on 1-2 outlier trades
- ✅ Robust to small parameter changes
- ✅ Profitable after accounting for:
  - Gas costs ($0.50/trade × trade count)
  - Funding fees (especially if holding > 8h)
  - Realistic slippage (0.05-0.10%)
- ✅ Position sizes < 1% of GMX liquidity
- ✅ Tested on bull AND bear markets

## Next Steps

1. **Technical details** → [Architecture](architecture.md)
   - Understand the monkeypatch approach
   - CCXT and GMX integration
   - Extend functionality

2. **Troubleshooting** → [Troubleshooting](troubleshooting.md)
   - Common backtest issues
   - Data problems
   - Strategy debugging

3. **Examples** → [Examples](examples/)
   - Practical strategy tutorials
   - Optimization workflows

## Resources

- [Freqtrade Backtesting Docs](https://www.freqtrade.io/en/stable/backtesting/)
- [Freqtrade Strategy Analysis](https://www.freqtrade.io/en/stable/strategy-analysis-example/)
- [GMX Stats](https://stats.gmx.io) - Live GMX data
