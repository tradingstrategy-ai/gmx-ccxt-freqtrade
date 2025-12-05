# GMX Freqtrade Setup

Freqtrade setup for trading GMX perpetual futures using web3-ethereum-defi.

## Quick Start

```bash
# Initialize git submodule
git submodule update --init --recursive

# Build and run trade
docker-compose build pingpong-gmx
docker-compose up pingpong-gmx
```

## Usage

```bash
# Run bot and trade
docker compose up pingpong-gmx

# Download data
make data CONTAINER=pingpong_gmx

# Download data with timerange
make data CONTAINER=pingpong_gmx TIMERANGE=20250801-20251001

# Backtest
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong

# Verbosity level for freqtrade commands (empty, -v, -vv, or -vvv or more)
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong VERBOSE=-v

# Pass timerange to freqtrade
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20250801-20251001 VERBOSE=-vv

# Pass timeframe to freqtrade with a different strategy
make backtest CONTAINER=pingpong_gmx STRATEGY=ADXMomentum TIMERANGE=20251031-20251105 TIMEFRAME=1m VERBOSE=-vvv # more verbose
```

## How It Works

1. `web3-ethereum-defi` is installed as a git submodule
2. Entrypoint is patched to register GMX exchange
3. GMX becomes available as an exchange

## Security

- Never commit private keys
- Test on testnet first
