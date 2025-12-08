# Architecture

Technical deep dive into how GMX is integrated with Freqtrade.

## Table of Contents

- [Overview](#overview)
- [The Monkeypatch Approach](#the-monkeypatch-approach)
- [Component Architecture](#component-architecture)
- [CCXT Integration](#ccxt-integration)
- [Freqtrade Integration](#freqtrade-integration)
- [Data Flow](#data-flow)
- [Extending the System](#extending-the-system)

## Overview

This project integrates GMX (a decentralized perpetual exchange) into Freqtrade using a **transparent monkeypatch** approach. The integration happens at runtime without modifying Freqtrade or CCXT source code.

**Key principle:** Make GMX look like a native exchange to Freqtrade.

### Why Monkeypatch?

GMX is not officially supported by:
- **CCXT** - Cryptocurrency exchange library
- **Freqtrade** - Algorithmic trading framework

Instead of forking and maintaining custom versions, we inject GMX support at runtime:
- ✅ No source code modifications
- ✅ Freqtrade can be updated independently
- ✅ Shared integration code via `web3-ethereum-defi`
- ✅ Works with standard Freqtrade strategies

## The Monkeypatch Approach

### High-Level Flow

```
Docker Container Startup
         │
         ▼
┌─────────────────────────────┐
│  patched_entrypoint.py      │  ← Runs BEFORE Freqtrade
│  (Entrypoint override)      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Step 1: CCXT Monkeypatch   │
│  - Register GMX in CCXT     │
│  - Add ccxt.gmx class       │
│  - Add async/sync variants  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Step 2: Freqtrade Patch    │
│  - Register GMX in Freqtrade│
│  - Add to SUPPORTED_EXCHANGES│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Step 3: Start Freqtrade    │
│  - GMX available as exchange│
│  - Works like Binance/Kraken│
└─────────────────────────────┘
```

### Dockerfile Configuration

```dockerfile
FROM freqtradeorg/freqtrade:2025.10

# Install web3-ethereum-defi (contains GMX integration)
COPY deps/web3-ethereum-defi /tmp/web3-ethereum-defi
RUN pip install --user "/tmp/web3-ethereum-defi[web3v7]"

# Override entrypoint with patched version
ENTRYPOINT ["python", "-u", "-B", "-m", "eth_defi.gmx.freqtrade.patched_entrypoint", "freqtrade"]
CMD ["trade"]
```

**Key:** The `ENTRYPOINT` runs the patched entrypoint instead of Freqtrade's default entrypoint.

### Patched Entrypoint

**File:** `eth_defi/gmx/freqtrade/patched_entrypoint.py`

```python
# Simplified version
import sys
from eth_defi.gmx.freqtrade.monkeypatch import apply_freqtrade_monkeypatch

# Apply the monkeypatch BEFORE importing freqtrade
apply_freqtrade_monkeypatch()

# Verify GMX is registered
import ccxt
assert 'gmx' in ccxt.exchanges, "GMX not registered in CCXT!"

# Now start Freqtrade normally
from freqtrade.main import main
sys.exit(main(sys.argv[1:]))
```

**Critical timing:** Must patch **before** Freqtrade imports, as module references are cached.

## Component Architecture

### Layer Architecture

```
┌─────────────────────────────────────────┐
│         Freqtrade (Unmodified)          │
│  - Strategy execution                   │
│  - Order management                     │
│  - Backtesting engine                   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Freqtrade Exchange Layer           │
│  - GMXExchange (custom class)           │
│  - Feature flags                        │
│  - Leverage handling                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         CCXT Compatibility Layer        │
│  - ccxt.gmx (sync)                      │
│  - ccxt.async_support.gmx (async)       │
│  - Standard CCXT interface              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      GMX Protocol (Blockchain)          │
│  - Smart contracts (Arbitrum/Avalanche)│
│  - Liquidity pools (GLP/GM)             │
│  - Chainlink price oracles              │
└─────────────────────────────────────────┘
```

### Directory Structure

```
eth_defi/gmx/
├── freqtrade/
│   ├── patched_entrypoint.py    # Docker entrypoint
│   ├── monkeypatch.py           # Monkeypatch logic
│   └── gmx_exchange.py          # Freqtrade Exchange subclass
│
├── ccxt/
│   ├── exchange.py              # Sync CCXT interface
│   ├── monkeypatch.py           # CCXT patching
│   └── async_support/
│       └── exchange.py          # Async CCXT interface
│
└── core/
    ├── markets.py               # Market enumeration
    ├── open_positions.py        # Position tracking
    ├── funding_fee.py           # Funding calculations
    ├── available_liquidity.py   # Liquidity queries
    └── ...                      # Other GMX modules
```

## CCXT Integration

### GMX as a CCXT Exchange

**File:** `eth_defi/gmx/ccxt/exchange.py`

The GMX class implements the CCXT interface:

```python
class GMX(ccxt.Exchange):
    """CCXT-compatible GMX exchange implementation"""

    def __init__(self, config=None):
        super().__init__(config)

        # Exchange metadata
        self.id = 'gmx'
        self.name = 'GMX'
        self.countries = ['US']  # Decentralized

        # Supported features
        self.has = {
            'fetchMarkets': True,
            'fetchTicker': True,
            'fetchTickers': True,
            'fetchOHLCV': True,
            'fetchTrades': True,
            'fetchBalance': True,
            'fetchOpenOrders': True,
            'fetchMyTrades': True,
            'createOrder': True,
            'fetchPositions': True,
            'fetchFundingRate': True,
            'fetchOpenInterest': True,

            # Not supported on GMX
            'fetchOrderBook': False,  # No order book
            'cancelOrder': False,     # Atomic execution
            'editOrder': False,       # No pending orders
        }

        # Web3 connection
        self.rpc_url = config.get('rpc_url')
        self.private_key = config.get('private_key')
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
```

### Supported CCXT Methods

**Market Data:**
- `fetch_markets()` - Available trading pairs
- `fetch_ticker(symbol)` - Current price, 24h stats
- `fetch_tickers(symbols)` - Batch ticker data
- `fetch_ohlcv(symbol, timeframe)` - Historical candles
- `fetch_trades(symbol, since, limit)` - Recent trades

**Trading:**
- `create_order(symbol, type, side, amount, price)` - Execute market order
- `fetch_balance()` - Account balances
- `fetch_positions(symbols)` - Open positions
- `fetch_open_orders(symbol)` - Open positions as orders
- `fetch_my_trades(symbol, since, limit)` - Trade history

**GMX-Specific:**
- `fetch_funding_rate(symbol)` - Current funding rate
- `fetch_funding_rate_history()` - Historical funding
- `fetch_open_interest(symbol)` - Total open positions
- `fetch_available_liquidity(symbol)` - Pool liquidity

### Async vs Sync

GMX provides both interfaces:

**Sync:** `ccxt.gmx`
```python
import ccxt

exchange = ccxt.gmx({'rpc_url': 'https://arb1.arbitrum.io/rpc'})
markets = exchange.fetch_markets()
```

**Async:** `ccxt.async_support.gmx`
```python
import ccxt.async_support as ccxt
import asyncio

async def main():
    exchange = ccxt.gmx({'rpc_url': 'https://arb1.arbitrum.io/rpc'})
    markets = await exchange.fetch_markets()
    await exchange.close()

asyncio.run(main())
```

Freqtrade uses the async interface internally.

## Freqtrade Integration

### GMXExchange Class

**File:** `eth_defi/gmx/freqtrade/gmx_exchange.py`

```python
from freqtrade.exchange import Exchange

class GMXExchange(Exchange):
    """Freqtrade Exchange subclass for GMX"""

    # Feature flags
    _ft_has = {
        "ohlcv_candle_limit": 10000,
        "mark_ohlcv_timeframe": "1h",
        "funding_fee_timeframe": "8h",
        "stoploss_on_exchange": False,  # Use Freqtrade stoploss
        "order_time_in_force": ["GTC"],  # Good till cancelled
        "ccxt_futures_name": "swap",
    }

    # Supported trading modes
    @property
    def _ft_trading_modes(self):
        return {
            "futures": ["cross", "isolated"]  # Both margin modes
        }

    def get_max_leverage(self, pair: str, stake_amount: float):
        """Get maximum leverage for pair"""
        # GMX supports up to 100x, but varies by market
        market = self.markets.get(pair)
        return market.get('limits', {}).get('leverage', {}).get('max', 50)
```

### Registration in Freqtrade

**File:** `eth_defi/gmx/freqtrade/monkeypatch.py`

```python
def apply_freqtrade_monkeypatch():
    """Register GMX in Freqtrade"""

    # First, apply CCXT monkeypatch
    from eth_defi.gmx.ccxt.monkeypatch import apply_gmx_monkeypatch
    apply_gmx_monkeypatch()

    # Import Freqtrade modules
    from freqtrade import exchange
    from freqtrade.exchange.common import SUPPORTED_EXCHANGES

    # Add GMX to supported exchanges list
    if 'gmx' not in SUPPORTED_EXCHANGES:
        SUPPORTED_EXCHANGES.append('gmx')

    # Register GMXExchange class
    from eth_defi.gmx.freqtrade.gmx_exchange import GMXExchange
    exchange.gmx = GMXExchange  # Lowercase
    exchange.GMX = GMXExchange  # Capitalized
```

After this monkeypatch:
- Freqtrade sees 'gmx' in `SUPPORTED_EXCHANGES`
- Freqtrade can instantiate `GMXExchange`
- All standard features work

## Data Flow

### Backtesting Flow

```
User runs: make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong
         │
         ▼
┌─────────────────────────────┐
│  Docker: pingpong_gmx       │
│  Entrypoint: patched        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Monkeypatch applied        │
│  GMX registered in CCXT +   │
│  Freqtrade                  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Freqtrade Backtesting      │
│  - Loads strategy           │
│  - Loads GMX historical data│
│  - Simulates trades         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  GMX CCXT Interface         │
│  - fetch_ohlcv() for data   │
│  - Returns historical       │
│    candles from GraphQL     │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Results printed            │
│  Saved to backtest_results/ │
└─────────────────────────────┘
```

### Live Trading Flow

```
User runs: docker compose up pingpong_gmx
         │
         ▼
┌─────────────────────────────┐
│  Docker: pingpong_gmx       │
│  Mode: live/dry_run         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Monkeypatch applied        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Freqtrade Live Bot         │
│  - Loads strategy           │
│  - Fetches real-time data   │
│  - Generates signals        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  GMX CCXT Interface         │
│  - fetch_ticker() for price │
│  - create_order() to trade  │
│  - fetch_balance() for funds│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  GMX Smart Contracts        │
│  - Executes on Arbitrum     │
│  - Transaction confirmed    │
└─────────────────────────────┘
```

## Extending the System

### Adding New Strategies

Just create a standard Freqtrade strategy - no GMX-specific code needed:

```python
# user_data/strategies/my_strategy.py
from freqtrade.strategy import IStrategy

class MyStrategy(IStrategy):
    INTERFACE_VERSION = 3

    def populate_indicators(self, dataframe, metadata):
        # Standard indicators work
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        # Standard signal logic
        return dataframe
```

### Accessing GMX-Specific Features

Use the dataframe provider to access GMX data:

```python
class MyStrategy(IStrategy):

    def populate_indicators(self, dataframe, metadata):
        # Get funding rate data (if available)
        pair = metadata['pair']

        # Access via dataframe provider
        if self.dp:
            funding = self.dp.get_pair_dataframe(
                pair=pair,
                timeframe='8h',
                candle_type='funding'
            )

            if not funding.empty:
                dataframe = dataframe.merge(
                    funding[['date', 'funding_rate']],
                    on='date',
                    how='left'
                )

        return dataframe
```

### Contributing to web3-ethereum-defi

The GMX integration lives in `web3-ethereum-defi`. To contribute:

1. Fork the repository
2. Make changes in `eth_defi/gmx/`
3. Add tests
4. Submit pull request

**Common contributions:**
- New GMX markets
- Bug fixes in data fetching
- Performance improvements
- Additional CCXT methods

### Testing Changes Locally

```bash
# Edit files in deps/web3-ethereum-defi/
cd deps/web3-ethereum-defi/
# Make your changes...

# Rebuild Docker with changes
cd ../..
docker-compose build --no-cache pingpong_gmx

# Test
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong
```

## Configuration Deep Dive

### Exchange Configuration

```json
{
  "exchange": {
    "name": "gmx",  // Must be "gmx"
    "rpc_url": "https://arb1.arbitrum.io/rpc",  // RPC endpoint
    "private_key": "0x...",  // For live trading only

    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 500  // 500ms between requests
    },

    "ccxt_async_config": {
      "enableRateLimit": true,
      "rateLimit": 500
    },

    "pair_whitelist": [
      "ETH/USDC:USDC",  // Explicit format
      "BTC/USDC"        // Simplified format (both work)
    ]
  },

  "trading_mode": "futures",  // GMX only supports futures
  "margin_mode": "isolated"   // or "cross"
}
```

### Docker Volumes

```yaml
# docker-compose.yml
services:
  pingpong_gmx:
    volumes:
      - ./user_data:/freqtrade/user_data  # Strategies, data, results
      - ./configs:/freqtrade/configs      # Configuration files
      - ./db:/freqtrade/db                # SQLite databases
```

**Persistence:**
- Historical data: `user_data/data/gmx/`
- Backtest results: `user_data/backtest_results/`
- Trade database: `db/<container>.sqlite`
- Logs: `user_data/logs/<container>.log`

## Security Considerations

### Private Key Handling

**For live trading:**
```json
// configs/pingpong_gmx.secrets.json (gitignored)
{
  "exchange": {
    "private_key": "0xYourPrivateKeyHere"
  }
}
```

**Best practices:**
- Use dedicated trading wallets
- Start with testnet (Arbitrum Sepolia)
- Limit funds in hot wallet
- Never commit secrets to git
- Rotate keys regularly

### RPC Security

**Public RPCs:**
- Fine for backtesting
- May have rate limits
- Not reliable for live trading

**Private RPCs:**
- Use for live trading
- Services: Alchemy, Infura, QuickNode
- Better reliability and rate limits

## Performance Optimization

### Data Caching

Historical data is cached in `user_data/data/gmx/`:
- Re-running backtests uses cached data
- Update with `make data` command
- Delete cache to force refresh

### Parallel Backtesting

Run multiple backtests simultaneously:

```bash
# Terminal 1
make backtest CONTAINER=pingpong_gmx STRATEGY=Strategy1 &

# Terminal 2
make backtest CONTAINER=simple_gmx STRATEGY=Strategy2 &
```

### Memory Usage

For large backtests:
- Limit timerange
- Use higher timeframes (1h vs 1m)
- Reduce `ohlcv_candle_limit` in config

## Troubleshooting

### Monkeypatch Not Applied

**Symptoms:**
```
freqtrade.exceptions.OperationalException: Exchange gmx is not supported
```

**Fix:**
1. Verify Docker entrypoint:
   ```bash
   docker inspect pingpong_gmx | grep Entrypoint
   ```
   Should show: `eth_defi.gmx.freqtrade.patched_entrypoint`

2. Rebuild container:
   ```bash
   docker-compose build --no-cache pingpong_gmx
   ```

### GMX Not in CCXT

**Check:**
```bash
docker-compose run --rm pingpong_gmx python -c "import ccxt; print('gmx' in ccxt.exchanges)"
```

Should print: `True`

### Data Download Issues

**Common causes:**
- GraphQL endpoint down
- Rate limiting
- Invalid timerange

**Debug:**
```bash
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201 VERBOSE=-vvv
```

## Next Steps

- **Troubleshooting** → [Troubleshooting](troubleshooting.md)
- **Getting Started** → [Getting Started](getting-started.md)
- **GMX Specifics** → [GMX Specifics](gmx-specifics.md)

## Resources

- [web3-ethereum-defi Repository](https://github.com/tradingstrategy-ai/web3-ethereum-defi)
- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [CCXT Documentation](https://docs.ccxt.com/)
- [GMX Documentation](https://docs.gmx.io)
