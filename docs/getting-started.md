# Getting Started

Complete guide to installing the GMX Freqtrade setup and running your first backtest using Python and uv.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Your First Backtest](#your-first-backtest)
- [Configuration Basics](#configuration-basics)
- [Next Steps](#next-steps)

## Prerequisites

### Required Software

1. **Python 3.11+**
   - Check your version:
     ```bash
     python3 --version  # Should be 3.11 or higher
     ```
   - Install if needed:
     - Mac: `brew install python@3.11`
     - Ubuntu/Debian: `sudo apt install python3.11`
     - Windows: Download from https://www.python.org/downloads/

2. **uv (Python Package Installer)**
   - Install uv:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - Or via pip:
     ```bash
     pip install uv
     ```
   - Documentation: https://docs.astral.sh/uv/

3. **Git**
   - Mac: Pre-installed or via Homebrew (`brew install git`)
   - Linux: `sudo apt install git` or `sudo yum install git`
   - Windows: https://git-scm.com/download/win
   - Verify installation:
     ```bash
     git --version  # Should be 2.30+
     ```

4. **System Dependencies**

   **Debian/Ubuntu:**
   ```bash
   sudo apt-get update
   sudo apt install -y python3-pip python3-venv python3-dev python3-pandas git curl
   ```

   **macOS:**
   ```bash
   brew install gettext libomp
   ```

   **For other systems**, see [Freqtrade installation requirements](https://www.freqtrade.io/en/stable/installation/#requirements).

5. **Disk Space**
   - Minimum: 5GB (Freqtrade + minimal data)
   - Recommended: 10GB+ (multiple strategies and historical data)
   - Check available space:
     ```bash
     df -h .  # Linux/Mac
     ```

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **OS**: Linux, macOS, or Windows with WSL2
- **Internet**: Required for downloading data and packages

### Optional

- **Code Editor**: VS Code, PyCharm, or similar
- **Docker**: If you prefer containerized execution (see bottom of README)

## Installation

### Step 1: Clone the Repositories

```bash
# Clone the GMX demo project
git clone https://github.com/yourusername/freqtrade-gmx-demo.git
cd freqtrade-gmx-demo

# Verify you're in the right directory
ls -la
# You should see: Dockerfile, docker-compose.yml, Makefile, configs/, deps/, etc.

# Initialize web3-ethereum-defi submodule (GMX integration)
git submodule update --init --recursive

# Verify submodule is loaded
ls deps/web3-ethereum-defi/
# You should see Python files and directories
```

**Troubleshooting submodule**: If deps/web3-ethereum-defi/ is empty:
```bash
# Force reinitialize
git submodule deinit -f deps/web3-ethereum-defi
git submodule update --init --recursive
```

### Step 2: Clone Freqtrade

```bash
# Clone freqtrade repository
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# Verify freqtrade is cloned
ls -la
# You should see: freqtrade/, requirements.txt, setup.py, etc.
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment using uv (fast!)
uv venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS

# On Windows, use:
# .venv\Scripts\activate

# Verify venv is activated (prompt should show (.venv))
which python
# Should show: /path/to/freqtrade/.venv/bin/python
```

**Note**: Always activate your venv before running freqtrade commands.

### Step 4: Install Freqtrade

```bash
# Upgrade pip (recommended)
python3 -m pip install --upgrade pip

# Install freqtrade dependencies
python3 -m pip install -r requirements.txt

# Install freqtrade in editable mode
python3 -m pip install -e .

# Verify freqtrade is installed
freqtrade --version
```

**Expected output:**
```
freqtrade 2025.10
```

**Troubleshooting**: If installation fails:
- Ensure system dependencies are installed (see Prerequisites)
- Check Python version: `python3 --version` (must be 3.11+)
- Try: `python3 -m pip install --upgrade setuptools wheel`

### Step 5: Install GMX Integration

```bash
# Return to project directory
cd ..  # Back to freqtrade-gmx-demo/

# Ensure venv is still activated
source freqtrade/.venv/bin/activate

# Install web3-ethereum-defi with GMX support
python3 -m pip install -e deps/web3-ethereum-defi[web3v7]
```

**What this installs:**
- web3-ethereum-defi core library
- GMX-specific modules
- Web3 v7 dependencies
- CCXT and Freqtrade monkeypatch code

### Step 6: Set Up Shell Alias

For convenience, add this alias to your shell profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
echo "alias freqtrade='python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade'" >> ~/.bashrc

# Reload shell configuration
source ~/.bashrc  # or source ~/.zshrc
```

Now you can use `freqtrade` instead of the full command.

### Step 7: Verify Installation

Check that GMX is registered as an exchange:

```bash
# Test GMX registration
python -c "import ccxt; print('GMX registered:', 'gmx' in ccxt.exchanges)"
```

**Expected output:**
```
GMX registered: True
```

If you see `False`, troubleshoot:
1. Verify submodule: `ls deps/web3-ethereum-defi/eth_defi/gmx/`
2. Reinstall: `python3 -m pip install -e deps/web3-ethereum-defi[web3v7] --force-reinstall`
3. Check venv is activated: `which python`

**Test the full command:**
```bash
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
```

**Expected output:**
```
freqtrade 2025.10
```

## Your First Backtest

Let's backtest the **Pingpong** strategy on GMX using historical data.

**Note**: Ensure your virtual environment is activated before running these commands:
```bash
source freqtrade/.venv/bin/activate  # From freqtrade-gmx-demo directory
```

### Step 1: Download Historical Data

Download 1 month of 5-minute candle data:

```bash
# Download January 2025 data (assuming you set up the alias)
freqtrade download-data \
  --exchange gmx \
  --config configs/pingpong_gmx.json \
  --timeframe 5m \
  --timerange 20250101-20250201

# Or without alias, use the full command:
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade download-data \
  --exchange gmx \
  --config configs/pingpong_gmx.json \
  --timeframe 5m \
  --timerange 20250101-20250201
```

**What this does:**
- Fetches OHLCV data from GMX's GraphQL API
- Stores data in `user_data/data/gmx/`
- Downloads for pairs in `configs/pingpong_gmx.json` (ETH/USDC by default)
- Uses 5m timeframe as specified

**Expected output:**
```
2025-01-01 00:00:00 - freqtrade.data.history.history_utils - INFO - Downloading pair ETH/USDC:USDC, interval 5m
2025-01-01 00:00:00 - freqtrade.data.history.history_utils - INFO - Downloaded data for ETH/USDC:USDC from 2025-01-01 to 2025-02-01
```

**Add verbosity for more details:**
```bash
# Basic progress
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timeframe 5m --timerange 20250101-20250201 -v

# Detailed progress
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timeframe 5m --timerange 20250101-20250201 -vv

# Debug information
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timeframe 5m --timerange 20250101-20250201 -vvv
```

**Data location:**
```bash
# View downloaded data
ls user_data/data/gmx/
# Should show: ETH_USDC-5m.json (or similar)

# Check data size
du -h user_data/data/gmx/
```

**Troubleshooting - No data downloaded:**
- Check internet connection
- Verify timerange format (YYYYMMDD-YYYYMMDD)
- Try different timerange (GMX launched in 2021)
- Ensure venv is activated: `which python`
- Check GraphQL endpoint is accessible

### Step 2: Run the Backtest

Backtest the Pingpong strategy using the downloaded data:

```bash
# Run backtest for January 2025
freqtrade backtesting \
  --strategy Pingpong \
  --config configs/pingpong_gmx.json \
  --timerange 20250101-20250201

# With verbose output
freqtrade backtesting \
  --strategy Pingpong \
  --config configs/pingpong_gmx.json \
  --timerange 20250101-20250201 \
  -vv
```

**What this does:**
- Loads historical data from `user_data/data/gmx/`
- Simulates trades using `user_data/strategies/pingpong.py`
- Applies GMX-specific constraints (funding fees, market orders)
- Generates backtest results

**Expected duration:** 30 seconds to 2 minutes (depends on data size)

**Expected output:**

```py
                                                BACKTESTING REPORT
┏━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃          Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ETH/USDC:USDC │   2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
│         TOTAL │   2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
└───────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                                         LEFT OPEN TRADES REPORT
┏━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ TOTAL │      0 │          0.0 │           0.000 │          0.0 │         0:00 │    0     0     0     0 │
└───────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                                                ENTER TAG STATS
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Enter Tag ┃ Entries ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│     OTHER │    2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
│     TOTAL │    2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
└───────────┴─────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                                                 EXIT REASON STATS
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ one_minute_exit │  2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
│           TOTAL │  2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
└─────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                                                        MIXED TAG STATS
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Enter Tag ┃     Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│           │ one_minute_exit │   2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
│     TOTAL │                 │   2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │
└───────────┴─────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                         SUMMARY METRICS
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2025-12-01 12:19:00            │
│ Backtesting to                │ 2025-12-05 00:00:00            │
│ Trading Mode                  │ Isolated Futures               │
│ Max open trades               │ 1                              │
│                               │                                │
│ Total/Daily Avg Trades        │ 2510 / 836.67                  │
│ Starting balance              │ 100 USDC                       │
│ Final balance                 │ 55.334 USDC                    │
│ Absolute profit               │ -44.666 USDC                   │
│ Total profit %                │ -44.67%                        │
│ CAGR %                        │ -100.00%                       │
│ Sortino                       │ -24037.87                      │
│ Sharpe                        │ -18729.53                      │
│ Calmar                        │ -636.83                        │
│ SQN                           │ -58.69                         │
│ Profit factor                 │ 0.06                           │
│ Expectancy (Ratio)            │ -0.02 (-0.87)                  │
│ Avg. daily profit             │ -14.889 USDC                   │
│ Avg. stake amount             │ 15 USDC                        │
│ Total trade volume            │ 75345.619 USDC                 │
│                               │                                │
│ Best Pair                     │ ETH/USDC:USDC -44.67%          │
│ Worst Pair                    │ ETH/USDC:USDC -44.67%          │
│ Best trade                    │ ETH/USDC:USDC 0.73%            │
│ Worst trade                   │ ETH/USDC:USDC -0.80%           │
│ Best day                      │ -6.42 USDC                     │
│ Worst day                     │ -13.274 USDC                   │
│ Days win/draw/lose            │ 0 / 0 / 4                      │
│ Min/Max/Avg. Duration Winners │ 0d 00:01 / 0d 00:01 / 0d 00:01 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:01 / 0d 00:01 / 0d 00:01 │
│ Max Consecutive Wins / Loss   │ 4 / 128                        │
│ Rejected Entry signals        │ 0                              │
│ Entry/Exit Timeouts           │ 0 / 0                          │
│                               │                                │
│ Min balance                   │ 55.334 USDC                    │
│ Max balance                   │ 99.976 USDC                    │
│ Max % of account underwater   │ 44.67%                         │
│ Absolute drawdown             │ 44.666 USDC (44.67%)           │
│ Drawdown duration             │ 3 days 11:38:00                │
│ Profit at drawdown start      │ -0.024 USDC                    │
│ Profit at drawdown end        │ -44.666 USDC                   │
│ Drawdown start                │ 2025-12-01 12:21:00            │
│ Drawdown end                  │ 2025-12-04 23:59:00            │
│ Market change                 │ 11.14%                         │
└───────────────────────────────┴────────────────────────────────┘

Backtested 2025-12-01 12:19:00 -> 2025-12-05 00:00:00 | Max open trades : 1
                                                         STRATEGY SUMMARY
┏━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃            Drawdown ┃
┡━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Pingpong │   2510 │        -0.12 │         -44.666 │       -44.67 │      0:01:00 │  202     0  2308   8.0 │ 44.666 USDC  44.67% │
└──────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┴─────────────────────┘
```

**Result Files:**

Backtest results are saved to `user_data/backtest_results/`:

```bash
# List recent backtests
ls -lht user_data/backtest_results/ | head -5

# View detailed results JSON
cat user_data/backtest_results/backtest-result-2025-12-08_*.json | jq
```

Each backtest creates:
- `.json` - Detailed trade list
- `.meta.json` - Metadata and settings

### Step 3: Iterate and Experiment

Try different parameters:

```bash
# 1. Different timerange (November 2024)
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20241101-20241201

# 2. Different strategy (Simple RSI)
make backtest CONTAINER=simple_gmx STRATEGY=Simple TIMERANGE=20250101-20250201

# 3. Different timeframe (1-hour candles)
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250201

# 4. Verbose output for debugging
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong VERBOSE=-vvv
```

**Common experiments:**
- Test different date ranges (bull market vs bear market)
- Compare strategies on the same data
- Adjust stake amount in config
- Modify strategy parameters

## Configuration Basics

### Configuration File Structure

Each container has two configuration files:

1. **Main config** (`configs/<container>.json`) - Strategy settings
2. **Secrets file** (`configs/<container>.secrets.json`) - RPC URL, private keys

Example: `configs/pingpong_gmx.json`

```json
{
  "max_open_trades": 1,
  "stake_currency": "USDC",
  "stake_amount": 1000,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "USD",
  "dry_run": true,
  "cancel_open_orders_on_exit": false,

  "exchange": {
    "name": "gmx",
    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 500
    },
    "ccxt_async_config": {
      "enableRateLimit": true,
      "rateLimit": 500
    },
    "pair_whitelist": [
      "ETH/USDC:USDC"
    ],
    "pair_blacklist": []
  },

  "entry_pricing": {
    "price_side": "same",
    "use_order_book": false,
    "order_book_top": 1,
    "check_depth_of_market": {
      "enabled": false
    }
  },

  "exit_pricing": {
    "price_side": "same",
    "use_order_book": false
  },

  "trading_mode": "futures",
  "margin_mode": "isolated",

  "pairlists": [
    {"method": "StaticPairList"}
  ]
}
```

### GMX-Specific Settings

**Required settings:**

```json
{
  "exchange": {
    "name": "gmx",  // Must be "gmx"
  },
  "trading_mode": "futures",  // GMX only supports futures
  "margin_mode": "isolated"   // or "cross"
}
```

**Pair format:**

GMX accepts both formats:
```json
"pair_whitelist": [
  "ETH/USDC:USDC",  // Explicit contract format
  "ETH/USDC",       // Simplified format
  "BTC/USDC:USDC",
  "ARB/USDC:USDC"
]
```

**Rate limiting:**

GMX uses GraphQL and RPC endpoints - respect rate limits:
```json
{
  "ccxt_config": {
    "enableRateLimit": true,
    "rateLimit": 500  // 500ms between requests
  }
}
```

### Secrets File Setup

Create `configs/<container>.secrets.json` for RPC URL and keys:

```bash
# Copy example file
cp configs/file.secrets.example.json configs/pingpong_gmx.secrets.json
```

**For backtesting (dry run):**

```json
{
  "exchange": {
    "rpc_url": "https://arb1.arbitrum.io/rpc"
  },
  "dry_run": true,
  "dry_run_wallet": 10000
}
```

Public RPC endpoints:
- Arbitrum: `https://arb1.arbitrum.io/rpc`
- Avalanche: `https://api.avax.network/ext/bc/C/rpc`

**For live trading (advanced):**

```json
{
  "exchange": {
    "rpc_url": "https://your-rpc-endpoint.com",
    "private_key": "0xYourPrivateKeyHere"
  },
  "dry_run": false
}
```

**Security notes:**
- Never commit `*.secrets.json` files (they're in `.gitignore`)
- Use dedicated wallets for trading
- Test on testnet first
- Start with small amounts

### Pair Selection

Available GMX pairs (Arbitrum):
- ETH/USDC
- BTC/USDC
- ARB/USDC
- LINK/USDC
- SOL/USDC
- DOGE/USDC
- And more...

Check available pairs:
```bash
docker-compose run --rm pingpong_gmx python -c "
from eth_defi.gmx.constants import ARBITRUM_MARKETS
print('Available GMX pairs:')
for market in ARBITRUM_MARKETS:
    print(f'- {market}')
"
```

### Stake Amount Configuration

Configure position sizing:

```json
{
  "stake_amount": 1000,         // Fixed 1000 USDC per trade
  "stake_amount": "unlimited",  // All available balance
  "stake_amount": 0.1,          // 10% of balance (0.1 = 10%)
}
```

**Best practices:**
- Start with fixed amounts (easier to backtest)
- Use percentage for live trading
- Never stake more than you can afford to lose
- Account for funding fees (reduces available balance)

### Leverage Configuration

Set leverage per pair:

```json
{
  "exchange": {
    "name": "gmx",
    "leverage_tiers": {
      "ETH/USDC:USDC": 5.0,  // 5x leverage
      "BTC/USDC:USDC": 3.0   // 3x leverage
    }
  }
}
```

**GMX leverage limits:**
- Max: Up to 100x (varies by pair and liquidity)
- Default: 50x
- Recommended: 3-10x for backtesting
- Higher leverage = higher liquidation risk

## Common Issues and Fixes

### Issue: Submodule not initialized

```bash
Error: deps/web3-ethereum-defi/ is empty
```

**Fix:**
```bash
git submodule update --init --recursive
ls deps/web3-ethereum-defi/  # Should show files
```

### Issue: Docker build fails

```bash
Error: failed to solve with frontend dockerfile.v0
```

**Fix:**
```bash
# Clean rebuild
docker-compose build --no-cache pingpong_gmx

# Check Docker daemon is running
docker info
```

### Issue: No data downloaded

```bash
WARNING - No data found for pair ETH/USDC
```

**Fixes:**
1. Check timerange format (YYYYMMDD-YYYYMMDD)
2. Try different timerange (GMX launched in 2021)
3. Verify internet connection
4. Check pair is in config `pair_whitelist`

```bash
# Debug download
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201 VERBOSE=-vvv
```

### Issue: GMX exchange not recognized

```bash
freqtrade.exceptions.OperationalException: Exchange gmx is not supported
```

**Fixes:**
1. Verify Docker entrypoint:
   ```bash
   grep ENTRYPOINT Dockerfile
   # Should show: eth_defi.gmx.freqtrade.patched_entrypoint
   ```

2. Rebuild container:
   ```bash
   docker-compose build --no-cache pingpong_gmx
   ```

3. Check GMX registration:
   ```bash
   docker-compose run --rm pingpong_gmx python -c "import ccxt; print('gmx' in ccxt.exchanges)"
   ```

### Issue: Backtest shows no trades

```bash
No trades found in backtest results
```

**Fixes:**
1. Check strategy logic (indicators may never trigger)
2. Verify data is downloaded for timerange
3. Try different timerange (more volatile periods)
4. Check strategy's `minimal_roi` and `stoploss` settings

```bash
# Debug strategy
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong VERBOSE=-vvv
```

For more issues, see [Troubleshooting](troubleshooting.md).

## Next Steps

Now that you have a working setup:

1. **Understand GMX differences** → [GMX Specifics](gmx-specifics.md)
   - Learn how GMX differs from traditional exchanges
   - Understand funding fees and liquidity pools

2. **Technical deep dive** → [Architecture](architecture.md)
   - Understand the monkeypatch approach
   - Explore CCXT integration
   - Extend the system

## Quick Reference

### Common Commands

```bash
# Download data
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201

# Backtest
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20250101-20250201

# Backtest with verbose output
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong VERBOSE=-vv

# Different timeframe
make data CONTAINER=pingpong_gmx TIMEFRAME=1h
make backtest CONTAINER=pingpong_gmx STRATEGY=ADXMomentum TIMEFRAME=1h

# Live trading (dry run)
docker-compose up pingpong_gmx
```

### File Locations

- Strategies: `user_data/strategies/`
- Data: `user_data/data/gmx/`
- Backtest results: `user_data/backtest_results/`
- Logs: `user_data/logs/`
- Configs: `configs/`
- Secrets: `configs/*.secrets.json`

### Available Strategies

- **Pingpong**: `user_data/strategies/pingpong.py`
- **Simple**: `user_data/strategies/Simple.py`
- **ADXMomentum**: `user_data/strategies/ADXMomentum.py`

### Support Resources

- [Freqtrade Docs](https://www.freqtrade.io/en/stable/)
- [GMX Docs](https://docs.gmx.io)
- [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi)
- [Troubleshooting](troubleshooting.md)
