# GMX, CCXT and FreqTrade algorithmic trading tutorial

This example repository shows how to use [CCXT](https://tradingstrategy.ai/glossary/ccxt)-compatible exchange adapter for [GMX](https://tradingstrategy.ai/glossary/gmx),
a decentralised [perpetual futures](https://tradingstrategy.ai/glossary/gmx) exchange.

The CCXT-compatible adapter is used with [FreqTrade](https://tradingstrategy.ai/glossary/freqtrade), an [algorithmic trading framework](https://tradingstrategy.ai/glossary/algorithmic-trading) for [Python](https://tradingstrategy.ai/glossary/python) to run an example automated trading strategy on GMX.

![alt text](docs/screenshot.png)

The example provide a handful of FreqTrade strategy modules and configs to get started.

<!-- TOC START -->
## Table of Contents

- [Overview](#overview)
  - [Key features](#key-features)
  - [Why GMX?](#why-gmx)
  - [How does it work?](#how-does-it-work)
  - [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [System Dependencies](#system-dependencies)
    - [Debian/Ubuntu/Windows Subsytem for Linux](#debianubuntuwindows-subsytem-for-linux)
    - [macOS](#macos)
    - [Clone the repository](#clone-the-repository)
  - [Install Freqtrade](#install-freqtrade)
  - [Install CCXT adapter for GMX](#install-ccxt-adapter-for-gmx)
  - [Verify FreqTrade installation](#verify-freqtrade-installation)
- [Backtesting](#backtesting)
    - [Download Historical Data](#download-historical-data)
    - [Run backtest](#run-backtest)
    - [Equity curve](#equity-curve)
    - [Entries and exists](#entries-and-exists)
- [Live trading](#live-trading)
  - [Creating a private key and funding](#creating-a-private-key-and-funding)
  - [RPC provider](#rpc-provider)
  - [Secrets management](#secrets-management)
  - [Starting FreqTrade in live trading](#starting-freqtrade-in-live-trading)
- [FreqUI](#frequi)
- [Stale positions](#stale-positions)
- [Fees and tokens](#fees-and-tokens)
  - [Trading fees](#trading-fees)
  - [Gas and execution buffer](#gas-and-execution-buffer)
- [How GMX is enabled in CCXT and FreqTrade via monkey patch](#how-gmx-is-enabled-in-ccxt-and-freqtrade-via-monkey-patch)
- [Next steps](#next-steps)
- [Support](#support)
  - [Social media](#social-media)
- [License](#license)

<!-- TOC END -->

# Overview

## Key features

- **CCXT-compatible interface** to GMX's onchain trading
- **FreqTrade-compatible** run our trading algorithms on deep GMX liquidity
- **Backtest** with historical GMX data

**Note**: This is still work-in-progress development. If you intend to use this software check Support section first.

## Why GMX?

GMX's unique [AMM](https://tradingstrategy.ai/glossary/amm) offers benefits for traders

- Deep liquidity
- Self custodial, transparent, less conterparty risk
- Pure onchain, composable with DeFi strategies and smart contracts
- Onchain data and execution availability ensures robust, self-hosted, API access

## How does it work?

Python package [web3-ethereum-defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi) includes
GMX-specific CCXT adapter code and monkey-patches to FreqTrade, so that you can run strategies by choosing `gmx` exchange type

The adapter is provided by [eth_defi](https://github.com/tradingstrategy-ai/web3-ethereum-defi#make) Python package, which provides necessary low-level primitives for RPC, smart contract interaction, onchain data ignestion. These are mapped to CCXT/FreqTrade transparently, so that you need a minimum modifications to your algorithsm to make them run onchain.

## Prerequisites

To run this tutorial

- **Python 3.12 only+** (see [web3-ethereum-defi README](https://github.com/tradingstrategy-ai/web3-ethereum-defi) for the status of Python version compatibility)
- **Git**: for cloning and submodule management
- **10GB+ disk space**: historical data, a lot of code to check out
- **System dependencies**: for talib - see below
- **Basic UNIX command line knowledge**

Microsoft Windows users need to use Windows Subsystem for Linux (WSL).

If you want to start building a real trading strategy, ADX momemntum is the best starting point.

# Installation

## System Dependencies

We recommend [pyenv](https://github.com/pyenv/pyenv) to install Python 3.12 or a specific Python version.

### Debian/Ubuntu/Windows Subsytem for Linux

```bash
# Update repository
sudo apt-get update

# Install packages
sudo apt install -y python3-pip python3-venv python3-dev python3-pandas git curl
```

### macOS

```bash
# Install packages
brew install gettext libomp
```

**For other systems or troubleshooting**, see the [official Freqtrade installation requirements](https://www.freqtrade.io/en/stable/installation/#requirements).

### Clone the repository

```bash
# Submodules most be includedin the checkout
git clone  --recurse-submodules  https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade.git
cd gmx-ccxt-freqtrade
git submodule update --remote --merge
```

## Install Freqtrade

We need to install Freqtrade from a local checkout:

```bash
# Clone freqtrade repository
# this naming is very important else python will get confused because the freqtrade command and the directory name would be same
git clone --depth 1 --branch stable https://github.com/freqtrade/freqtrade.git freqtrade-develop

# Create virtual environment in main project directory using uv
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS

# Install freqtrade dependencies
pip install -r freqtrade-develop/requirements.txt

# Install freqtrade itself (editable mode)
pip install -e freqtrade-develop/
```

## Install CCXT adapter for GMX

The adapter lives in [eth_defi/gmx/ccxt](https://github.com/tradingstrategy-ai/web3-ethereum-defi/tree/master/eth_defi/gmx/ccxt) submodule.
This will add necessary classes to both CCXT and FreqTrade.

The adapter is injected to Python process via [monkey patching](https://en.wikipedia.org/wiki/Monkey_patch). Due to internal Python structure,
we need to use a special wrapper command around `freqtrade` to launch it.

```bash
# Install web3-ethereum-defi from local submodule (includes freqtrade integration).
# TODO: Currently there is an installation issue resolving web3-ethereum-defi dependencies with uv.
pip install "web3-ethereum-defi[data,ccxt]"
```

Show installed packages:

```bash
pip list|grep -i web3
```

You should see web3-ethereum-defi package which provides CCXT and FreqTrade monkey patches:

```bash
web3                      7.14.0
web3-ethereum-defi        0.35            /Users/moo/code/gmx-ccxt-freqtrade/deps/web3-ethereum-defi
```

## Verify FreqTrade installation

We run freqtrade using our [freqtrade-gmx wrapper command](./freqtrade-gmx).

See that we can start `freqtrade` with our GMX monkey patches:

```bash
./freqtrade-gmx --version
```

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

# Backtesting

In this section, we run a strategy [backtest](https://tradingstrategy.ai/glossary/backtest) to see how FreqTrade strategy would have historically performend on GMX.

For a backtest you need

- [A FreqTrade strategy module](./user_data/strategies/) that describes the strategy lofic
- [A FreqTrade config](./configs/) that describes the exchange we connect to
- Exchange API keys needed to download [historical data](https://tradingstrategy.ai/glossary/historical-market-data) (GMX doesn't need this as APIs are public)

**Note**: Because of GMX's internal limitations, the GMX historical data REST API only serves approximately 4,320 candles (about 6 months of 1h data). This means you must choose a time range within the last ~6 months for backtesting to work. The exact available range shifts forward over time. If you get `InsufficientHistoricalDataError`, adjust your start date to be more recent.

Here we backtest [ADX momentum strategy](./configs/adxmomentum_gmx.json).

- Trades majors: BTC, SOL, DOGE, ETH
- Uses 1h timeframe

### Download Historical Data

First we need to download a copy of historicalc GMX data we use for the backtesting.
FreqTrade provides a command for this.
This fetches GMX market data from GMX GraphQL endpoint and stores it locally.

Choose a time range within the last ~6 months. For example, if today is February 2026:

```bash
BACKTEST_TIME_RANGE=20250901-20260201

./freqtrade-gmx download-data \
  --config configs/adxmomentum_gmx.json \
  --config configs/secrets.empty.json \
  --exchange gmx \
  --timeframe 1h \
  --timerange $BACKTEST_TIME_RANGE
```

Example output:

```
2025-12-10 12:20:51,030 - freqtrade.data.history.history_utils - INFO - Download history data for "ETH/USDC:USDC", 1h, index and store in /Users/moo/code/gmx-ccxt-freqtrade/user_data/data/gmx. From 2025-12-10T09:00:00 to
2025-12-08T00:00:00
2025-12-10 12:20:51,033 - freqtrade.data.history.history_utils - INFO - Downloaded data for ETH/USDC:USDC with length 0.
Timeframe                 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3 100% • 0:00:01 • 0:00:00
Downloading ETH/USDC:USDC ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4/4 100% • 0:00:01 • 0:00:00
2025-12-10 12:20:51,111 - eth_defi.gmx.ccxt.async_support.exchange - INFO - Async GMX exchange session closed
```

### Run backtest

```bash
# Backtest the ADX momentum strategy
./freqtrade-gmx backtesting \
  --config configs/adxmomentum_gmx.json \
  --config configs/secrets.empty.json \
  --strategy ADXMomentum \
  --timerange $BACKTEST_TIME_RANGE
```

You should see backtest results with trades, profit, and statistics:

```
                                                  BACKTESTING REPORT
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃           Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ DOGE/USDC:USDC │     17 │         2.31 │           5.894 │         5.89 │  1 day, 10:39:00 │   12     0     5  70.6 │
│  SOL/USDC:USDC │     27 │         0.93 │           3.751 │         3.75 │  1 day, 23:00:00 │   16     0    11  59.3 │
│  ETH/USDC:USDC │     20 │         0.38 │           1.143 │         1.14 │  1 day, 18:57:00 │   10     0    10  50.0 │
│  BTC/USDC:USDC │     15 │         0.34 │           0.773 │         0.77 │ 2 days, 22:24:00 │    5     0    10  33.3 │
│          TOTAL │     79 │         0.97 │          11.560 │        11.56 │  1 day, 23:46:00 │   43     0    36  54.4 │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                         LEFT OPEN TRADES REPORT
┏━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ TOTAL │      0 │          0.0 │           0.000 │          0.0 │         0:00 │    0     0     0     0 │
└───────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┘
                                                 ENTER TAG STATS
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Enter Tag ┃ Entries ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│     OTHER │      79 │         0.97 │          11.560 │        11.56 │ 1 day, 23:46:00 │   43     0    36  54.4 │
│     TOTAL │      79 │         0.97 │          11.560 │        11.56 │ 1 day, 23:46:00 │   43     0    36  54.4 │
└───────────┴─────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┘
                                                EXIT REASON STATS
┏━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│         roi │    42 │          5.0 │          31.500 │         31.5 │ 1 day, 20:23:00 │   42     0     0   100 │
│ exit_signal │    37 │        -3.59 │         -19.939 │       -19.94 │ 2 days, 3:36:00 │    1     0    36   2.7 │
│       TOTAL │    79 │         0.97 │          11.560 │        11.56 │ 1 day, 23:46:00 │   43     0    36  54.4 │
└─────────────┴───────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┘
                                                        MIXED TAG STATS
┏━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Enter Tag ┃ Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│           │         roi │     42 │          5.0 │          31.500 │         31.5 │ 1 day, 20:23:00 │   42     0     0   100 │
│           │ exit_signal │     37 │        -3.59 │         -19.939 │       -19.94 │ 2 days, 3:36:00 │    1     0    36   2.7 │
│     TOTAL │             │     79 │         0.97 │          11.560 │        11.56 │ 1 day, 23:46:00 │   43     0    36  54.4 │
└───────────┴─────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┘
                          SUMMARY METRICS
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2025-07-01 20:00:00             │
│ Backtesting to                │ 2025-12-08 00:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 2                               │
│                               │                                 │
│ Total/Daily Avg Trades        │ 79 / 0.5                        │
│ Starting balance              │ 100 USDC                        │
│ Final balance                 │ 111.56 USDC                     │
│ Absolute profit               │ 11.56 USDC                      │
│ Total profit %                │ 11.56%                          │
│ CAGR %                        │ 28.55%                          │
│ Sortino                       │ 4.32                            │
│ Sharpe                        │ 2.04                            │
│ Calmar                        │ 20.46                           │
│ SQN                           │ 1.89                            │
│ Profit factor                 │ 1.58                            │
│ Expectancy (Ratio)            │ 0.15 (0.26)                     │
│ Avg. daily profit             │ 0.073 USDC                      │
│ Avg. stake amount             │ 15 USDC                         │
│ Total trade volume            │ 2384.405 USDC                   │
│                               │                                 │
│ Best Pair                     │ DOGE/USDC:USDC 5.89%            │
│ Worst Pair                    │ BTC/USDC:USDC 0.77%             │
│ Best trade                    │ SOL/USDC:USDC 5.00%             │
│ Worst trade                   │ SOL/USDC:USDC -9.68%            │
│ Best day                      │ 2.25 USDC                       │
│ Worst day                     │ -1.837 USDC                     │
│ Days win/draw/lose            │ 28 / 100 / 27                   │
│ Min/Max/Avg. Duration Winners │ 0d 00:00 / 12d 07:00 / 1d 20:14 │
│ Min/Max/Avg. Duration Losers  │ 0d 10:00 / 9d 12:00 / 2d 03:58  │
│ Max Consecutive Wins / Loss   │ 11 / 8                          │
│ Rejected Entry signals        │ 898                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 99.533 USDC                     │
│ Max balance                   │ 119.053 USDC                    │
│ Max % of account underwater   │ 6.79%                           │
│ Absolute drawdown             │ 8.082 USDC (6.79%)              │
│ Drawdown duration             │ 48 days 07:00:00                │
│ Profit at drawdown start      │ 19.053 USDC                     │
│ Profit at drawdown end        │ 10.971 USDC                     │
│ Drawdown start                │ 2025-10-13 19:00:00             │
│ Drawdown end                  │ 2025-12-01 02:00:00             │
│ Market change                 │ -2.70%                          │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2025-07-01 20:00:00 -> 2025-12-08 00:00:00 | Max open trades : 2
                                                           STRATEGY SUMMARY
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃    Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDC ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃          Drawdown ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ ADXMomentum │     79 │         0.97 │          11.560 │        11.56 │ 1 day, 23:46:00 │   43     0    36  54.4 │ 8.082 USDC  6.79% │
└─────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴───────────────────┘
2025-12-10 13:01:36,182 - eth_defi.gmx.ccxt.async_support.exchange - INFO - Async GMX exchange session closed
```

### Equity curve

You can view the equity curve chart of the backtest results with:

```bash
./freqtrade-gmx plot-profit \
  --config configs/adxmomentum_gmx.json \
  --config configs/secrets.empty.json \
  --auto-open
```

![Indicator plot](./docs/equity-curve.png)

### Entries and exists

You can view the entries/exits chart of the strategy with.
This will render the chart and open a new browser window to display it:

```bash
./freqtrade-gmx plot-dataframe \
  --config configs/adxmomentum_gmx.json \
  --config configs/secrets.empty.json \
  --strategy ADXMomentum \
  --indicators1 adx plus_di minus_di \
  --indicators2 mom

open user_data/plot/freqtrade-plot-ETH_USDC_USDC-1h.html
```

![Indicator plot](./docs/plot-indicators.png)

# Live trading

For live trading you are going to need

- USDC on Arbitrum (native variant) as collateral.
- ETH for gas fees

## Creating a private key and funding

To to start trading we need a funded wallet on Arbitrum.

Create a new private key on a command line:

```shell
python -c "from web3 import Web3; w3 = Web3(); acc = w3.eth.account.create(); print(f'private key={w3.to_hex(acc._private_key)}, account={acc.address}')"
```

You will get output like:

```
private key=<...>, account=0x881B099b365d7B6F92B2Adf18732470AcBBebBE5
```

Import private key in your wallet like Rabby.

Fund it with WETH and USDC on Arbitrum.

Then you can set this as an environment variable:

```shell
export GMX_PRIVATE_KEY=<...>
```

The private key must be `0x` prefixed.

## RPC provider

We need to use multiple RPC providers with Arbitrum, with the Arbitrum specific sequencer being the [MEV-resistant centralised sequencer](https://ethereum.stackexchange.com/questions/162207/how-to-broadcast-a-transaction-directly-to-a-centralised-sequencer-arbitrum-opt) for broadcasting our transactions.

You also need a high quality commercial RPC provider for JSON-RPC chain reads, as free providers are too flaky and likely to crash your trading in few transactions. You also likely want to configure at least two read providers to ensure that the FreqTrade does not crash if one of them gets flaky.

Set them as a space separated list:

```shell
export JSON_RPC_ARBITRUM="mev+https://arb1-sequencer.arbitrum.io/rpc <your providert 1> <your provider 2>"
```

Some providers to try

- dRPC
- Alchemy
- Quicknode

## Secrets management

We pass secrets to FreqTrade via a separate config file that lives outside the repository, so we minimise the risk of exposing our secrets. We use [.config directory in user home](https://unix.stackexchange.com/questions/126603/is-there-a-standards-specified-location-for-user-configuration-files).

We also set a username/password for localhost web UI: [freq-ui](https://www.freqtrade.io/en/stable/freq-ui/).

Generate `~/.config/freqtrade.secrets.json` from the environment variables set above:

```shell
jq -n \
  --arg rpcUrl "$JSON_RPC_ARBITRUM" \
  --arg privateKey "$GMX_PRIVATE_KEY" \
  '{
    exchange: {ccxt_config: {rpcUrl: $rpcUrl, privateKey: $privateKey}},
    api_server: {
      enabled: true,
      listen_ip_address: "127.0.0.1",
      listen_port: 8080,
      username: "tradingstrategy.ai",
      password: "tradingstrategy.ai"
    }
  }' \
  > ~/.config/freqtrade.secrets.json

echo "Secret config is:"
cat ~/.config/freqtrade.secrets.json
```

## Starting FreqTrade in live trading

We do a trading test using a ping pong strategy that opens and closes positions on both long and short side to see the trading works. Ping pong opens a long position in one cycle (candle) and closes it in the next. [See Pingpong.py here](./user_data/strategies/pingpong.py). Ping pong uses 5m candles, so it opens a position in 5 minutes and then closes it in 5 minutes.

The startup is coming to take a minute or so.

```sh
./freqtrade-gmx trade \
  --strategy Pingpong \
  --config configs/pingpong_gmx.json \
  --config ~/.config/freqtrade.secrets.json \
  --log-file freqtrade.logs
```

You should see output:

```
pplying GMX monkeypatch to Freqtrade...
Verifying GMX monkeypatch...
  ccxt.async_support.gmx = <class 'eth_defi.gmx.ccxt.async_support.exchange.GMX'>
  Class module: eth_defi.gmx.ccxt.async_support.exchange
  ✓ load_markets is async
GMX support enabled successfully!
2026-02-12 14:20:02,314 - freqtrade - INFO - freqtrade 2026.1
2026-02-12 14:20:02,555 - freqtrade.worker - INFO - Starting worker 2026.1
2026-02-12 14:20:02,555 - freqtrade.configuration.load_config - INFO - Using config: configs/pingpong_gmx.json ...
2026-02-12 14:20:02,556 - freqtrade.configuration.load_config - INFO - Using config: /Users/moo/.config/freqtrade.secrets.json ...
2026-02-12 14:20:02,556 - freqtrade.configuration.environment_vars - INFO - Loading variable 'FREQTRADE__EXCHANGE__CCXT_CONFIG'
2026-02-12 14:20:02,556 - freqtrade.configuration.environment_vars - INFO - Key parts: ['EXCHANGE', 'CCXT_CONFIG']
2026-02-12 14:20:02,558 - freqtrade.loggers - INFO - Enabling colorized output.
2026-02-12 14:20:02,558 - freqtrade.loggers - INFO - Logfile configured
2026-02-12 14:20:02,558 - freqtrade.loggers - INFO - Verbosity set to 0
2026-02-12 14:20:02,558 - freqtrade.configuration.configuration - INFO - Runmode set to live.
```

And then:

```
2026-02-12 14:40:29,011 - eth_defi.gmx.ccxt.async_support.exchange - INFO - Loading markets from REST API (default mode)
2026-02-12 14:41:39,277 - eth_defi.gmx.ccxt.async_support.exchange - INFO - Loaded 110 markets from REST API
2026-02-12 14:41:39,283 - eth_defi.gmx.ccxt.exchange - INFO - Loading markets from REST API (default mode)
2026-02-12 14:41:41,056 - eth_defi.gmx.ccxt.exchange - INFO - Loaded 106 markets from REST API (21 excluded)
```

And then:

```
2026-02-12 14:42:24,905 - pingpong - INFO - 🎯 ENTRY SIGNAL: ETH/USDC:USDC | Price: 1967.4872 | Time: 2026-02-12 14:42:24.905823
```

And then:

```
2026-02-12 15:27:44,652 - freqtrade.worker - INFO - Bot heartbeat. PID=56064, version='2026.1', state='RUNNING'
2026-02-12 15:27:44,655 - pingpong - INFO - 🔄 BOT LOOP START: 2026-02-12 06:27:44.655105+00:00 | Open Trades: 1
2026-02-12 15:27:45,496 - freqtrade.freqtradebot - INFO - No currency pair in active pair whitelist, but checking to exit open trades.
2026-02-12 15:27:59,660 - pingpong - INFO - 🔄 BOT LOOP START: 2026-02-12 06:27:59.660384+00:00 | Open Trades: 1
2026-02-12 15:28:14,676 - pingpong - INFO - 🔄 BOT LOOP START: 2026-02-12 06:28:14.674233+00:00 | Open Trades: 1
2026-02-12 15:28:29,670 - pingpong - INFO - 🔄 BOT LOOP START: 2026-02-12 06:28:29.670521+00:00 | Open Trades: 1
```

And then:

```
2026-02-12 15:30:22,597 - eth_defi.gmx.ccxt.exchange - INFO - Closing LONG position: size=$15.00, collateral=$15.00 (15.001809 USDC), leverage=1.0x
```

And then:

```
2026-02-12 15:30:30,513 - eth_defi.gmx.ccxt.exchange - INFO - ORDER_TRACE: create_order() - Order EXECUTED successfully - price=1977.77, size_usd=15.00
2026-02-12 15:30:30,514 - eth_defi.gmx.ccxt.exchange - INFO - ORDER_TRACE: create_order() RETURNING - order_id=0x6582468792d733, status=closed, filled=0.00744021,
remaining=0.00000000
20
```

You can leave the ping pong strategy running and wacthing it slowly eating through your balance in the form of trading fees.

# FreqUI

FreqTrade has a web dashboard called FreqUI. It is used to monitor the live trading.

You need to enable it with:

```
./freqtrade-gmx install-ui
```

Restart bot.

Then visit http://localhost:8080 - the default username and password we set above are `tradingstrategy.ai` / `tradingstrategy.ai`.

You should see the UI:

![alt text](docs/screenshot.png)

# Stale positions

If FreqTrade crashes in the middle of a trade, it might not be able to recover at the restart.

In this case you need to login to GMX web UI and manually close any stale positions. For this, you need to import the private key to a wallet like Rabby you can connect to a GMX website.

# Fees and tokens

## Trading fees

The trading fee to open a position is [`0.04%` or `0.06%`](https://docs.gmx.io/docs/trading#fees-and-rebates) of the position size, similarly there is a 0.04% or 0.06% fee when closing the position. This applies for increasing the position size of an existing position and partially decreasing a position size as well.

If the trade increases the balance of longs and shorts then the fee would be 0.04%, otherwise the fee would be 0.06%.

## Gas and execution buffer

ETH is needed to pay the gas on Arbitrum. This covers deposit, opening trade and closing the trade. Part of this goes to our Arbitrum transaction costs, part of this we pass to [keepers as execution buffer](https://web3-ethereum-defi.tradingstrategy.ai/api/gmx/_autosummary_gmx/eth_defi.gmx.execution_buffer#module-eth_defi.gmx.execution_buffer) to cover the gas fees for filling our orders.

# How GMX is enabled in CCXT and FreqTrade via monkey patch

The monkeypatch (`python -m eth_defi.gmx.freqtrade.patched_entrypoint`):

- Adds `ccxt.gmx` and `ccxt.async_support.gmx` classes
- Registers GMX in Freqtrade's `SUPPORTED_EXCHANGES`
- Provides CCXT-compatible interface to GMX's on-chain data
- No modifications to Freqtrade or CCXT source code

See [docs/architecture.md](docs/architecture.md) for technical details.

# Next steps

There is a simple [ADX](https://tradingstrategy.ai/glossary/average-directional-index-adx) based [trading strategy example](./user_data/strategies/ADXMomentum.py). It is a [momentum](https://tradingstrategy.ai/glossary/momentum) strategy with modest profit and risk.

It's a good starting point to start working on a real strategy.

# Support

- [Join Discord for any questions](https://tradingstrategy.ai/community).

## Social media

- [Follow on Twitter](https://twitter.com/TradingProtocol)
- [Follow on Telegram](https://t.me/trading_protocol)
- [Follow on LinkedIn](https://www.linkedin.com/company/trading-strategy/)
- [Watch tutorials on YouTube](https://www.youtube.com/@tradingstrategyprotocol)

# License

MIT.

[Created by Trading Strategy](https://tradingstrategy.ai).
