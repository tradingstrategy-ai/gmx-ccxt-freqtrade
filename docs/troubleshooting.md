# Troubleshooting

Common issues and solutions for GMX Freqtrade setup.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Errors](#configuration-errors)
- [Data Download Issues](#data-download-issues)
- [Backtest Failures](#backtest-failures)
- [GMX-Specific Issues](#gmx-specific-issues)
- [Getting Help](#getting-help)

## Installation Issues

### Submodule Not Initialized

**Problem:**
```bash
ls deps/web3-ethereum-defi/
# Directory is empty or missing
```

**Solution:**
```bash
# Initialize submodule
git submodule update --init --recursive

# Verify
ls eth_defi/
# Should show Python files
```

**If still empty:**
```bash
# Force reinitialize
git submodule deinit -f deps/web3-ethereum-defi
git submodule update --init --recursive
```

---

### Docker Build Fails

**Problem:**
```bash
docker-compose build pingpong_gmx
ERROR: failed to solve with frontend dockerfile.v0
```

**Solutions:**

**1. Clean rebuild:**
```bash
docker-compose build --no-cache pingpong_gmx
```

**2. Check Docker is running:**
```bash
docker info
# Should show Docker daemon info
```

**3. Increase Docker resources:**
- Docker Desktop → Settings → Resources
- RAM: 4GB+ recommended
- Disk: 10GB+ free space

**4. Check Dockerfile syntax:**
```bash
docker build -f Dockerfile -t test .
```

---

### Build Dependency Errors

**Problem:**
```
ERROR: Could not build wheels for gmpy2
```

**Solution:**
```bash
# The Dockerfile should install build dependencies
# If error persists, check Dockerfile has:
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libgmp-dev \
    libmpfr-dev \
    libmpc-dev
```

---

### Permission Denied Errors

**Problem:**
```bash
docker-compose up pingpong_gmx
ERROR: Permission denied
```

**Solution:**
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Mac/Windows: Restart Docker Desktop
```

## Configuration Errors

### Invalid Pair Format

**Problem:**
```
ERROR: Pair ETH-USDC not found
```

**Solution:**
Use correct pair format:
```json
{
  "pair_whitelist": [
    "ETH/USDC:USDC",  // ✅ Correct (futures format)
    "ETH/USDC",       // ✅ Also works. Won't work for futures
    "BTC/USDC:USDC"   // ✅ Correct
  ]
}
```

**Common mistakes:**
```json
{
  "pair_whitelist": [
    "ETH-USDC",       // ❌ Wrong separator
    "ETHUSDC",        // ❌ No separator
    "ETH/USD"         // ❌ Must be USDC on GMX
  ]
}
```

---

### Missing Secrets File

**Problem:**
```
ERROR: Config file not found: configs/pingpong_gmx.secrets.json
```

**Solution:**
```bash
# Create secrets file
cp configs/file.secrets.example.json configs/pingpong_gmx.secrets.json

# Edit with your RPC URL
nano configs/pingpong_gmx.secrets.json
```

**Minimum secrets for backtesting:**
```json
{
  "exchange": {
    "rpc_url": "https://arb1.arbitrum.io/rpc"
  },
  "dry_run": true
}
```

---

### RPC Connection Failed

**Problem:**
```
ERROR: Could not connect to RPC endpoint
```

**Solutions:**

**1. Check RPC URL is valid:**
```bash
curl -X POST https://arb1.arbitrum.io/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

**2. Try alternative public RPCs:**
```json
{
  "rpc_url": "https://arbitrum-one.publicnode.com"
}
```

**3. Check firewall/proxy settings**

**4. Use private RPC for reliability:**
- Alchemy: https://alchemy.com
- Infura: https://infura.io
- QuickNode: https://quicknode.com

---

### Trading Mode Mismatch

**Problem:**
```
ERROR: GMX only supports futures trading
```

**Solution:**
```json
{
  "trading_mode": "futures",  // ✅ Must be "futures"
  "margin_mode": "isolated"   // or "cross"
}
```

**Don't use:**
```json
{
  "trading_mode": "spot"  // ❌ GMX doesn't support spot. Use Swap markets
}
```

## Data Download Issues

### No Data Downloaded

**Problem:**
```bash
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201
WARNING: No data found for pair ETH/USDC
```

**Solutions:**

**1. Check timerange format:**
```bash
# ✅ Correct format: YYYYMMDD-YYYYMMDD
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201

# ❌ Wrong formats:
TIMERANGE=2025-01-01-2025-02-01  # Hyphens in dates
TIMERANGE=01012025-02012025      # Wrong order
```

**2. Verify pair exists in config:**
```bash
cat configs/pingpong_gmx.json | grep pair_whitelist
```

**3. Try different timerange:**
```bash
# GMX launched in 2021, try recent dates
make data CONTAINER=pingpong_gmx TIMERANGE=20241101-20241201
```

**4. Check with verbose output:**
```bash
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201 VERBOSE=-vvv
```

---

### GraphQL Errors

**Problem:**
```
ERROR: GraphQL query failed
```

**Solutions:**

**1. Check internet connection**

**2. Verify GraphQL endpoint:**
```bash
curl https://subgraph.satsuma-prod.com/3b2ced13c8d9/gmx/gmx-arbitrum-stats/api \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'
```

**3. Try again later (endpoint may be temporarily down)**

**4. Check rate limiting:**
```json
{
  "exchange": {
    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 1000  // Increase to 1000ms
    }
  }
}
```

---

### Incomplete Data

**Problem:**
```
WARNING: Missing candles in downloaded data
```

**Solutions:**

**1. Re-download with `--prepend` flag** (added by Makefile automatically):
```bash
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201
```

**2. Delete cached data and re-download:**
```bash
rm -rf user_data/data/gmx/
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201
```

**3. Try smaller timerange:**
```bash
# Instead of 1 year, try 1 month
make data CONTAINER=pingpong_gmx TIMERANGE=20250101-20250201
```

## Backtest Failures

### No Trades Generated

**Problem:**
```
Backtest completed: 0 trades
```

**Solutions:**

**1. Check strategy logic:**
```bash
# Run with very verbose output
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy VERBOSE=-vvv
```

**2. Verify indicators calculate correctly:**
```python
# Add debug logging to strategy
def populate_indicators(self, dataframe, metadata):
    dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

    # Debug: Print last values
    print(f"Last RSI values: {dataframe['rsi'].tail()}")

    return dataframe
```

**3. Check entry conditions aren't too strict:**
```python
# Temporarily loosen conditions to test
def populate_entry_trend(self, dataframe, metadata):
    # Original (strict):
    # dataframe.loc[(dataframe['rsi'] < 20), 'enter_long'] = 1

    # Test (loose):
    dataframe.loc[(dataframe['rsi'] < 50), 'enter_long'] = 1
    return dataframe
```

**4. Verify data is loaded:**
```bash
ls user_data/data/gmx/
# Should show: ETH_USDC-5m.json or similar
```

---

### Strategy Import Errors

**Problem:**
```
ERROR: Could not import strategy MyStrategy
```

**Solutions:**

**1. Check strategy file location:**
```bash
ls user_data/strategies/MyStrategy.py
# File must exist
```

**2. Verify Python syntax:**
```bash
docker-compose run --rm pingpong_gmx python -m py_compile /freqtrade/user_data/strategies/MyStrategy.py
```

**3. Check class name matches filename:**
```python
# File: MyStrategy.py
class MyStrategy(IStrategy):  # ✅ Names match
    pass
```

**4. Verify imports:**
```python
from freqtrade.strategy import IStrategy  # ✅ Correct
from pandas import DataFrame                # ✅ Correct
import talib.abstract as ta                # ✅ Correct
```

---

### Indicator Calculation Errors

**Problem:**
```
ERROR: NaN values in dataframe
ERROR: Invalid indicator values
```

**Solutions:**

**1. Check for NaN before using:**
```python
def populate_entry_trend(self, dataframe, metadata):
    conditions = (
        (dataframe['rsi'] < 30) &
        (dataframe['rsi'].notnull())  # ✅ Check for NaN
    )
    dataframe.loc[conditions, 'enter_long'] = 1
    return dataframe
```

**2. Ensure sufficient startup candles:**
```python
class MyStrategy(IStrategy):
    startup_candle_count = 50  # ✅ Enough for indicators
```

**3. Check indicator period < available data:**
```python
# If you only have 100 candles, don't use:
dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)  # ❌ Not enough data

# Use shorter periods:
dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)   # ✅ OK
```

---

### Memory Errors

**Problem:**
```
ERROR: MemoryError
```

**Solutions:**

**1. Reduce timerange:**
```bash
# Instead of 1 year:
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20240101-20241231

# Try 1 month:
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMERANGE=20250101-20250201
```

**2. Use higher timeframe:**
```bash
# Instead of 1m, use 5m or 1h
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy TIMEFRAME=1h
```

**3. Increase Docker memory:**
- Docker Desktop → Settings → Resources
- Increase memory to 8GB+

## GMX-Specific Issues

### GMX Exchange Not Recognized

**Problem:**
```
freqtrade.exceptions.OperationalException: Exchange gmx is not supported
```

**Solutions:**

**1. Verify monkeypatch is applied:**
```bash
docker-compose run --rm pingpong_gmx python -c "import ccxt; print('gmx' in ccxt.exchanges)"
# Should print: True
```

**2. Check Docker entrypoint:**
```bash
docker inspect pingpong_gmx | grep Entrypoint
# Should show: eth_defi.gmx.freqtrade.patched_entrypoint
```

**3. Verify submodule is initialized:**
```bash
ls deps/web3-ethereum-defi/eth_defi/gmx/
# Should show: ccxt/, freqtrade/, core/, etc.
```

**4. Rebuild container:**
```bash
docker-compose build --no-cache pingpong_gmx
```

---

### Volume Data Missing

**Problem:**
```
WARNING: Volume is 0 for all candles
```

**Solution:**
This is **expected** on GMX! GMX doesn't provide volume data.

**Workarounds:**
```python
# ❌ Don't use volume-based indicators:
dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)

# ✅ Use price-based alternatives:
dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
dataframe['price_roc'] = ta.ROC(dataframe, timeperiod=10)
```

---

### Funding Fee Confusion

**Problem:**
```
My backtest shows profit but actual trading loses money
```

**Explanation:**
Funding fees are **not included** in standard Freqtrade backtests!

**Solution:**
Manually account for funding:
```python
# Rough estimate:
# - 0.01% per 8h (typical)
# - 3 periods per day
# - 0.03% per day

# For 10 trades, avg 24h hold each:
funding_cost = 10 × 0.03% × 1 day = 0.3% of stake
```

---

### High Slippage

**Problem:**
```
Live trades have worse execution than backtest
```

**Solutions:**

**1. Add realistic slippage:**
```json
{
  "exchange": {
    "slippage": 0.10  // 0.10% = 10 basis points
  }
}
```

**2. Check position size vs liquidity:**
```bash
# Check available liquidity
docker-compose run --rm pingpong_gmx python -c "
from eth_defi.gmx.available_liquidity import fetch_available_liquidity
liquidity = fetch_available_liquidity('ETH/USDC')
print(f'Available: {liquidity}')
"
```

**3. Reduce position size if needed**

---

### Gas Costs Higher Than Expected

**Problem:**
```
Transaction costs eating into profits
```

**Solutions:**

**1. Trade less frequently:**
- High frequency (>100 trades/month) = $50+ gas
- Medium frequency (50 trades/month) = $25 gas
- Low frequency (<20 trades/month) = $10 gas

**2. Increase profit targets:**
```python
minimal_roi = {
    "0": 0.01  // 1% minimum (covers gas + fees)
}
```

**3. Use higher timeframes:**
- 1m timeframe → many signals → high gas
- 1h timeframe → fewer signals → lower gas

## Getting Help

### Check Logs

**Freqtrade logs:**
```bash
# Container logs (live view)
docker-compose logs -f pingpong_gmx

# Log files
tail -f user_data/logs/pingpong_gmx.log
```

**Backtest verbose output:**
```bash
make backtest CONTAINER=pingpong_gmx STRATEGY=MyStrategy VERBOSE=-vvv
```

### Diagnostic Commands

**Check GMX registration:**
```bash
docker-compose run --rm pingpong_gmx python -c "
import ccxt
print('CCXT exchanges:', 'gmx' in ccxt.exchanges)

from freqtrade.exchange.common import SUPPORTED_EXCHANGES
print('Freqtrade exchanges:', 'gmx' in SUPPORTED_EXCHANGES)
"
```

**Check data files:**
```bash
ls -lh user_data/data/gmx/
cat user_data/data/gmx/ETH_USDC-5m.json | head -20
```

**Check strategy syntax:**
```bash
docker-compose run --rm pingpong_gmx python -m py_compile /freqtrade/user_data/strategies/MyStrategy.py
```

**Check config validity:**
```bash
docker-compose run --rm pingpong_gmx freqtrade show-config \
  --config /freqtrade/configs/pingpong_gmx.json
```

### Collecting Debug Information

When asking for help, include:

1. **Command run:**
   ```bash
   make backtest CONTAINER=pingpong_gmx STRATEGY=Pingpong TIMERANGE=20250101-20250201
   ```

2. **Error message:**
   ```
   ERROR: Exchange gmx is not supported
   ```

3. **Configuration (sanitized):**
   ```json
   {
     "exchange": {"name": "gmx"},
     "trading_mode": "futures"
   }
   ```

4. **Environment:**
   - OS: macOS 14.0
   - Docker version: 24.0.6
   - Submodule initialized: Yes

5. **Diagnostic output:**
   ```bash
   docker-compose run --rm pingpong_gmx python -c "import ccxt; print(ccxt.exchanges)"
   ```

### Community Resources

- **Freqtrade Discord**: https://discord.gg/freqtrade
- **Freqtrade GitHub Issues**: https://github.com/freqtrade/freqtrade/issues
- **web3-ethereum-defi GitHub**: https://github.com/tradingstrategy-ai/web3-ethereum-defi/issues
- **GMX Discord**: https://discord.gg/gmx

### Issue Reporting

When reporting bugs:

1. Search existing issues first
2. Use provided templates
3. Include reproducible steps
4. Attach relevant logs
5. Mention versions (Docker, Freqtrade, web3-ethereum-defi)

## Common Error Messages

### Quick Reference

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `Exchange gmx is not supported` | Monkeypatch not applied | Rebuild Docker, check entrypoint |
| `No data found for pair` | Wrong timerange or pair | Check config, try different dates |
| `Could not connect to RPC` | RPC endpoint down | Try alternative RPC URL |
| `NaN values in dataframe` | Insufficient startup candles | Increase `startup_candle_count` |
| `MemoryError` | Too much data | Reduce timerange or use higher timeframe |
| `Strategy import failed` | Syntax error or wrong location | Check Python syntax, file location |
| `Permission denied` | Docker permissions | Add user to docker group (Linux) |
| `Config file not found` | Missing secrets file | Create `.secrets.json` file |
| `Pair not found` | Invalid pair format | Use `ETH/USDC:USDC` format |
| `Backtest: 0 trades` | Strategy never triggers | Check entry conditions, add logging |

## Still Stuck?

1. Re-read documentation carefully
2. Check [Architecture](architecture.md) for technical details
3. Try the Pingpong strategy (known to work)
4. Start fresh with clean Docker build
5. Ask on Freqtrade Discord with details

Remember: Most issues are configuration or environment-related, not bugs in the code!

## Next Steps

- **Getting Started** → [Getting Started](getting-started.md)
- **GMX Specifics** → [GMX Specifics](gmx-specifics.md)
- **Architecture** → [Architecture](architecture.md)
