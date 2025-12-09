# GMX Specifics

Understanding GMX's unique characteristics and how they affect backtesting and trading strategies.

## Table of Contents

- [What is GMX?](#what-is-gmx)
- [Key Differences from Traditional Exchanges](#key-differences-from-traditional-exchanges)
- [Available Data](#available-data)
- [Trading Implications](#trading-implications)
- [How the Integration Works](#how-the-integration-works)

## What is GMX?

[GMX](https://gmx.io) is a decentralized perpetual futures exchange on Arbitrum and Avalanche. Unlike CEXs (Binance) or traditional DEXs (Uniswap), GMX uses a **liquidity pool model** for perpetual trading.

### Key Characteristics

1. **Decentralized & Non-Custodial**
   - On-chain execution via smart contracts
   - No KYC, account registration, or custody
   - Transparent, verifiable

2. **Liquidity Pool Model (V2: GM Pools)**
   - Trades against GM pools with long/short token pairs
   - LPs earn 63% of protocol fees
   - Entry: No price impact (oracle price)
   - Exit: Price impact capped at ~0.5%

3. **Perpetual Futures Only**
   - Up to 100x leverage
   - Hourly funding rates (dynamic)
   - Borrowing fees based on utilization

4. **Supported Chains**
   - **Arbitrum**: Main deployment, lower fees (~$0.10-0.50/trade)
   - **Avalanche**: Faster blocks, higher fees

5. **Available Markets**
   - Major: ETH, BTC, SOL, LINK, ARB
   - Alts: DOGE, XRP, LTC, UNI
   - 15+ perpetual markets

## Key Differences from Traditional Exchanges

Understanding these differences is crucial for building effective GMX strategies.


### 1. No Order Book

**Implications:**
- No order book depth analysis
- No limit orders at specific prices
- No order flow support/resistance
- No front-running/MEV (different model)

**Data unavailable:**
- `fetch_order_book()`, bid/ask spreads, market depth

**Alternatives:**
- Available liquidity → order book depth
- Open interest → market sentiment
- Funding rates → long/short bias

### 2. Atomic Execution

**Characteristics:**
- Single blockchain transaction (all-or-nothing)
- No partial fills or pending orders

**Benefits:**
- Simplified order logic, no timeouts/cancels
- Deterministic execution

**Limitations:**
- Can't scale into positions gradually

### 3. Funding Rates

GMX funding rates work differently than most CEXs:

**GMX Funding:**
- **Hourly calculation**: Funding rates update continuously based on long/short ratio (not fixed 8-hour cycles like CEXs)
- **Borrowing fees**: Hourly cost for leverage based on pool utilization
- **Long/short imbalance**: Affects funding direction
- **Pool based**: Depends on GM pool composition and open interest balance

**Typical rates:**
- Balanced markets: -0.01% to +0.01% per hour
- Imbalanced markets: -0.05% to +0.05% per hour
- Extreme conditions: Can exceed ±0.1% per hour

**Annual funding (approximation):**
```
Annual rate = (hourly rate) × 24 (daily) × 365
Example: 0.01% per hour = 87.6% APR
```

**Note**: Third-party data providers (CoinGlass, Coinalyze) often normalize GMX funding rates to 8-hour periods for comparison with CEXs, but the actual protocol calculates hourly.

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
- **V1 (legacy)**: GLP pools - single liquidity token
- **V2 (current)**: GM pools - individual market pools with long/short token pairs
- GM pools aim to maintain equal worth of long and short tokens
- Traders trade against the pool
- Liquidity providers take opposite side of trades and earn 63% of protocol fees

**Price impact model:**
- **Entry positions**: No price impact - always executed at mark (oracle) price
- **Exit positions**: Price impact applies, typically capped at ~0.5% (50 bps)
- Impact can be positive (favorable) or negative (unfavorable)

**High price impact when:**
- Pool is imbalanced (too many longs or shorts)
- Large position relative to available liquidity
- Extreme market conditions

**Check available liquidity:**
```bash
python -c "
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

**Arbitrum:** $0.10-0.50 (typical), $1-3 (congestion)
**Avalanche:** $0.50-2.00 (higher, more stable)

**Impact:**
- Minimum profit threshold: >$0.50/trade
- High-frequency strategies pay more

**Example:**
```
100 trades @ $0.50 gas = $50 cost
On $1000 stake with 1% avg profit: 5% reduction
```

**Note:** Not auto-included in Freqtrade backtests - account manually.

## Available Data

### Historical OHLCV Data

**Timeframes:** 1m, 5m, 15m, 30m, 1h, 4h, 1d (via GraphQL)

**Data fields:**
```python
{
  "timestamp": 1704067200000,  # Unix timestamp (ms)
  "open": 2250.50,
  "high": 2265.75,
  "low": 2245.20,
  "close": 2260.00,
  "volume": 0                  # ⚠️ Always 0 (not available)
}
```

**⚠️ Volume unavailable - use alternatives:**
```python
# ❌ Won't work
dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)

# ✅ Use open interest or price-based
dataframe['oi_sma'] = ta.SMA(dataframe['open_interest'], timeperiod=20)
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
python -c "
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

GMX uses Chainlink Data Streams for pricing:

**Characteristics:**
- Updates: ~1-5 minutes
- Median of multiple exchanges
- Manipulation-resistant
- May differ from spot

**Implications:**
- Backtest prices = actual execution
- Reduced arbitrage opportunities
- Potential lag during volatility

### Supported Markets

**Major:** ETH/USDC, BTC/USDC (most liquid), SOL/USDC, ARB/USDC, LINK/USDC
**Alts:** DOGE/USDC, XRP/USDC, LTC/USDC, UNI/USDC, AAVE/USDC

**Check current markets:**
```bash
python -c "
from eth_defi.gmx.constants import ARBITRUM_MARKETS
for market in ARBITRUM_MARKETS: print(market)
"
```

## Trading Implications

### Strategy Design Considerations

**1. Funding Cost Awareness**

Factor funding into P&L:
- Short-term strategies (< 1 day holds) - moderate impact
- Medium-term (1-3 days) - significant impact
- Long-term (> 1 week) - very significant impact (can exceed profit)

**Example:**
```
Position: 1 ETH long at $2500, 10x leverage
Holding period: 7 days
Funding rate: 0.01% per hour (87.6% APR)

Daily funding: $2500 × 10x × 0.01% × 24 = $60
Weekly funding: $60 × 7 = $420
Profit needed to break even: 16.8% (on unleveraged position)
```

**Critical**: GMX hourly funding can be 8x more expensive than CEX 8-hour funding for long holds.

**2. Gas Cost Threshold**

Ensure profit > gas costs:
- Minimum profitable trade: $5-10 (on Arbitrum)
- High-frequency strategies need larger edges
- Consider gas in position sizing

**3. Liquidity Constraints**

- Small (< $10k): No issue
- Medium ($10k-$100k): Check liquidity
- Large (> $100k): Split or wait

**4. No Volume Indicators**

**Replacements:**
- Volume SMA → Price SMA / Open Interest
- Volume oscillators → Price oscillators
- Volume breakouts → Price + ATR
- OBV → Accumulation/Distribution


### Fee Structure

**GMX fee tiers (V2):**
- **Balanced pool**: 0.04% entry + 0.04% exit = 0.08% total
- **Imbalanced pool**: 0.06% entry + 0.06% exit = 0.12% total

**Additional costs:**
- **Borrowing fees**: Varies by pool utilization (displayed when opening position)
- **Funding rates**: Dynamic hourly rates based on long/short ratio
- **Gas**: Varies by network congestion (excess refunded)
- **Price impact**: Only on exits, typically capped at ~0.5%

**Total cost example:**
```
Trade: Enter + hold 1 day + exit
Entry fee: 0.06% (imbalanced)
Funding (24h): ~0.24% (0.01%/hour × 24)
Borrowing fees: ~0.48% (varies)
Exit fee: 0.06% (imbalanced)
Gas (2 transactions): $0.50-1.00

Total cost on $10,000 position:
Fees: $84 (0.84%)
Gas: $1.00
Total: $85 (0.85%)

Required profit to break even: 0.85%
```

**N.B.** This is a very abstract overview of the fees & may change. Always use the official documentaion for reference.

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

### Slippage and Price Impact

**Important distinction:**
- **Slippage**: Difference between expected price (when submitted) and actual mark price (when executed) - caused by volatility
- **Price impact**: Applied only to exit/decrease orders, capped at ~0.5%

**Entry positions:**
- No price impact - executed at mark (oracle) price
- Only slippage from volatility during pending execution
- Default allowed slippage: 1% (adjustable)

**Exit positions:**
- Price impact applies (typically ±0.5% cap)
- Can be positive (favorable) or negative (unfavorable)
- Depends on pool balance and position size

**High price impact on exits when:**
- Large position relative to pool liquidity
- Imbalanced pool (too many longs/shorts)
- Extreme market conditions

**Backtest considerations:**
```json
{
  "exchange": {
    "name": "gmx",
    "slippage": 0.01  // Account for entry slippage only (1 basis point)
    // Note: Exit price impact varies and is market-dependent
  }
}
```

## How the Integration Works

### High-Level Architecture

This project integrates GMX into Freqtrade using a **monkeypatch approach**:

```
┌──────────────────────────────────────────────┐
│ Python Execution Environment                 │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │ python -m eth_defi.gmx.freqtrade   │    │
│  │       .patched_entrypoint          │    │
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

**How it works:**

1. Instead of running `freqtrade` directly, you run through the patched entrypoint:
   ```bash
   python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade <command>
   ```

2. The patched entrypoint applies the monkeypatches before Freqtrade starts

3. Freqtrade sees GMX as a native exchange and works transparently

**Convenience alias:**
```bash
alias freqtrade='python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade'
```

This allows you to run commands naturally:
```bash
freqtrade download-data --exchange gmx ...
freqtrade backtesting --strategy Pingpong ...
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
- No need to install dependencies manually
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

1. **Technical details** → [Architecture](architecture.md)
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
