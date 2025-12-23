# Docker Setup Guide

This guide covers running freqtrade-gmx-demo using Docker containers, providing an isolated environment alternative to local Python installation.

## Table of Contents

- [When to Use Docker](#when-to-use-docker)
- [Prerequisites](#prerequisites)
- [Understanding the Docker Setup](#understanding-the-docker-setup)
- [Quick Start](#quick-start)
- [Building Containers](#building-containers)
- [Running Commands](#running-commands)
  - [Using Makefile (Recommended)](#using-makefile-recommended)
  - [Using docker compose Directly](#using-docker-compose-directly)
- [Available Containers](#available-containers)
- [Common Operations](#common-operations)
- [Volume Mapping](#volume-mapping)
- [Troubleshooting](#troubleshooting)

---

## When to Use Docker

**Use Docker if you:**
- Want complete environment isolation
- Prefer not to manage Python virtual environments
- Need to run multiple strategies simultaneously
- Want reproducible builds across different systems

**Use native Python if you:**
- Want faster iteration and debugging
- Need direct access to Python debugging tools
- Prefer simpler setup without Docker overhead

---

## Prerequisites

- **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
  - macOS: https://docs.docker.com/desktop/install/mac-install/
  - Windows: https://docs.docker.com/desktop/install/windows-install/
  - Linux: https://docs.docker.com/engine/install/
- **docker compose** (included in Docker Desktop, separate install on Linux)
- **Git** for cloning the repository
- **10GB+ disk space** for images and data

---

## Understanding the Docker Setup

### The Dockerfile

The project uses a custom Dockerfile based on the official Freqtrade image:

```dockerfile
FROM freqtradeorg/freqtrade:2025.10

# Install build dependencies for web3-ethereum-defi
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc g++ python3-dev \
        libgmp-dev libmpfr-dev libmpc-dev && \
    apt-get clean

USER ftuser

# Install web3-ethereum-defi from local submodule
COPY deps/web3-ethereum-defi /tmp/web3-ethereum-defi
RUN pip install --user --force-reinstall "/tmp/web3-ethereum-defi[web3v7]"

# Install plotly for visualization
RUN pip install --user plotly

# Use patched entrypoint for GMX integration
ENTRYPOINT ["python", "-u", "-B", "-m", "eth_defi.gmx.freqtrade.patched_entrypoint", "freqtrade"]
CMD ["trade"]
```

**Key points:**
- Based on official `freqtradeorg/freqtrade:2025.10` image
- Installs `web3-ethereum-defi` from local submodule (not PyPI)
- Uses patched entrypoint to apply GMX integration
- Includes plotly for generating equity curves

### docker-compose.yml

Defines 6 pre-configured containers for different strategy/exchange combinations:

- **pingpong_gmx** (port 9090) - Pingpong strategy on GMX
- **simple_gmx** (port 9091) - Simple strategy on GMX
- **adxmomentum_gmx** (port 9093) - ADX Momentum strategy on GMX
- **ichiv2_gmx** (port 9094) - IchiV2_LS_Live strategy on GMX
- **pingpong_hyperliquid** (port 9090) - Pingpong strategy on Hyperliquid
- **simple_hyperliquid** (port 9092) - Simple strategy on Hyperliquid

Each container:
- Mounts `user_data/`, `configs/`, and `db/` directories
- Uses dedicated SQLite database file
- Writes logs to strategy-specific file
- Restarts automatically unless stopped

---

## Quick Start

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/tradingstrategy-ai/freqtrade-gmx-demo.git
cd freqtrade-gmx-demo

# Initialize submodules (required for web3-ethereum-defi)
git submodule update --init --recursive
```

### Step 2: Build Container

```bash
# Build a specific container (example: pingpong_gmx)
docker-compose build pingpong_gmx

# Or build all containers at once
docker-compose build
```

**Note**: Building takes 5-10 minutes on first run (downloads base image and installs dependencies).

### Step 3: Download Data

```bash
# Using Makefile (recommended)
make data CONTAINER=pingpong_gmx TIMERANGE=20251128-20251208

# Or using docker compose directly
docker compose run --rm pingpong_gmx download-data \
  --config /freqtrade/configs/pingpong_gmx.json \
  --config /freqtrade/configs/pingpong_gmx.secrets.json \
  --timeframe 5m \
  --timerange 20251128-20251208
```

### Step 4: Run Backtest

```bash
# Using Makefile (recommended)
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20251128-20251208

# Or using docker compose directly
docker compose run --rm pingpong_gmx backtesting \
  --config /freqtrade/configs/pingpong_gmx.json \
  --config /freqtrade/configs/pingpong_gmx.secrets.json \
  --strategy Pingpong \
  --timeframe 5m \
  --timerange 20251128-20251208
```

---

## Building Containers

### Build Single Container

```bash
# Build specific container
docker-compose build pingpong_gmx
docker-compose build adxmomentum_gmx
```

### Build All Containers

```bash
# Build all defined containers
docker-compose build
```

### Rebuild from Scratch

```bash
# Force rebuild (no cache)
docker-compose build --no-cache pingpong_gmx

# Rebuild if submodule updated
docker-compose build --pull pingpong_gmx
```

---

## Running Commands

### Using Makefile (Recommended)

The Makefile provides convenient shortcuts for common operations.

#### Download Data

```bash
# Basic usage
make data CONTAINER=pingpong_gmx TIMERANGE=20251128-20251208

# With custom timeframe
make data CONTAINER=adxmomentum_gmx TIMEFRAME=1h TIMERANGE=20250101-20250401

# With verbosity
make data CONTAINER=pingpong_gmx TIMERANGE=20251128-20251208 VERBOSE=-vv
```

**Parameters:**
- `CONTAINER` (required): Container name (e.g., `pingpong_gmx`, `adxmomentum_gmx`)
- `TIMEFRAME` (optional): Default `5m`, can be `1m`, `1h`, `4h`, `1d`
- `TIMERANGE` (optional): Default `20250101-20251130`
- `VERBOSE` (optional): `-v`, `-vv`, or `-vvv`

#### Run Backtest

```bash
# Basic usage
make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20251128-20251208

# With custom timeframe and verbosity
make backtest CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401 VERBOSE=-vv
```

**Parameters:**
- `CONTAINER` (required): Container name
- `STRATEGY` (required): Strategy name (e.g., `Pingpong`, `Simple`, `ADXMomentum`)
- `TIMEFRAME` (optional): Default `5m`
- `TIMERANGE` (optional): Default `20250101-20251130`
- `VERBOSE` (optional): `-v`, `-vv`, or `-vvv`

#### Plot Dataframe

```bash
# Basic usage
make plot-dataframe CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum

# With specific indicators
make plot-dataframe CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum INDICATORS1="adx plus_di minus_di" INDICATORS2="mom"

# With timeframe and timerange
make plot-dataframe CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TIMEFRAME=1h TIMERANGE=20250101-20250401

# With specific backtest file
make plot-dataframe CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum BACKTEST_FILENAME=backtest-result-2025-12-08_11-36-37.json
```

**Parameters:**
- `CONTAINER` (required): Container name
- `STRATEGY` (required): Strategy name
- `PAIRS` (optional): Space-separated pairs (e.g., `"ETH/USDC:USDC BTC/USDC:USDC"`)
- `TIMEFRAME` (optional): Timeframe filter
- `TIMERANGE` (optional): Date range filter
- `BACKTEST_FILENAME` (optional): Specific backtest file (defaults to latest)
- `INDICATORS1` (optional): Indicators for main chart
- `INDICATORS2` (optional): Indicators for subplot

#### Plot Profit

```bash
# Basic usage
make plot-profit CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum

# With auto-open in browser
make plot-profit CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum AUTO_OPEN=1

# With specific pairs and timerange
make plot-profit CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum PAIRS="ETH/USDC:USDC" TIMERANGE=20250101-20250401

# Using database trades instead of backtest
make plot-profit CONTAINER=adxmomentum_gmx STRATEGY=ADXMomentum TRADE_SOURCE=DB DB=adxmomentum_gmx.sqlite
```

**Parameters:**
- `CONTAINER` (required): Container name
- `STRATEGY` (required): Strategy name
- `PAIRS` (optional): Space-separated pairs
- `TIMEFRAME` (optional): Timeframe filter
- `TIMERANGE` (optional): Date range filter
- `AUTO_OPEN` (optional): Set to `1` to auto-open in browser
- `BACKTEST_FILENAME` (optional): Specific backtest file
- `TRADE_SOURCE` (optional): Set to `DB` to use database trades
- `DB` (optional): Database filename (required if `TRADE_SOURCE=DB`)

---

### Using docker compose Directly

For more control, use `docker compose run` directly:

#### Download Data

```bash
docker compose run --rm pingpong_gmx download-data \
  --config /freqtrade/configs/pingpong_gmx.json \
  --config /freqtrade/configs/pingpong_gmx.secrets.json \
  --timeframe 5m \
  --timerange 20251128-20251208 \
  --prepend
```

#### Run Backtest

```bash
docker compose run --rm adxmomentum_gmx backtesting \
  --config /freqtrade/configs/adxmomentum_gmx.json \
  --config /freqtrade/configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --timeframe 1h \
  --timerange 20250101-20250401 \
  -vv
```

#### Plot Dataframe

```bash
docker compose run --rm adxmomentum_gmx plot-dataframe \
  --config /freqtrade/configs/adxmomentum_gmx.json \
  --config /freqtrade/configs/adxmomentum_gmx.secrets.json \
  --strategy ADXMomentum \
  --indicators1 adx plus_di minus_di \
  --indicators2 mom
```

#### Plot Profit

```bash
docker compose run --rm adxmomentum_gmx plot-profit \
  --config /freqtrade/configs/adxmomentum_gmx.json \
  --config /freqtrade/configs/adxmomentum_gmx.secrets.json \
  --auto-open
```

---

## Available Containers

### GMX Containers

| Container Name | Strategy | Exchange | Port | Config Files |
|---------------|----------|----------|------|-------------|
| `pingpong_gmx` | Pingpong | GMX | 9090 | `configs/pingpong_gmx.json`, `configs/pingpong_gmx.secrets.json` |
| `simple_gmx` | Simple | GMX | 9091 | `configs/simple_gmx.json`, `configs/simple_gmx.secrets.json` |
| `adxmomentum_gmx` | ADXMomentum | GMX | 9093 | `configs/adxmomentum_gmx.json`, `configs/adxmomentum_gmx.secrets.json` |
| `ichiv2_gmx` | IchiV2_LS_Live | GMX | 9094 | `configs/ichiv2_gmx.json`, `configs/ichiv2_gmx.secrets.json` |

### Hyperliquid Containers

| Container Name | Strategy | Exchange | Port | Config Files |
|---------------|----------|----------|------|-------------|
| `pingpong_hyperliquid` | Pingpong | Hyperliquid | 9090 | `configs/pingpong_hyperliquid.json`, `configs/pingpong_hyperliquid.secrets.json` |
| `simple_hyperliquid` | Simple | Hyperliquid | 9092 | `configs/simple_hyperliquid.json`, `configs/simple_hyperliquid.secrets.json` |

---

## Common Operations

### Start Container in Live/Dry-Run Mode

```bash
# Start container in background
docker-compose up -d pingpong_gmx

# View logs
docker-compose logs -f pingpong_gmx

# Stop container
docker-compose stop pingpong_gmx
```

### Execute Shell in Container

```bash
# Open bash shell inside container
docker compose run --rm pingpong_gmx bash

# Inside container, you can run any freqtrade command
# Commands automatically use the GMX-patched entrypoint
freqtrade --version
freqtrade list-strategies
```

### View Container Status

```bash
# List running containers
docker-compose ps

# View logs from all containers
docker-compose logs

# View logs from specific container
docker-compose logs pingpong_gmx
```

### Clean Up

```bash
# Stop all containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove built images (to rebuild from scratch)
docker rmi freqtrade-gmx-demo-pingpong_gmx
docker rmi freqtrade-gmx-demo-adxmomentum_gmx
```

---

## Volume Mapping

Containers mount the following directories from your host machine:

| Host Directory | Container Path | Purpose |
|---------------|----------------|---------|
| `./user_data` | `/freqtrade/user_data` | Strategies, data, backtest results, plots |
| `./configs` | `/freqtrade/configs` | Configuration files |
| `./db` | `/freqtrade/db` | SQLite database files |

**This means:**
- Data downloaded in containers appears in `./user_data/data/`
- Backtest results saved to `./user_data/backtest_results/`
- Plots generated to `./user_data/plot/`
- Strategies in `./user_data/strategies/` are accessible in containers

---

## Troubleshooting

### Container Fails to Build

**Problem**: Build fails with dependency errors

```bash
# Rebuild from scratch without cache
docker-compose build --no-cache pingpong_gmx

# Check if submodule is initialized
git submodule status
# Should show a commit hash, not "-" prefix

# Update submodule if needed
git submodule update --init --recursive
```

### GMX Exchange Not Recognized

**Problem**: `Exchange gmx is not supported`

**Solution**: Rebuild container to reinstall web3-ethereum-defi:

```bash
docker-compose build --no-cache pingpong_gmx
```

### No Data Downloaded

**Problem**: Data download completes but no files in `user_data/data/gmx/`

```bash
# Check timerange format (YYYYMMDD-YYYYMMDD)
make data CONTAINER=pingpong_gmx TIMERANGE=20251128-20251208 VERBOSE=-vv

# Verify container has access to configs
docker compose run --rm pingpong_gmx ls -la /freqtrade/configs/
```

### Port Already in Use

**Problem**: `Bind for 0.0.0.0:9090 failed: port is already allocated`

**Solution**: Either stop the conflicting container or change the port in `docker-compose.yml`:

```yaml
ports:
  - "9094:8080"  # Changed from 9090
```

### Permission Denied on Volume Mounts

**Problem**: Container can't write to `user_data/` or `db/`

**Solution** (Linux only):

```bash
# Fix permissions
sudo chown -R $(whoami):$(whoami) user_data db configs

# Or run container with your user ID
docker compose run --rm --user $(id -u):$(id -g) pingpong_gmx bash
```

### Out of Disk Space

**Problem**: Docker build fails with "no space left on device"

**Solution**:

```bash
# Clean up unused images and containers
docker system prune -a

# Remove old volumes
docker volume prune
```

### Container Crashes Immediately

**Problem**: Container starts but exits immediately

```bash
# View error logs
docker-compose logs pingpong_gmx

# Common causes:
# 1. Missing secrets file - create configs/pingpong_gmx.secrets.json
# 2. Invalid JSON in config - validate with jsonlint
# 3. Database locked - remove db/pingpong_gmx.sqlite and restart
```

---

## Comparison: Docker vs Native Python

| Aspect | Docker | Native Python (./freqtrade-gmx) |
|--------|--------|-------------------------------|
| **Setup Time** | 5-10 min (first build) | 3-5 min |
| **Isolation** | Complete | Shared venv |
| **Debugging** | More complex | Direct access |
| **Multiple Strategies** | Easy (separate containers) | Manual management |
| **Disk Space** | ~2GB per image | ~500MB (venv) |
| **Performance** | Slight overhead | Native speed |
| **Updates** | Rebuild containers | `pip install -U` |

---

## Additional Resources

- **Dockerfile**: See `./Dockerfile` for build configuration
- **docker-compose.yml**: See `./docker-compose.yml` for service definitions
- **Makefile**: See `./Makefile` for all available commands
- **Freqtrade Docker Docs**: https://www.freqtrade.io/en/stable/docker_quickstart/
- **Docker Compose Reference**: https://docs.docker.com/compose/

---

## Quick Reference

### Makefile Commands Summary

```bash
# Download data
make data CONTAINER=<name> TIMERANGE=<range> [TIMEFRAME=5m] [VERBOSE=-v]

# Run backtest
make backtest CONTAINER=<name> STRATEGY=<strat> TIMERANGE=<range> [VERBOSE=-v]

# Plot dataframe
make plot-dataframe CONTAINER=<name> STRATEGY=<strat> [INDICATORS1="..."] [INDICATORS2="..."]

# Plot profit
make plot-profit CONTAINER=<name> STRATEGY=<strat> [AUTO_OPEN=1] [TIMERANGE=<range>]
```

### Container Names

- GMX: `pingpong_gmx`, `simple_gmx`, `adxmomentum_gmx`
- Hyperliquid: `pingpong_hyperliquid`, `simple_hyperliquid`

### Strategy Names

- `Pingpong` - Entry/exit every minute (1m timeframe)
- `Simple` - RSI-based momentum strategy
- `ADXMomentum` - Multi-indicator trend following (1h timeframe)
