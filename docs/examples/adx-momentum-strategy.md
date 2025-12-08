# ADX Momentum Strategy

A trend-following strategy using ADX (Average Directional Index) to identify strong trends and momentum indicators to time entries and exits.

## Table of Contents

- [Strategy Overview](#strategy-overview)
- [Indicators Explained](#indicators-explained)
- [Entry Logic](#entry-logic)
- [Exit Logic](#exit-logic)
- [Running the Strategy](#running-the-strategy)
- [Understanding the Results](#understanding-the-results)
- [Optimization Tips](#optimization-tips)

## Strategy Overview

The ADXMomentum strategy combines multiple technical indicators to capture strong trending moves:

**Core Concept:** Enter when a strong trend is confirmed by ADX and momentum is positive, exit when trend weakens or momentum reverses.

**Best for:**
- Trending markets (bull or bear runs)
- Medium to long-term holds (1h+ timeframes)
- GMX perpetuals with clear directional bias

**Not suitable for:**
- Range-bound/choppy markets
- Very short timeframes (< 1h)
- Low-volatility conditions

## Indicators Explained

### 1. ADX (Average Directional Index)

**What it measures:** Trend strength (not direction)

```python
dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
```

**Interpretation:**
- **ADX > 25**: Strong trend (good for trend-following)
- **ADX 20-25**: Moderate trend
- **ADX < 20**: Weak trend or ranging (avoid trading)
- **ADX > 50**: Very strong trend (but may be overextended)

**Why 25?** This is the threshold where trends become statistically reliable for trend-following strategies.

### 2. +DI and -DI (Directional Indicators)

**What they measure:** Direction of the trend

```python
dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=25)
dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=25)
```

**Interpretation:**
- **+DI > -DI**: Uptrend (bulls in control)
- **-DI > +DI**: Downtrend (bears in control)
- **+DI > 25**: Strong bullish momentum
- **-DI > 25**: Strong bearish momentum

**Crossovers:** When +DI crosses above -DI, it signals potential uptrend start.

### 3. Momentum (MOM)

**What it measures:** Rate of price change

```python
dataframe['mom'] = ta.MOM(dataframe, timeperiod=14)
```

**Interpretation:**
- **MOM > 0**: Positive momentum (price rising)
- **MOM < 0**: Negative momentum (price falling)
- **MOM magnitude**: Strength of momentum

**Why momentum?** Confirms that price is actually moving in the trend direction, not just consolidating during high ADX.

### 4. Parabolic SAR

**What it measures:** Trailing stop and trend reversal points

```python
dataframe['sar'] = ta.SAR(dataframe)
```

**Interpretation:**
- **SAR below price**: Uptrend
- **SAR above price**: Downtrend
- **SAR flips**: Potential trend reversal

**Note:** Currently calculated but not used in entry/exit logic. Can be added for additional confirmation or trailing stops.

## Entry Logic

```python
def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['adx'] > 25) &              # Strong trend
            (dataframe['mom'] > 0) &               # Positive momentum
            (dataframe['plus_di'] > 25) &          # Strong bullish movement
            (dataframe['plus_di'] > dataframe['minus_di'])  # Bulls winning
        ),
        'enter_long'] = 1
    return dataframe
```

**Conditions breakdown:**

1. **ADX > 25**: Ensures we only trade in strong trends (avoids choppy markets)
2. **MOM > 0**: Price is rising (momentum confirmation)
3. **+DI > 25**: Strong bullish directional movement
4. **+DI > -DI**: Bullish direction is dominant

**All four must be true simultaneously** - This conservative approach reduces false signals.

### Entry Example

```
Time: 2025-01-15 14:00
ETH/USDC: $2,450

Indicators:
- ADX: 32 (strong trend ✓)
- MOM: 15.2 (positive ✓)
- +DI: 28 (strong bullish ✓)
- -DI: 12 (+DI > -DI ✓)

→ ENTER LONG at $2,450
```

## Exit Logic

```python
def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['adx'] > 25) &              # Still in trend
            (dataframe['mom'] < 0) &               # Momentum reversed
            (dataframe['minus_di'] > 25) &         # Strong bearish movement
            (dataframe['plus_di'] < dataframe['minus_di'])  # Bears winning
        ),
        'exit_long'] = 1
    return dataframe
```

**Exit strategy:**

**Active exit** (all conditions):
- ADX still > 25 (trend strength maintained)
- MOM < 0 (momentum turned negative)
- -DI > 25 (strong bearish movement)
- -DI > +DI (bearish dominance)

**Why this logic?**
- Waits for confirmed momentum reversal (not just a pullback)
- Requires strong counter-trend to exit
- May hold through minor dips if trend intact

**Passive exits:**
- **ROI target**: 5% profit (from `minimal_roi`)
- **Stoploss**: -25% loss (from `stoploss`)

### Exit Example

```
Time: 2025-01-20 08:00
ETH/USDC: $2,680 (entered at $2,450, +9.4% profit)

Indicators:
- ADX: 30 (still strong ✓)
- MOM: -8.5 (negative ✓)
- +DI: 18
- -DI: 28 (bearish dominance ✓)

→ EXIT LONG at $2,680
→ Profit: $230 (+9.4%)
```

## Running the Strategy

### 1. Download Data

```bash
# Download 3 months of 1h data
make data CONTAINER=adxmomentum_gmx TIMEFRAME=1h TIMERANGE=20250101-20250401
```

### 2. Run Backtest

```bash
# Basic backtest
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401

# Verbose output (see each trade)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401 VERBOSE=-vv
```

### 3. View Results

The backtest will show:
- Total trades executed
- Win rate and profit factor
- Average profit per trade
- Maximum drawdown
- Sharpe ratio

### 4. Generate Equity Curve

```bash
docker-compose run --rm adxmomentum_gmx freqtrade plot-dataframe \
  --strategy ADXMomentum \
  --timerange 20250101-20250401 \
  -p ETH/USDC:USDC \
  --indicators1 adx,plus_di,minus_di \
  --indicators2 mom
```

Then open `user_data/plot/freqtrade-plot-ETH_USDC_USDC-1h.html` in your browser.

## Understanding the Results

### Expected Performance (Trending Markets)

**Good results:**
- Win rate: 40-55%
- Profit factor: > 1.5
- Average trade: > 3-5%
- Max drawdown: < 20%

**Why win rate is lower:**
- Strategy waits for strong confirmation before entering
- Exits on reversal, which means giving back some profit
- Gets stopped out during false breakouts
- **But:** When it wins, it wins big (rides entire trends)

### Interpreting the Indicators

When viewing the plot:

**Look for:**
- **Green entry markers** during rising ADX with +DI > -DI
- **Red exit markers** when -DI crosses above +DI
- **ADX peaks** correlate with trade entries
- **MOM crossing zero** triggers exits

**Pattern recognition:**
```
ADX rising + MOM > 0 = Good entry zone
ADX high + MOM flips negative = Exit signal
ADX falling = Trend weakening, avoid new entries
```

## Optimization Tips

### 1. Adjust ADX Threshold

**More conservative (fewer trades, higher quality):**
```python
(dataframe['adx'] > 30)  # Instead of 25
```

**More aggressive (more trades, may catch weaker trends):**
```python
(dataframe['adx'] > 20)  # Instead of 25
```

**Test different values:**
```bash
# Edit user_data/strategies/ADXMomentum.py
# Change line 39: (dataframe['adx'] > 25) to desired value
# Re-run backtest
```

### 2. Tune DI Threshold

**Stronger trends only:**
```python
(dataframe['plus_di'] > 30)  # Instead of 25
```

**Earlier entries:**
```python
(dataframe['plus_di'] > 20)  # Instead of 25
```

### 3. ROI and Stoploss

**Current settings:**
```python
minimal_roi = {"0": 0.05}  # 5% profit target
stoploss = -0.25           # -25% stop loss
```

**Conservative (take profits faster):**
```python
minimal_roi = {"0": 0.03}  # 3% profit target
stoploss = -0.15           # -15% stop loss
```

**Aggressive (let winners run):**
```python
minimal_roi = {"0": 0.10}  # 10% profit target
stoploss = -0.30           # -30% stop loss
```

### 4. Timeframe Selection

**Current:** 1h (medium-term)

**Try different timeframes:**
```bash
# 4h - longer holds, fewer trades
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=4h

# 15m - shorter holds, more trades (may be too noisy)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=15m
```

**Recommendation:** Stick with 1h or 4h for this strategy. Lower timeframes generate too many false signals.

### 5. Add SAR Confirmation

Enhance entry logic with Parabolic SAR:

```python
def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['adx'] > 25) &
            (dataframe['mom'] > 0) &
            (dataframe['plus_di'] > 25) &
            (dataframe['plus_di'] > dataframe['minus_di']) &
            (dataframe['close'] > dataframe['sar'])  # ← Added SAR confirmation
        ),
        'enter_long'] = 1
    return dataframe
```

This ensures price is above the SAR (uptrend confirmed).

## Common Issues

### Issue: No Trades Generated

**Possible causes:**
1. ADX never exceeds 25 (market too choppy)
2. +DI never exceeds 25 (weak trends)
3. Conditions too strict for the timerange

**Solutions:**
- Try a different date range (look for trending periods)
- Lower ADX threshold to 20
- Check the data with `plot-dataframe` first

### Issue: Too Many Losing Trades

**Possible causes:**
1. Testing in ranging market
2. Timeframe too short (noise)
3. Exit conditions too loose

**Solutions:**
- Increase ADX threshold (30+)
- Use 4h timeframe instead of 1h
- Tighten stop loss
- Add trend filter (e.g., 50-period EMA)

### Issue: Missing Big Moves

**Possible causes:**
1. Entry conditions too strict
2. ROI too low (taking profits early)

**Solutions:**
- Lower +DI threshold (20)
- Increase ROI target (10%)
- Remove or relax one entry condition

## Advanced: Walk-Forward Testing

Test strategy robustness:

```bash
# Period 1: Train
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=20250101-20250201

# Period 2: Test (out-of-sample)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=20250201-20250301

# Period 3: Validate
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMERANGE=20250301-20250401
```

**Good strategy:** Performance consistent across all periods
**Overfit strategy:** Great in Period 1, poor in Periods 2-3

## Complete Strategy Code

```python
# user_data/strategies/ADXMomentum.py
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class ADXMomentum(IStrategy):
    INTERFACE_VERSION: int = 3

    # ROI: Exit at 5% profit
    minimal_roi = {
        "0": 0.05
    }

    # Stoploss: -25%
    stoploss = -0.25

    # Timeframe
    timeframe = '1h'

    # Startup candles
    startup_candle_count: int = 20
    exit_profit_only = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators"""
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=25)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=25)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['mom'] = ta.MOM(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define entry conditions"""
        dataframe.loc[
            (
                (dataframe['adx'] > 25) &              # Strong trend
                (dataframe['mom'] > 0) &               # Positive momentum
                (dataframe['plus_di'] > 25) &          # Bullish strength
                (dataframe['plus_di'] > dataframe['minus_di'])  # Bulls winning
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define exit conditions"""
        dataframe.loc[
            (
                (dataframe['adx'] > 25) &              # Still trending
                (dataframe['mom'] < 0) &               # Momentum reversed
                (dataframe['minus_di'] > 25) &         # Bearish strength
                (dataframe['plus_di'] < dataframe['minus_di'])  # Bears winning
            ),
            'exit_long'] = 1
        return dataframe
```

## Next Steps

1. **Generate equity curves** → [Equity Curves Guide](../equity-curves.md)
2. **Interpret results** → [Interpreting Results](../interpreting-results.md)
3. **Optimize parameters** → Try different ADX/DI thresholds
4. **Compare to other strategies** → Run Simple or Pingpong strategies

## Resources

- [ADX Indicator Explained](https://www.investopedia.com/terms/a/adx.asp)
- [Directional Movement System](https://school.stockcharts.com/doku.php?id=technical_indicators:average_directional_index_adx)
- [TA-Lib Documentation](https://mrjbq7.github.io/ta-lib/func_groups/momentum_indicators.html)
- [Freqtrade Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)
