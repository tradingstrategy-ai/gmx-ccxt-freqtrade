# GMX Specifics

Understanding GMX's unique characteristics and how they affect backtesting and trading strategies.

## Table of Contents

- [What is GMX?](#what-is-gmx)
- [Key Differences from Traditional Exchanges](#key-differences-from-traditional-exchanges)
- [Available Data](#available-data)
- [Trading Implications](#trading-implications)
- [How the Integration Works](#how-the-integration-works)

## What is GMX?

[GMX](https://gmx.io) is a decentralized perpetual futures exchange built on Arbitrum and Avalanche blockchains. Unlike centralized exchanges (CEX) like Binance or traditional decentralized exchanges (DEX) like Uniswap, GMX uses a unique **liquidity pool model** for perpetual futures trading.

### Key Characteristics

1. **Decentralized & Non-Custodial**
   - Trades execute on-chain via smart contracts
   - You control your private keys
   - No KYC or account registration
   - Transparent, verifiable execution

2. **Liquidity Pool Model**
   - Trades against GLP/GM pools (not order books)
   - Liquidity providers earn fees + funding rates
   - Zero price impact within available liquidity
   - Pool composition affects slippage

3. **Perpetual Futures Only**
   - No spot trading
   - Up to 100x leverage (varies by pair)
   - Funding rates every 8 hours
   - Borrowing fees for leverage

4. **Supported Chains**
   - **Arbitrum**: Main deployment, lower fees (~$0.10-0.50 per trade)
   - **Avalanche**: Alternative chain, faster blocks (~2s vs ~0.25s)

5. **Available Markets**
   - Major crypto: ETH, BTC, SOL, LINK, ARB
   - Alts: DOGE, XRP, LTC, UNI
   - Total: 15+ perpetual markets

## Key Differences from Traditional Exchanges

Understanding these differences is crucial for building effective GMX strategies.

### Comparison Table

| Feature | Centralized Exchange (CEX) | GMX |
|---------|---------------------------|-----|
| **Execution** | Order book matching | **Liquidity pool** |
| **Order Book** | Full depth visible | **No order book** |
| **Slippage** | Based on order book depth | **Based on pool liquidity** |
| **Fees** | Maker (0.01-0.1%), Taker (0.02-0.2%) | **Flat 0.04-0.07%** |
| **Funding** | Usually 8h, varies by CEX | **Always 8h cycles** |
| **Latency** | ~50-200ms | **Block time (~0.25s Arbitrum)** |
| **Volume Data** | Real-time tick data | **Not available** |
| **Gas Costs** | None (centralized) | **$0.10-1.00 per transaction** |
| **Privacy** | KYC required | **Wallet only** |
| **Custody** | Exchange holds funds | **Self-custodial** |

### 1. No Order Book

**What this means:**
- Can't analyze order book depth
- Can't place orders at specific price levels
- Can't see support/resistance from order flow
- No front-running or MEV concerns (different model)

**Data not available:**
- `fetch_order_book()` - Not supported
- Bid/ask spreads
- Order book imbalance
- Market depth

**Alternative indicators:**
- Use available liquidity instead of order book depth
- Monitor open interest for market sentiment
- Track funding rates for long/short bias

### 2. Atomic Execution

**What this means:**
- Orders execute in a single blockchain transaction
- Either complete success or complete failure
- No partial fills
- No pending order management

**Benefits:**
- Simplified order logic
- No order timeout handling
- No cancel/replace logic
- Deterministic execution

**Limitations:**
- Can't scale into positions gradually

### 3. Funding Rates

GMX funding rates work differently than most CEXs:

**GMX Funding:**
- **8-hour cycles**: 00:00, 08:00, 16:00 UTC
- **Borrowing fees**: Hourly cost for leverage
- **Long/short imbalance**: Affects funding direction
- **Pool based**: Depends on GLP/GM pool composition

**Typical rates:**
- Balanced markets: -0.01% to +0.01% (per 8h)
- Imbalanced markets: -0.05% to +0.05% (per 8h)
- Extreme conditions: -0.1% to +0.1% (per 8h)

**Annual funding (approximation):**
```
Annual rate = (8h rate) × 3 (daily) × 365
Example: 0.01% per 8h = 10.95% APR
```

**Strategy implications:**
- Long-term positions pay significant funding
- Consider funding in backtest P&L
- Funding can reverse trend profitability
- Short-term strategies less affected

**Freqtrade handling:**
```python
# Funding fees are automatically included in backtests
# Check funding impact:
def custom_stake_amount(self, pair, current_time, ...):
    # Account for funding in position sizing
    funding_cost = self.get_funding_fees(pair, ...)
    return adjusted_stake - funding_cost
```

### 4. Liquidity Pools Instead of Order Books

**How GMX pools work:**
- **GLP (V1)** / **GM (V2)**: Liquidity provider tokens
- Pools contain: 50% stablecoins, 50% crypto assets
- Traders trade against the pool
- LP's take opposite side of trades

**Slippage model:**
```
Price impact = f(trade_size, pool_liquidity, pool_balance)
```

**Zero price impact when:**
- Pool has sufficient liquidity
- Pool balance isn't heavily skewed
- Trade size is small relative to pool

**High price impact when:**
- Pool is imbalanced (too many longs or shorts)
- Large trade relative to available liquidity
- Extreme market conditions

**Check available liquidity:**
```bash
docker-compose run --rm pingpong_gmx python -c "
from eth_defi.gmx.ccxt.exchange import GMX
import asyncio

async def check_liquidity():
    gmx = GMX({'rpc_url': 'https://arb1.arbitrum.io/rpc'})
    liquidity = await gmx.fetch_available_liquidity('ETH/USDC:USDC')
    print(f'ETH/USDC Available Liquidity:')
    print(f'  Long: {liquidity[\"long\"]} ETH')
    print(f'  Short: {liquidity[\"short\"]} USDC')
    await gmx.close()

asyncio.run(check_liquidity())
"
```

### 5. Gas Costs

Every trade incurs blockchain transaction fees:

**Arbitrum (typical):**
- Simple market order: $0.10 - $0.50
- During congestion: $1.00 - $3.00
- Complex operations: $0.50 - $2.00

**Avalanche:**
- Simple market order: $0.50 - $2.00
- Higher than Arbitrum but more stable

**Impact on strategies:**
- High-frequency strategies pay more gas
- Must factor gas into profitability
- Minimum profit threshold: > $0.50 per trade
- Gas costs reduce effective returns

**Example:**
```
Strategy: 100 trades, 1% avg profit, $1000 stake
Profit: $1000 (1% × 100 trades)
Gas costs: $50 (100 trades × $0.50)
Net profit: $950 (5% reduction)
```

**Backtesting note:**
Gas costs are NOT automatically included in Freqtrade backtests. You must account for them manually.

## Available Data

### Historical OHLCV Data

GMX provides candlestick data via GraphQL:

**Timeframes:**
- 1m, 5m, 15m, 30m (intraday)
- 1h, 4h (hourly)
- 1d (daily)

**Data fields:**
```python
{
  "timestamp": 1704067200000,  # Unix timestamp (ms)
  "open": 2250.50,             # Opening price
  "high": 2265.75,             # Highest price
  "low": 2245.20,              # Lowest price
  "close": 2260.00,            # Closing price
  "volume": 0                  # ⚠️ Always 0 (not available)
}
```

**⚠️ Volume data not available:**
- GMX doesn't track volume per candle
- Volume-based indicators won't work
- Use open interest or price-based indicators instead

**Alternatives to volume indicators:**
```python
# ❌ Won't work (no volume)
dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)

# ✅ Use open interest instead
dataframe['oi_sma'] = ta.SMA(dataframe['open_interest'], timeperiod=20)

# ✅ Or price-based indicators
dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
```

### Funding Rates

Historical funding rate data:

**Availability:**
- 8-hour snapshots (00:00, 08:00, 16:00 UTC)
- Historical data since GMX launch (2021)
- Per-market rates

**Usage in strategies:**
```python
def populate_indicators(self, dataframe, metadata):
    # Fetch funding rates (if available)
    funding = self.dp.get_pair_dataframe(
        pair=metadata['pair'],
        timeframe='8h',
        candle_type='funding'
    )

    # Merge with main dataframe
    dataframe = dataframe.merge(
        funding[['date', 'funding_rate']],
        on='date',
        how='left'
    )

    # Avoid high funding cost positions
    dataframe['high_funding'] = dataframe['funding_rate'] > 0.05

    return dataframe
```

### Open Interest

Track total open positions:

**Data points:**
- Total long positions (USD)
- Total short positions (USD)
- Long/short ratio
- Historical trends

**Use cases:**
- Sentiment analysis (more longs = bullish sentiment)
- Contrarian signals (extreme OI = reversal?)
- Liquidity assessment (high OI = more liquidity)

**Example:**
```bash
docker-compose run --rm pingpong_gmx python -c "
from eth_defi.gmx.open_interest import fetch_open_interest
import asyncio

async def show_oi():
    oi = await fetch_open_interest('ETH/USDC', chain='arbitrum')
    print(f'ETH/USDC Open Interest:')
    print(f'  Total Long: ${oi[\"total_long\"]:,.0f}')
    print(f'  Total Short: ${oi[\"total_short\"]:,.0f}')
    print(f'  Ratio: {oi[\"long_short_ratio\"]:.2f}')

asyncio.run(show_oi())
"
```

### Price Oracle

GMX uses Chainlink oracles for pricing:

**Characteristics:**
- Updated every ~1-5 minutes
- Median of multiple exchanges
- Protection against manipulation
- May differ from spot prices

**Implications:**
- Backtest prices match actual execution
- Less arbitrage opportunity
- Oracle lag during volatility

### Supported Markets

As of 2025, GMX supports:

**Major markets:**
- ETH/USDC (most liquid)
- BTC/USDC (most liquid)
- SOL/USDC
- ARB/USDC
- LINK/USDC

**Alt markets:**
- DOGE/USDC
- XRP/USDC
- LTC/USDC
- UNI/USDC
- AAVE/USDC

**Check current markets:**
```bash
docker-compose run --rm pingpong_gmx python -c "
from eth_defi.gmx.constants import ARBITRUM_MARKETS
print('GMX Arbitrum Markets:')
for market in ARBITRUM_MARKETS:
    print(f'  - {market}')
"
```

## Trading Implications

### Strategy Design Considerations

**1. Funding Cost Awareness**

Factor funding into P&L:
- Short-term strategies (< 8h holds) - minimal impact
- Medium-term (1-3 days) - moderate impact (0.03-0.15%)
- Long-term (> 1 week) - significant impact (0.5-2%)

**Example:**
```
Position: 1 ETH long at $2500, 10x leverage
Holding period: 7 days
Funding rate: 0.01% per 8h (3% APR)

Daily funding: $2500 × 10x × 0.01% × 3 = $7.50
Weekly funding: $7.50 × 7 = $52.50
Profit needed to break even: 2.1% (on unleveraged position)
```

**2. Gas Cost Threshold**

Ensure profit > gas costs:
- Minimum profitable trade: $5-10 (on Arbitrum)
- High-frequency strategies need larger edges
- Consider gas in position sizing

**3. Liquidity Constraints**

Check pool liquidity before large trades:
- Small positions (< $10k): Usually no issue
- Medium positions ($10k-$100k): Check available liquidity
- Large positions (> $100k): May need to split or wait

**4. No Volume Indicators**

Replace volume-based analysis:
- Volume SMA → Price SMA or Open Interest
- Volume oscillators → Price oscillators
- Volume breakouts → Price + ATR breakouts
- OBV → Accumulation/Distribution on price

### Latency Expectations

**Block time = execution delay**

**Arbitrum:**
- Block time: ~0.25 seconds
- Total execution: 0.5-2 seconds
- Finality: ~10 minutes (L1 confirmation)

**Avalanche:**
- Block time: ~2 seconds
- Total execution: 3-5 seconds
- Finality: 2-3 seconds

**Implications:**
- Can't front-run millisecond movements
- Strategies should work on minute+ timeframes
- Signals have 0.5-2s execution lag
- Acceptable for most crypto strategies

### Fee Structure

**GMX fee tiers:**
- **Balanced pool**: 0.04% entry + 0.04% exit = 0.08% total
- **Imbalanced pool**: 0.06% entry + 0.06% exit = 0.12% total
- **Extreme imbalance**: Up to 0.07% each side = 0.14% total

**Additional costs:**
- **Borrowing fees**: ~0.01-0.05% per hour (varies by leverage)
- **Funding rates**: -0.05% to +0.05% per 8h
- **Gas**: $0.10-0.50 per transaction

**Total cost example:**
```
Trade: Enter + hold 1 day + exit
Entry fee: 0.05%
Funding (3 × 8h): 0.03%
Borrowing (24h × 0.02%/h): 0.48%
Exit fee: 0.05%
Gas (2 transactions): $1.00

Total cost on $10,000 position:
Fees: $61 (0.61%)
Gas: $1.00
Total: $62 (0.62%)

Required profit to break even: 0.62%
```

**Compare to CEX:**
```
Binance Futures (example):
Entry fee: 0.02% (maker) or 0.04% (taker)
Funding (3 × 8h): ~0.01%
Exit fee: 0.02% (maker) or 0.04% (taker)

Total (maker): ~0.05%
Total (taker): ~0.09%
```

GMX fees are higher than CEX maker fees but competitive with taker fees.

### Slippage Behavior

**GMX slippage model:**
```
Slippage = f(position_size, available_liquidity, pool_balance)
```

**Low slippage scenarios:**
- Small positions (< 0.1% of pool)
- Balanced pool composition
- High available liquidity

**High slippage scenarios:**
- Large positions (> 1% of pool)
- Imbalanced pool (too many longs/shorts)
- Low liquidity periods

**Estimate slippage:**
```python
def estimate_slippage(position_size_usd, available_liquidity_usd):
    """
    Rough slippage estimate for GMX
    """
    size_ratio = position_size_usd / available_liquidity_usd

    if size_ratio < 0.001:  # < 0.1% of liquidity
        return 0.01  # ~1 basis point
    elif size_ratio < 0.01:  # 0.1-1% of liquidity
        return 0.05  # ~5 basis points
    elif size_ratio < 0.05:  # 1-5% of liquidity
        return 0.20  # ~20 basis points
    else:  # > 5% of liquidity
        return 1.00  # ~100 basis points (avoid!)
```

**Backtest slippage:**
```json
{
  "exchange": {
    "name": "gmx",
    "slippage": 0.05  // 5 basis points = 0.05%
  }
}
```

## How the Integration Works

### High-Level Architecture

This project integrates GMX into Freqtrade using a **monkeypatch approach**:

```
┌──────────────────────────────────────────────┐
│ Docker Container                             │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │ patched_entrypoint.py              │    │
│  │ (runs before Freqtrade starts)     │    │
│  └─────────────┬──────────────────────┘    │
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐    │
│  │ CCXT Monkeypatch                   │    │
│  │ - Inject GMX into ccxt.exchanges   │    │
│  │ - Add ccxt.gmx class               │    │
│  │ - Add ccxt.async_support.gmx class │    │
│  └─────────────┬──────────────────────┘    │
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐    │
│  │ Freqtrade Monkeypatch              │    │
│  │ - Add GMX to SUPPORTED_EXCHANGES   │    │
│  │ - Register GMXExchange class       │    │
│  └─────────────┬──────────────────────┘    │
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐    │
│  │ Freqtrade (unmodified)             │    │
│  │ - Sees GMX as native exchange      │    │
│  │ - Uses GMX like Binance/Kraken     │    │
│  └────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

### Web3-Ethereum-DeFi Module

The GMX integration lives in the `web3-ethereum-defi` library:

**Key components:**
- `eth_defi/gmx/ccxt/exchange.py` - CCXT-compatible GMX class
- `eth_defi/gmx/freqtrade/gmx_exchange.py` - Freqtrade Exchange subclass
- `eth_defi/gmx/freqtrade/monkeypatch.py` - Monkeypatch logic
- `eth_defi/gmx/core/` - Core GMX data modules

**Why submodule?**
- Shared across multiple projects
- Active development and maintenance
- Comprehensive GMX functionality
- Tested and production-ready

### CCXT Compatibility Layer

GMX implements the CCXT interface:

**Supported methods:**
- `fetch_markets()` - Available trading pairs
- `fetch_ticker(symbol)` - Current price + 24h stats
- `fetch_ohlcv(symbol, timeframe)` - Historical candles
- `fetch_funding_rate(symbol)` - Current funding
- `fetch_open_interest(symbol)` - Total open positions
- `create_order(symbol, type, side, amount)` - Execute trade
- `fetch_balance()` - Account balance
- `fetch_positions(symbols)` - Open positions

**Unsupported methods:**
- `fetch_order_book()` - No order book on GMX
- `cancel_order()` - Orders execute atomically
- `edit_order()` - No pending orders to edit

**See full API:** [Architecture](architecture.md)

### Transparent to Freqtrade

Once the monkeypatch is applied:
- Freqtrade sees GMX as a native exchange
- All existing features work (backtesting, strategies, etc.)
- No modifications to Freqtrade source code
- Freqtrade can be updated independently

**User experience:**
```python
# In your strategy, this works exactly the same as Binance:
from freqtrade.strategy import IStrategy

class MyStrategy(IStrategy):
    def populate_entry_trend(self, dataframe, metadata):
        # Works identically on GMX, Binance, Kraken, etc.
        dataframe.loc[(dataframe['rsi'] < 30), 'enter_long'] = 1
        return dataframe
```

### Technical Deep Dive

For developers who want to understand or extend the integration:
→ See [Architecture](architecture.md)

## Next Steps

Now that you understand GMX's unique characteristics:

1. **Analyze results** → [Interpreting Results](interpreting-results.md)
   - Factor in GMX-specific costs
   - Evaluate funding impact
   - Optimize for gas efficiency

2. **Technical details** → [Architecture](architecture.md)
   - Understand the monkeypatch
   - Explore CCXT integration
   - Extend functionality

## Quick Reference

### GMX Limitations

- ❌ No order book
- ❌ No volume data

### GMX Advantages

- ✅ Decentralized & non-custodial
- ✅ Zero price impact (within limits)
- ✅ Up to 100x leverage
- ✅ Transparent on-chain execution
- ✅ No KYC required

### Cost Summary

| Cost Type | Amount |
|-----------|--------|
| Trading fee | 0.04-0.07% (each side) |
| Funding rate | -0.05% to +0.05% (per 8h) |
| Borrowing fee | 0.01-0.05% (per hour) |
| Gas cost | $0.10-0.50 (per transaction) |

### Supported Data

- ✅ OHLCV (1m, 5m, 15m, 1h, 4h, 1d)
- ✅ Funding rates (8h snapshots)
- ✅ Open interest (real-time)
- ✅ Available liquidity
- ❌ Volume (not available)
- ❌ Order book (not applicable)

## Resources

- **GMX Documentation**: https://docs.gmx.io
- **GMX Stats**: https://stats.gmx.io
- **web3-ethereum-defi**: https://github.com/tradingstrategy-ai/web3-ethereum-defi
- **Chainlink Oracles**: https://data.chain.link
