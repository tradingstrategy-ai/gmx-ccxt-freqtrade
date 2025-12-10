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

### Virtual Environment Not Activated

**Problem:**
```bash
python -c "import freqtrade"
ModuleNotFoundError: No module named 'freqtrade'
```

**Solution:**
```bash
# Activate virtual environment (from main project directory)
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Verify activation
which python
# Should show: /path/to/freqtrade-gmx-demo/.venv/bin/python
```

---

### ImportError: cannot import name '__version__' from 'freqtrade'

**Problem:**
```bash
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
# ImportError: cannot import name '__version__' from 'freqtrade' (unknown location)
```

**Cause:**
This is a Python import conflict. When running from the project directory, Python finds the `freqtrade/` subdirectory (the cloned freqtrade repository) as a namespace package before finding the installed freqtrade package in the virtual environment.

**Solution:**
Use the `freqtrade-gmx` wrapper script instead:

```bash
# ✓ Correct - use the wrapper script
./freqtrade-gmx --version

# ✓ Or add to PATH
export PATH="$PWD:$PATH"
freqtrade-gmx --version
```

**Why the wrapper works:**
The `freqtrade-gmx` script changes to `/tmp` before running freqtrade, avoiding the import conflict with the `freqtrade/` directory in your project.

**Alternative (manual):**
If you need to run the command directly without the wrapper:
```bash
cd /tmp
source /path/to/freqtrade-gmx-demo/.venv/bin/activate
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
```

---

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
ls deps/web3-ethereum-defi/eth_defi/
# Should show Python files
```

**If still empty:**
```bash
# Force reinitialize
git submodule deinit -f deps/web3-ethereum-defi
git submodule update --init --recursive
```

---

### System Dependencies Missing

**Problem:**
```
ERROR: Could not build wheels for gmpy2
ERROR: Failed building wheel for pandas
```

**Solution:**

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt install -y python3-pip python3-venv python3-dev python3-pandas \
    build-essential gcc g++ libgmp-dev libmpfr-dev libmpc-dev git curl
```

**macOS:**
```bash
brew install gettext libomp
```

**For other systems**, see [Freqtrade installation requirements](https://www.freqtrade.io/en/stable/installation/#requirements).

---

### Python Version Issues

**Problem:**
```bash
python3 --version
Python 3.9.7  # Too old!
```

**Solution:**
```bash
# Install Python 3.11+
# Ubuntu/Debian:
sudo apt install python3.11 python3.11-venv

# macOS:
brew install python@3.11

# Verify:
python3.11 --version
# Should show 3.11.x or higher

# Use python3.11 explicitly when creating venv
python3.11 -m venv .venv
```

---

### pip Install Fails

**Problem:**
```bash
pip install -e .
ERROR: Failed to build installable wheels for some pyproject.toml based projects
```

**Solutions:**

**1. Upgrade pip, setuptools, and wheel:**
```bash
python3 -m pip install --upgrade pip setuptools wheel
```

**2. Ensure venv is activated:**
```bash
which python
# Should show .venv path
```

**3. Check system dependencies installed** (see above)

---

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
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201
WARNING: No data found for pair ETH/USDC
```

**Solutions:**

**1. Check timerange format:**
```bash
# ✅ Correct format: YYYYMMDD-YYYYMMDD
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201

# ❌ Wrong formats:
--timerange 2025-01-01-2025-02-01  # Hyphens in dates
--timerange 01012025-02012025      # Wrong order
```

**2. Verify pair exists in config:**
```bash
cat configs/pingpong_gmx.json | grep pair_whitelist
```

**3. Try different timerange:**
```bash
# GMX launched in 2021, try recent dates
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20241101-20241201
```

**4. Check with verbose output:**
```bash
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201 -vvv
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

**1. Re-download with `--prepend` flag:**
```bash
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201 --prepend
```

**2. Delete cached data and re-download:**
```bash
rm -rf user_data/data/gmx/
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201
```

**3. Try smaller timerange:**
```bash
# Instead of 1 year, try 1 month
freqtrade download-data --exchange gmx --config configs/pingpong_gmx.json --timerange 20250101-20250201
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
freqtrade backtesting --strategy MyStrategy --config configs/pingpong_gmx.json --timerange 20250101-20250201 -vvv
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
python -m py_compile user_data/strategies/MyStrategy.py
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
freqtrade backtesting --strategy MyStrategy --config configs/pingpong_gmx.json --timerange 20240101-20241231

# Try 1 month:
freqtrade backtesting --strategy MyStrategy --config configs/pingpong_gmx.json --timerange 20250101-20250201
```

**2. Use higher timeframe:**
```bash
# Instead of 1m, use 5m or 1h
freqtrade backtesting --strategy MyStrategy --config configs/pingpong_gmx.json --timeframe 1h --timerange 20250101-20250201
```

**3. Increase system memory:**
- Close unnecessary applications
- Restart your computer if needed

## GMX-Specific Issues

### ModuleNotFoundError: No module named 'eth_defi.gmx.freqtrade'

**Problem:**
```bash
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
# ModuleNotFoundError: No module named 'eth_defi.gmx.freqtrade'
```

**Cause:**
You installed `web3-ethereum-defi` from PyPI instead of from the local submodule. The PyPI version (v0.35) doesn't include the freqtrade integration yet.

**Solution:**
Uninstall the PyPI version and install from the local submodule:

```bash
source .venv/bin/activate

# Uninstall PyPI version
uv pip uninstall web3-ethereum-defi

# Install from local submodule (includes freqtrade integration)
uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"

# Verify
./freqtrade-gmx --version
```

**Verification:**
Check that the freqtrade module exists:
```bash
python -c "import eth_defi.gmx.freqtrade; print('Freqtrade integration found!')"
# Should print: Freqtrade integration found!
```

---

### GMX Exchange Not Recognized

**Problem:**
```
freqtrade.exceptions.OperationalException: Exchange gmx is not supported
```

**Solutions:**

**1. Verify monkeypatch is applied:**
```bash
python -c "import ccxt; print('GMX registered:', 'gmx' in ccxt.exchanges)"
# Should print: GMX registered: True
```

**2. Verify web3-ethereum-defi is installed:**
```bash
python -c "import eth_defi.gmx; print('GMX module found')"
# Should print: GMX module found
```

**3. Verify submodule is initialized:**
```bash
ls deps/web3-ethereum-defi/eth_defi/gmx/
# Should show: ccxt/, freqtrade/, core/, etc.
```

**4. Reinstall GMX integration:**
```bash
# Ensure venv is activated
source .venv/bin/activate
# Reinstall from local submodule
uv pip uninstall web3-ethereum-defi
uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"
```

**5. Verify using patched entrypoint:**
```bash
# You must use the patched entrypoint
python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade --version
# Should show freqtrade version
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
python -c "
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
# Log files (if running live or dry-run)
tail -f user_data/logs/freqtrade.log
```

**Backtest verbose output:**
```bash
freqtrade backtesting --strategy MyStrategy --config configs/pingpong_gmx.json -vvv
```

### Diagnostic Commands

**Check GMX registration:**
```bash
python -c "
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
python -m py_compile user_data/strategies/MyStrategy.py
```

**Check config validity:**
```bash
freqtrade show-config --config configs/pingpong_gmx.json
```

### Collecting Debug Information

When asking for help, include:

1. **Command run:**
   ```bash
   freqtrade backtesting --strategy Pingpong --config configs/pingpong_gmx.json --timerange 20250101-20250201
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
   - Python version: 3.11.5
   - Virtual environment activated: Yes
   - Submodule initialized: Yes

5. **Diagnostic output:**
   ```bash
   python -c "import ccxt; print('gmx' in ccxt.exchanges)"
   python -c "import eth_defi.gmx; print('GMX module found')"
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
5. Mention versions (Python, Freqtrade, web3-ethereum-defi)

## Common Error Messages

### Quick Reference

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `Exchange gmx is not supported` | Monkeypatch not applied | Use patched entrypoint, reinstall web3-ethereum-defi |
| `No data found for pair` | Wrong timerange or pair | Check config, try different dates |
| `Could not connect to RPC` | RPC endpoint down | Try alternative RPC URL |
| `NaN values in dataframe` | Insufficient startup candles | Increase `startup_candle_count` |
| `MemoryError` | Too much data | Reduce timerange or use higher timeframe |
| `Strategy import failed` | Syntax error or wrong location | Check Python syntax, file location |
| `ModuleNotFoundError: freqtrade` | Virtual environment not activated | Activate venv with `source .venv/bin/activate` |
| `Config file not found` | Missing secrets file | Create `.secrets.json` file |
| `Pair not found` | Invalid pair format | Use `ETH/USDC:USDC` format |
| `Backtest: 0 trades` | Strategy never triggers | Check entry conditions, add logging |

## Still Stuck?

1. Re-read documentation carefully
2. Check [Architecture](architecture.md) for technical details
3. Try the Pingpong strategy (known to work)
4. Start fresh with clean venv:
   ```bash
   rm -rf .venv
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r freqtrade-develop/requirements.txt
   uv pip install -e freqtrade-develop/
   uv pip install -e "deps/web3-ethereum-defi[web3v7,data,ccxt]"
   ```
5. Ask on Freqtrade Discord with details

Remember: Most issues are configuration or environment-related, not bugs in the code!

## Next Steps

- **Getting Started** → [Getting Started](getting-started.md)
- **GMX Specifics** → [GMX Specifics](gmx-specifics.md)
- **Architecture** → [Architecture](architecture.md)
