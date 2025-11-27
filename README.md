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
# Run bot
docker compose up pingpong-gmx

# List markets
docker compose run pingpong-gmx list-markets

# Backtesting
docker compose run pingpong-gmx backtesting

# Dry run
docker compose run pingpong-gmx trade
```

## How It Works

1. `web3-ethereum-defi` is installed as a git submodule
2. Entrypoint is patched to register GMX exchange
3. GMX becomes available as an exchange

## Security

- Never commit private keys
- Test on testnet first
