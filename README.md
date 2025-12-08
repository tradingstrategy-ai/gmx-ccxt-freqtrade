# GMX Freqtrade Backtesting

Backtest trading strategies on [GMX](https://gmx.io) perpetual futures using [Freqtrade](https://www.freqtrade.io/). This project enables historical strategy analysis on GMX's decentralized perpetual exchange without risking capital.

## Why This Project?

GMX is a decentralized perpetual futures exchange on Arbitrum and Avalanche, but it's not officially supported by Freqtrade or CCXT. This project bridges that gap using [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi) to provide:

- **Historical backtesting** of GMX perpetual strategies
- **CCXT-compatible interface** to GMX's on-chain data
- **Freqtrade integration** via transparent monkeypatch
- **Real market data** from GMX's liquidity pools
- **Multiple timeframes** (1m, 5m, 15m, 1h, 4h, 1d)
- **Funding rate analysis** and position tracking

Perfect for traders and quants who want to validate GMX strategies before deploying capital.

## Key Features

### GMX-Specific Capabilities
- Access GMX perpetual markets (ETH, BTC, ARB, and more)
- Historical OHLCV data via GraphQL
- Funding rate tracking (8-hour cycles)
- Open interest analysis
- Isolated and cross margin support
- Up to 100x leverage backtesting

### Freqtrade Integration
- Full IStrategy v3 interface support
- All standard Freqtrade indicators (TA-Lib)
- Custom exit logic and hooks
- ROI and stoploss configuration
- Strategy optimization (hyperopt compatible)
- Dry-run and live trading modes

### Included Strategies
- **Pingpong**: Rapid entry/exit testing (1m timeframe)
- **Simple**: RSI-based momentum strategy
- **ADXMomentum**: Multi-indicator trend following

## Prerequisites

- **Docker** and **docker-compose** (for containerized execution)
- **Git** (for cloning and submodule management)
- **10GB+ disk space** (for historical data)
- **Basic command line** knowledge

Optional for development:
- Python 3.11+
- Familiarity with Freqtrade

## Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/freqtrade-gmx-demo.git
cd freqtrade-gmx-demo

# Initialize web3-ethereum-defi submodule
git submodule update --init --recursive
```

### 2. Build Docker Container

```bash
# Build the GMX-enabled freqtrade container
docker-compose build pingpong_gmx
```

This installs `web3-ethereum-defi` and applies the GMX monkeypatch to Freqtrade.

### 3. Download Historical Data

```bash
# Download 1 month of 5m data for backtesting
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201
```

This fetches GMX market data from GraphQL and stores it locally.

### 4. Run Your First Backtest

```bash
# Backtest the Pingpong strategy
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20250101-20250201
```

You should see backtest results with trades, profit, and statistics.

**Next Steps**: Check [docs/getting-started.md](docs/getting-started.md) for detailed installation and configuration.

## Usage Examples

### Download Data

```bash
# Download with default timerange (from Makefile)
make data CONTAINER=pingpong_gmx

# Specific timerange
make data CONTAINER=pingpong_gmx TIMERANGE=20250801-20251001

# Different timeframe
make data CONTAINER=pingpong_gmx TIMEFRAME=1m TIMERANGE=20251101-20251130
```

### Run Backtests

```bash
# Basic backtest
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong

# With timerange
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20250801-20251001

# With verbose output (-v, -vv, -vvv)
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong VERBOSE=-vv

# Different strategy and timeframe
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h VERBOSE=-vvv
```

### Available Strategies

- **Pingpong** (`user_data/strategies/pingpong.py`) - Entry/exit every minute
- **Simple** (`user_data/strategies/Simple.py`) - RSI < 50 entry, RSI > 50 exit
- **ADXMomentum** (`user_data/strategies/ADXMomentum.py`) - ADX + momentum trend following

### Live Trading (Advanced)

```bash
# Dry run mode (paper trading)
docker compose up pingpong_gmx

# Requires setting up configs/pingpong_gmx.secrets.json with RPC URL
# See docs/getting-started.md for configuration details
```

## How It Works

This project uses a transparent monkeypatch approach to integrate GMX into Freqtrade:

1. **web3-ethereum-defi** is installed as a git submodule
2. **patched_entrypoint.py** applies monkeypatch before Freqtrade starts
3. **GMX Exchange class** is registered in both CCXT and Freqtrade
4. **Freqtrade** uses GMX like any other exchange

The monkeypatch:
- Adds `ccxt.gmx` and `ccxt.async_support.gmx` classes
- Registers GMX in Freqtrade's `SUPPORTED_EXCHANGES`
- Provides CCXT-compatible interface to GMX's on-chain data
- No modifications to Freqtrade or CCXT source code

See [docs/architecture.md](docs/architecture.md) for technical details.

## Available Containers

| Container | Strategy | Exchange | Port |
|-----------|----------|----------|------|
| pingpong_gmx | Pingpong | GMX | 9090 |
| simple_gmx | Simple | GMX | 9091 |
| adxmomentum_gmx | ADXMomentum | GMX | 9093 |
| pingpong_hyperliquid | Pingpong | Hyperliquid | 9090 |
| simple_hyperliquid | Simple | Hyperliquid | 9092 |

Each container has its own:
- Configuration file (`configs/<container>.json`)
- Secrets file (`configs/<container>.secrets.json`)
- SQLite database (`db/<container>.sqlite`)
- Log file (`user_data/logs/<container>.log`)

## Documentation

- **[Getting Started](docs/getting-started.md)** - Detailed installation and first backtest
- **[GMX Specifics](docs/gmx-specifics.md)** - Understanding GMX differences
- **[Interpreting Results](docs/interpreting-results.md)** - Analyzing backtest output
- **[Architecture](docs/architecture.md)** - Technical deep dive (developers)
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

### Examples & Tutorials
- [Basic RSI Strategy](docs/examples/basic-rsi-strategy.md)
- [Multi-Indicator Strategy](docs/examples/multi-indicator-strategy.md)
- [Funding Rate Analysis](docs/examples/funding-rate-analysis.md)
- [Strategy Optimization](docs/examples/strategy-optimization.md)

## Project Structure

```
freqtrade-gmx-demo/
├── configs/               # Freqtrade configuration files
│   ├── pingpong_gmx.json
│   ├── simple_gmx.json
│   └── *.secrets.json     # RPC URLs, private keys (gitignored)
├── deps/
│   └── web3-ethereum-defi/  # GMX integration (git submodule)
├── docs/                  # Documentation
├── user_data/
│   ├── strategies/        # Trading strategies
│   ├── data/             # Historical OHLCV data
│   └── backtest_results/ # Backtest outputs
├── Dockerfile            # Container with GMX monkeypatch
├── docker-compose.yml    # Service definitions
└── Makefile             # Common commands
```

## Security

### For Backtesting (Dry Run)
- No private keys needed
- Uses public RPC endpoints
- Safe to experiment

### For Live Trading
- **Never commit private keys** to git
- Store keys in `*.secrets.json` files (gitignored)
- **Test on testnet first** (GMX supports Arbitrum Sepolia)
- Use dedicated trading wallets
- Understand gas costs and slippage
- Start with small position sizes

### Configuration Security
- All `*.secrets.json` files are in `.gitignore`
- Use environment variables for sensitive data
- Never share RPC URLs with rate limits
- Rotate private keys regularly

## Contributing

Contributions welcome! Areas of interest:

- **New strategies**: Add to `user_data/strategies/`
- **Documentation improvements**: Fix typos, add examples
- **Bug fixes**: Issues in monkeypatch or configuration
- **Testing**: More backtest examples and edge cases

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

For GMX integration improvements, contribute to [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi).

## Troubleshooting

### Container won't build
```bash
# Clean rebuild
docker-compose build --no-cache pingpong_gmx
```

### No data downloaded
```bash
# Check timerange format (YYYYMMDD-YYYYMMDD)
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201 VERBOSE=-vv
```

### GMX exchange not recognized
```bash
# Verify submodule initialized
git submodule update --init --recursive

# Check Docker entrypoint
docker-compose run pingpong_gmx python -c "import ccxt; print('gmx' in ccxt.exchanges)"
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for more issues and solutions.

## Resources

- **GMX Documentation**: https://docs.gmx.io
- **Freqtrade Documentation**: https://www.freqtrade.io/en/stable/
- **web3-ethereum-defi**: https://github.com/tradingstrategy-ai/web3-ethereum-defi
- **CCXT**: https://docs.ccxt.com/

## License

[Your License Here]

## Acknowledgments

- [Freqtrade](https://github.com/freqtrade/freqtrade) - Algorithmic trading framework
- [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi) - GMX integration layer
- [GMX](https://gmx.io) - Decentralized perpetual exchange
- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency exchange API
