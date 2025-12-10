# GMX Freqtrade and CCXT integration tutorial

This example repository shows how to use [CCXT](https://tradingstrategy.ai/glossary/ccxt)-compatible exchange adapter for [GMX](https://tradingstrategy.ai/glossary/gmx),
a decentralised [perpetual futures](https://tradingstrategy.ai/glossary/gmx) exchange. The adapter is provided by [eth_defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi#make) Python package,
with primitives for RPC, low level smart contract interaction, onchain data ignestion and other.

The adapter is then used with [FreqTrade](https://tradingstrategy.ai/glossary/freqtrade), an [algorithmic trading framework](https://tradingstrategy.ai/glossary/algorithmic-trading) for [Python](https://tradingstrategy.ai/glossary/python) to run an example automated trading strategy on GMX.

**Note**: This is still work-in-progress development. If you intend to use this software check Support section first.

**Note**: As the writing of this, because of GMX's internal limitations, there might not be enough historical data available from GMX historical data REST API endpoint
to perform meaningful trading or backtesting, as the APIs are limited to 10,000 latest candles only.

**Note**: AS the writing of this, `uv` Python package managers has issues and cannot correctly install packages in this tutorial. As a solution,
do not use `uv` or fix the issues with the package manager yourself.

## Key features

- **Historical backtesting** of GMX perpetual strategies
- **CCXT-compatible interface** to GMX's on-chain data
- **Freqtrade integration** via transparent monkeypatch
- **Real market data** from GMX's liquidity pools
- **Multiple timeframes** (1m, 5m, 15m, 1h, 4h, 1d)
- **Funding rate analysis** and position tracking

## Prerequisites

- **Python 3.11+** (not tested with other Python versions)
- **uv**: Python package installer
- **Git**: for cloning and submodule management
- **10GB+ disk space**: historical data, a lot of code to check out
- **System dependencies**: for talib - see below
- **Basic UNIX command line knowledge**

Microsoft Windows users need to use Windows Subsystem for Linux (WSL).

### Included example trading strategies

This example repository comes with few example strategies for FreqTrade.

- [ADX Momentum](./configs/adxmomentum_gmx.json): Multi-indicator trend following: a basic multi-pair strategy to make modest profit in trending cryptocurrency markets
- [Ping pong](./configs/pingpong_gmx.json): Live entry/exit stress testing (1m timeframe): to check that live trading with the connector works and exchange works
- [RSI simple](./configs/simple_gmx.json): RSI-based momentum strategy

All strategies come with

- Python source code for the strategy itself
- Config file for executing against GMX and Hyperliquid to review the adapter functionality side-by-side with a mature CCXT connector
- Example secrets config file

If you want to start building a real trading strategy, ADX momemntum is the best starting point.

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

## Installation

### Clone

```bash
# Submodules most be includedin the checkout
git clone  --recurse-submodules  https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade.git
cd gmx-ccxt-freqtrade
```

### Install Freqtrade

We need to install Freqtrade from a local checkout:

```bash
# Clone freqtrade repository
# this naming is very important else python will get confused because the freqtrade command and the directory name would be same
git clone --branch stable https://github.com/freqtrade/freqtrade.git freqtrade-develop

# Create virtual environment in main project directory using uv
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS

# Install freqtrade dependencies
pip install -r freqtrade-develop/requirements.txt

# Install freqtrade itself (editable mode)
pip install -e freqtrade-develop/
```

### Install CCXT adapter for GMX

The adapter lives in [eth_defi/gmx/ccxt](https://github.com/tradingstrategy-ai/web3-ethereum-defi/tree/master/eth_defi/gmx/ccxt) submodule.
This will add necessary classes to both CCXT and FreqTrade.

The adapter is injected to Python process via [monkey patching](https://en.wikipedia.org/wiki/Monkey_patch). Due to internal Python structure,
we need to use a special wrapper command around `freqtrade` to launch it.

```bash
# Install web3-ethereum-defi from local submodule (includes freqtrade integration).
# TODO: Currently there is an installation issue resolving web3-ethereum-defi dependencies with uv.
python -m pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"
```

Show installed packages:

````bash
pip list|grep -i web3
```

You should see:

```bash
web3                      7.14.0
web3-ethereum-defi        0.35            /Users/moo/code/gmx-ccxt-freqtrade/deps/web3-ethereum-defi
web3-google-hsm           0.1.0
```

### Verify FreqTrade installation

See that we can start `freqtrade` with our GMX monkey patches:

```bash
./freqtrade-gmx --version
````

This should output:

```
Applying GMX monkeypatch to Freqtrade...
Verifying GMX monkeypatch...
  ccxt.async_support.gmx = <class 'eth_defi.gmx.ccxt.async_support.exchange.GMX'>
  Class module: eth_defi.gmx.ccxt.async_support.exchange
  ✓ load_markets is async
GMX support enabled successfully!
Operating System:       macOS-15.6.1-arm64-arm-64bit
Python Version:         Python 3.11.10
CCXT Version:           4.5.20
Freqtrade Version:      freqtrade 2025.11
```

## Backtesting

In this section, we run a strategy backtest to see how FreqTrade strategy would have historically performend on GMX.

**Note**: AS the writing of this, because of GMX's internal limitations, there might not be enough historical data available from GMX historical data REST API endpoint
to perform meaningful trading or backtesting, as the APIs are limited to 10,000 latest candles only.

### Download Historical Data

First we need to download a copy of historicalc GMX data we use for the backtesting.
FreqTrade provides a command for this.

```bash
BACKTEST_TIME_RANGE=20251128-20251208

# 5m data for backtesting
./freqtrade-gmx download-data \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --exchange gmx \
  --timeframe 5m \
  --timerange $BACKTEST_TIME_RANGE
```

**Note**: Always pass both config files - the main config and the secrets config.

This fetches GMX market data from GraphQL and stores it locally.

#### Demo

![](media/download-data.gif)

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

#### Demo

![](media/backtest.gif)

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

TODO: Still under progess.

```bash
# Dry run mode (paper trading)
freqtrade-gmx trade \
  --config configs/pingpong_gmx.json \
  --config configs/pingpong_gmx.secrets.json \
  --strategy Pingpong
```

### The Monkeypatch

The monkeypatch (`python -m eth_defi.gmx.freqtrade.patched_entrypoint`):

- Adds `ccxt.gmx` and `ccxt.async_support.gmx` classes
- Registers GMX in Freqtrade's `SUPPORTED_EXCHANGES`
- Provides CCXT-compatible interface to GMX's on-chain data
- No modifications to Freqtrade or CCXT source code

See [docs/architecture.md](docs/architecture.md) for technical details.

## Configuration Files

Each strategy has its own configuration.

Each config references:

- Secrets file (`configs/<name>.secrets.json`) - RPC URLs, private keys (gitignored)
- SQLite database (`db/<name>.sqlite`) - Trade history
- Log file (`user_data/logs/<name>.log`) - Execution logs
