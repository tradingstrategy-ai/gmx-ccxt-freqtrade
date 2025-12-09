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

- **Python 3.11+** (for running Freqtrade)
- **uv** (Python package installer - https://docs.astral.sh/uv/)
- **Git** (for cloning and submodule management)
- **10GB+ disk space** (for historical data)
- **Basic command line** knowledge
- **System dependencies** (see below)

Optional:
- Familiarity with Freqtrade
- Docker (if you prefer containerized execution - see bottom of README)

### System Dependencies

**Debian/Ubuntu:**
```bash
# Update repository
sudo apt-get update

# Install packages
sudo apt install -y python3-pip python3-venv python3-dev python3-pandas git curl
```

**macOS:**
```bash
# Install packages
brew install gettext libomp
```

**For other systems or troubleshooting**, see the [official Freqtrade installation requirements](https://www.freqtrade.io/en/stable/installation/#requirements).

## Quick Start (10 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/tradingstrategy-ai/freqtrade-gmx-demo.git
cd freqtrade-gmx-demo

# Initialize web3-ethereum-defi submodule
git submodule update --init --recursive
```

### 2. Install Freqtrade

```bash
# Clone freqtrade repository
# this naming is very important else python will get confused because the freqtrade command and the directory name would be same
git clone https://github.com/freqtrade/freqtrade.git freqtrade-develop

# Create virtual environment in main project directory using uv
uv venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install freqtrade dependencies
uv pip install -r freqtrade-develop/requirements.txt

# Install freqtrade itself (editable mode)
uv pip install -e freqtrade-develop/
```

### 3. Install GMX Integration

```bash
# Install web3-ethereum-defi from local submodule (includes freqtrade integration)
uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"

# Install additional required dependency
uv pip install cchecksum

# Verify installation
./freqtrade-gmx --version
```

**Important Notes:**

- **Why install from local submodule?** The PyPI version of `web3-ethereum-defi` doesn't include the freqtrade integration yet. The freqtrade monkeypatch module only exists in the local `deps/web3-ethereum-defi` directory.

- **Why install `cchecksum` separately?** This is a required dependency for Ethereum address checksumming that isn't automatically installed with the current extras configuration.

- **Why use the `freqtrade-gmx` wrapper script?** Running `python -m eth_defi.gmx.freqtrade.patched_entrypoint` directly from the project directory causes Python import conflicts. Python finds the `freqtrade/` subdirectory as a namespace package instead of the installed freqtrade package, leading to `ImportError: cannot import name '__version__'`. The wrapper script solves this by running from a clean directory (`/tmp`).

**Pro Tip**: The project includes a `freqtrade-gmx` wrapper script that handles the GMX integration:
```bash
# Use the wrapper script directly
./freqtrade-gmx --version
./freqtrade-gmx download-data --exchange gmx --config configs/pingpong_gmx.json ...

# Or add it to your PATH for convenience:
export PATH="$PWD:$PATH"
freqtrade-gmx --version
```

### 4. Download Historical Data

```bash
# Download 1 month of 5m data for backtesting
./freqtrade-gmx download-data \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --exchange gmx \
  --timeframe 5m \
  --timerange 20251128-20251208
```

**Note**: Always pass both config files - the main config and the secrets config.

This fetches GMX market data from GraphQL and stores it locally.

### 5. Run Your First Backtest

```bash
# Backtest the Pingpong strategy
./freqtrade-gmx backtesting \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --strategy Pingpong \
  --timerange 20251128-20251208
```

You should see backtest results with trades, profit, and statistics.

**Next Steps**:
- Quick start with ADX strategy: [docs/QUICKSTART.md](docs/QUICKSTART.md)
- Detailed setup: [docs/getting-started.md](docs/getting-started.md)

## Usage Examples

**Note**: All commands below use the `freqtrade-gmx` wrapper script.

For shorter commands, add it to your PATH:
```bash
export PATH="$PWD:$PATH"
```

Then you can use `freqtrade-gmx` directly instead of `./freqtrade-gmx`.

### Download Data

```bash
# Basic data download
freqtrade-gmx download-data \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --exchange gmx \
  --timeframe 5m \
  --timerange 20251128-20251208 \
  --prepend

# Specific timerange
freqtrade-gmx download-data \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --exchange gmx \
  --timeframe 5m \
  --timerange 20250801-20251001

# Different timeframe (1-minute candles)
freqtrade-gmx download-data \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --exchange gmx \
  --timeframe 1m \
  --timerange 20251101-20251130
```

### Run Backtests

```bash
# Basic backtest
freqtrade-gmx backtesting \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --strategy Pingpong \
  --timerange 20251128-20251208

# With verbose output (-v, -vv, -vvv)
freqtrade-gmx backtesting \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --strategy Pingpong \
  --timerange 20251128-20251208 \
  -vv

# Different strategy with hourly timeframe
freqtrade-gmx backtesting \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --timeframe 1h \
  --timerange 20241128-20251205 \
  -vvv
```

### Generate Visualizations

```bash
# Plot profit/equity curve (interactive HTML)
freqtrade-gmx plot-profit \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json

# Plot with auto-open in browser
freqtrade-gmx plot-profit \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --auto-open

# Plot candlestick charts with entry/exit signals
freqtrade-gmx plot-dataframe \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum

# Plot with specific indicators
freqtrade-gmx plot-dataframe \
  --config configs/adxmomentum_gmx.json \
  --config configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --indicators1 adx plus_di minus_di \
  --indicators2 mom

# Custom Python script (generates PNG images)
source .venv/bin/activate
python scripts/plot_equity.py user_data/backtest_results/backtest-result-*.json
```

**Output locations:**
- Freqtrade plots: `user_data/plot/*.html` (interactive)
- Custom script: `user_data/backtest_results/*.png` (static images)

### Available Strategies

- **Pingpong** (`user_data/strategies/pingpong.py`) - Entry/exit every minute
- **Simple** (`user_data/strategies/Simple.py`) - RSI < 50 entry, RSI > 50 exit
- **ADXMomentum** (`user_data/strategies/ADXMomentum.py`) - ADX + momentum trend following

### Live Trading (Advanced)

```bash
# Dry run mode (paper trading)
freqtrade-gmx trade \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --strategy Pingpong
```

## How It Works

This project uses a transparent monkeypatch approach to integrate GMX into Freqtrade:

1. **web3-ethereum-defi** is installed from the local `deps/` submodule (includes freqtrade integration)
2. **patched_entrypoint** module applies monkeypatch before Freqtrade starts
3. **GMX Exchange class** is registered in both CCXT and Freqtrade
4. **Freqtrade** uses GMX like any other exchange

### The `freqtrade-gmx` Wrapper Script

The project includes a `freqtrade-gmx` bash script that:
- Activates the virtual environment
- Runs freqtrade from a clean directory to avoid Python import conflicts
- Applies the GMX monkeypatch automatically

This wrapper is needed because running `python -m eth_defi.gmx.freqtrade.patched_entrypoint` directly from the project directory causes Python to find the `freqtrade/` subdirectory as a namespace package, leading to import errors.

### The Monkeypatch

The monkeypatch (`python -m eth_defi.gmx.freqtrade.patched_entrypoint`):
- Adds `ccxt.gmx` and `ccxt.async_support.gmx` classes
- Registers GMX in Freqtrade's `SUPPORTED_EXCHANGES`
- Provides CCXT-compatible interface to GMX's on-chain data
- No modifications to Freqtrade or CCXT source code

See [docs/architecture.md](docs/architecture.md) for technical details.

## Configuration Files

Each strategy has its own configuration:

- **Pingpong** → `configs/pingpong_gmx.json`
- **Simple** → `configs/simple_gmx.json`
- **ADXMomentum** → `configs/adxmomentum_gmx.json`
- **Hyperliquid variants** → `configs/*_hyperliquid.json`

Each config references:
- Secrets file (`configs/<name>.secrets.json`) - RPC URLs, private keys (gitignored)
- SQLite database (`db/<name>.sqlite`) - Trade history
- Log file (`user_data/logs/<name>.log`) - Execution logs

## Documentation

### Core Guides
- **[Getting Started](docs/getting-started.md)** - Detailed installation and first backtest
- **[GMX Specifics](docs/gmx-specifics.md)** - Understanding GMX differences
- **[Equity Curves](docs/equity-curves.md)** - Generate and analyze equity curves
- **[Architecture](docs/architecture.md)** - Technical deep dive (developers)
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

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

### Virtual environment issues
```bash
# Ensure venv is activated
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Verify installation
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
```

### No data downloaded
```bash
# Check timerange format (YYYYMMDD-YYYYMMDD)
freqtrade download-data \
  --exchange gmx \
  --config configs/pingpong_gmx.json \
  --timeframe 5m \
  --timerange 20251128-20251208 \
  -vv
```

### GMX exchange not recognized
```bash
# Reinstall web3-ethereum-defi from local submodule
uv pip uninstall web3-ethereum-defi
uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"
uv pip install cchecksum

# Check GMX is available
python -c "import ccxt; print('gmx' in ccxt.exchanges)"
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for more issues and solutions.

## Resources

- **GMX Documentation**: https://docs.gmx.io
- **Freqtrade Documentation**: https://www.freqtrade.io/en/stable/
- **web3-ethereum-defi**: https://github.com/tradingstrategy-ai/web3-ethereum-defi
- **CCXT**: https://docs.ccxt.com/

---

## Alternative: Using Docker (Optional)

If you prefer using Docker containers for isolated environments, you can use the provided Docker setup instead of local Python installation.

### Docker Quick Start

```bash
# Build container
docker-compose build pingpong_gmx

# Download data
make data CONTAINER=pingpong_gmx TIMERANGE=20251128-20251208

# Run backtest
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20251128-20251208

# Generate plots
make plot-profit CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum
make plot-dataframe CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum
```

### Docker Container List

- `pingpong_gmx` - Pingpong strategy on GMX (port 9090)
- `simple_gmx` - Simple strategy on GMX (port 9091)
- `adxmomentum_gmx` - ADX Momentum strategy on GMX (port 9093)
- `pingpong_hyperliquid` - Pingpong strategy on Hyperliquid (port 9090)
- `simple_hyperliquid` - Simple strategy on Hyperliquid (port 9092)

See the `Makefile` for all available Docker commands and parameters.

---

## Acknowledgments

- [Freqtrade](https://github.com/freqtrade/freqtrade) - Algorithmic trading framework
- [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi) - GMX integration layer
- [GMX](https://gmx.io) - Decentralized perpetual exchange
- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency exchange API
