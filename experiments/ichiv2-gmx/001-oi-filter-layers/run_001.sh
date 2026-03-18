#!/bin/bash
# Experiment 001: OI Filter Layers — Sequential Backtest Runner
# Runs all 5 backtests (Chainlink baseline + A0-A3) and saves results

set -e

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

EXP_DIR="experiments/ichiv2-gmx/001-oi-filter-layers"
RESULTS_DIR="$EXP_DIR/results"

# Common args for full universe tests
FULL_UNIVERSE_ARGS="--config configs/ichiv2_gmx_full_universe.json \
  --config configs/ichiv2_gmx_full_universe.secrets.json \
  --datadir user_data/data/gmx_complete_w_binance \
  --timeframe-detail 5m --timerange 20210106-20260312 --timeframe 1h"

# Common args for Chainlink baseline
CHAINLINK_ARGS="--config configs/ichiv2_gmx.json \
  --config configs/ichiv2_gmx.secrets.json \
  --datadir user_data/data/gmx_complete_w_binance \
  --timeframe-detail 5m --timerange 20210106-20260312 --timeframe 1h"

echo "============================================="
echo "Experiment 001: OI Filter Layers"
echo "============================================="
echo ""

# --- Chainlink Baseline ---
echo "[$(date)] Starting Chainlink baseline (41 pairs, IchiV2_LS_Backtest)..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_Backtest $CHAINLINK_ARGS 2>&1 | tee "$RESULTS_DIR/chainlink_baseline.txt"
echo "[$(date)] Chainlink baseline complete."
echo ""

# --- A1: OI sort only (liquidity_filter_min_pool=0) ---
echo "[$(date)] Setting up A1: OI sort only (liquidity_filter_min_pool=0)..."
# Backup original and set liquidity_filter_min_pool=0
cp user_data/strategies/IchiV2_LS_OI_Filter.json user_data/strategies/IchiV2_LS_OI_Filter.json.bak
python3 -c "
import json
with open('user_data/strategies/IchiV2_LS_OI_Filter.json') as f:
    data = json.load(f)
data['params']['buy']['liquidity_filter_min_pool'] = 0
with open('user_data/strategies/IchiV2_LS_OI_Filter.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Set liquidity_filter_min_pool=0')
"
echo "[$(date)] Starting A1: OI sort only..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_Filter $FULL_UNIVERSE_ARGS 2>&1 | tee "$RESULTS_DIR/A1_oi_sort_only.txt"
echo "[$(date)] A1 complete."
echo ""

# --- A2: OI sort + liquidity filter (liquidity_filter_min_pool=500000) ---
echo "[$(date)] Setting up A2: OI sort + liquidity filter (liquidity_filter_min_pool=500000)..."
python3 -c "
import json
with open('user_data/strategies/IchiV2_LS_OI_Filter.json') as f:
    data = json.load(f)
data['params']['buy']['liquidity_filter_min_pool'] = 500000
with open('user_data/strategies/IchiV2_LS_OI_Filter.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Set liquidity_filter_min_pool=500000')
"
echo "[$(date)] Starting A2: OI sort + liquidity filter..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_Filter $FULL_UNIVERSE_ARGS 2>&1 | tee "$RESULTS_DIR/A2_oi_plus_liquidity.txt"
echo "[$(date)] A2 complete."
echo ""

# --- Restore original OI_Filter JSON ---
mv user_data/strategies/IchiV2_LS_OI_Filter.json.bak user_data/strategies/IchiV2_LS_OI_Filter.json

# --- A3: OI sort + liquidity + whale cap ---
echo "[$(date)] Starting A3: OI sort + liquidity + whale cap..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_WhaleCap $FULL_UNIVERSE_ARGS 2>&1 | tee "$RESULTS_DIR/A3_oi_liq_whalecap.txt"
echo "[$(date)] A3 complete."
echo ""

echo "============================================="
echo "All backtests complete!"
echo "Results saved to: $RESULTS_DIR/"
echo "============================================="
ls -la "$RESULTS_DIR/"
