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
   - Alts: DOGE, XRP, LTC, UNI, and many more
   - 95+ perpetual markets

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
# Activate your virtual environment first
source .venv/bin/activate

# Check open interest as proxy for liquidity
python -c "
from eth_defi.gmx.ccxt.exchange import GMX
exchange = GMX()
markets = exchange.load_markets()
print('ETH/USD:USD Market Info:')
market = markets.get('ETH/USD:USD')
if market:
    print(f\"  Contract Size: {market.get('contractSize', 'N/A')}\")
    print(f\"  Max Leverage: {market.get('limits', {}).get('leverage', {}).get('max', 'N/A')}\")
"
```


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

**Current rates only:**
- GMX does not provide historical funding rate data
- Only current/real-time funding rates available
- Rates update hourly based on long/short ratio

**Check current rates:**
- Visit [stats.gmx.io](https://stats.gmx.io/) for real-time funding rates
- Third-party sites ([CoinGlass](https://www.coinglass.com/funding/GMX), [Coinalyze](https://coinalyze.net/gmx/funding-rate/)) track historical rates

**Note:** Without historical funding data, backtests cannot accurately model funding costs. Consider using fixed estimates or external data sources.

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

**Check via GMX Stats:**
- Visit [stats.gmx.io](https://stats.gmx.io/) for real-time open interest data
- Or use the freqtrade-gmx wrapper to fetch market data:

```bash
./freqtrade-gmx test-pairlist \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --quote USDC
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

**95+ perpetual markets** including:
- **Most liquid:** ETH/USDC, BTC/USDC
- **Major:** SOL/USDC, ARB/USDC, LINK/USDC
- **Popular alts:** DOGE/USDC, XRP/USDC, LTC/USDC, UNI/USDC, AAVE/USDC

**List all available markets:**
```bash
# Using freqtrade-gmx
./freqtrade-gmx test-pairlist \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json

# Or check stats.gmx.io for full market list
```


### Fee Structure

**GMX fee tiers (V2):**
- **Balanced pool**: 0.04% entry + 0.04% exit = 0.08% total
- **Imbalanced pool**: 0.06% entry + 0.06% exit = 0.12% total

**Additional costs:**
- **Borrowing fees**: Varies by pool utilization (displayed when opening position)
- **Funding rates**: Dynamic hourly rates based on long/short ratio
- **Gas**: Varies by network congestion (excess refunded)
- **Price impact**: Only on exits, typically capped at ~0.5%


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
│  ┌────────────────────────────────────┐      │
│  │ python -m eth_defi.gmx.freqtrade   │      │
│  │       .patched_entrypoint          │      │
│  │ (runs before Freqtrade starts)     │      │
│  └─────────────┬──────────────────────┘      │ 
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐      │
│  │ CCXT Monkeypatch                   │      │
│  │ - Inject GMX into ccxt.exchanges   │      │
│  │ - Add ccxt.gmx class               │      │
│  │ - Add ccxt.async_support.gmx class │      │
│  └─────────────┬──────────────────────┘      │
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐      │
│  │ Freqtrade Monkeypatch              │      │
│  │ - Add GMX to SUPPORTED_EXCHANGES   │      │
│  │ - Register GMXExchange class       │      │
│  └─────────────┬──────────────────────┘      │
│                │                             │
│                ▼                             │
│  ┌────────────────────────────────────┐      │
│  │ Freqtrade (unmodified)             │      │
│  │ - Sees GMX as native exchange      │      │
│  │ - Uses GMX like Binance/Kraken     │      │
│  └────────────────────────────────────┘      │
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
| Trading fee | 0.04-0.06% (each side, balanced/imbalanced) |
| Funding rate | -0.01% to +0.05% (per hour, dynamic) |
| Borrowing fee | Varies by pool utilization |
| Price impact | Exit only, typically capped at ~0.5% |
| Gas cost | $0.10-0.50 Arbitrum, $0.50-2.00 Avalanche |

### Supported Data

- ✅ OHLCV (1m, 5m, 15m, 1h, 4h, 1d)
- ✅ Open interest (real-time)
- ✅ Current funding rates (real-time only)
- ❌ Historical funding rates (not available from GMX)
- ❌ Volume (not available)
- ❌ Order book (not applicable)

## Resources

- **GMX Documentation**: https://docs.gmx.io
- **GMX Stats**: https://stats.gmx.io
- **web3-ethereum-defi**: https://github.com/tradingstrategy-ai/web3-ethereum-defi
- **Chainlink Oracles**: https://data.chain.link
