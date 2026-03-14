#!/bin/bash
# Experiment 002: Volume Pairlist Layers — Sequential Backtest Runner
# Tests incremental impact of Binance volume sorting, GMX liquidity filtering,
# and OI whale cap on IchiV2_LS_Static with $100k starting capital.

set -e

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

EXP_DIR="experiments/ichiv2-gmx/002-volume-pairlist-layers"
RESULTS_DIR="$EXP_DIR/results"
CONFIGS_DIR="$EXP_DIR/configs"
SECRETS="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
COMMON_ARGS="--datadir $DATADIR --timeframe 1h --timerange 20210106-20260312 --cache none"

mkdir -p "$RESULTS_DIR"

echo "============================================="
echo "Experiment 002: Volume Pairlist Layers"
echo "Starting capital: \$100,000 USDC"
echo "Strategy: IchiV2_LS_Static (arms A-C)"
echo "          IchiV2_LS_Static_WhaleCap (arm D)"
echo "============================================="
echo ""

# --- Arm A: Baseline (StaticPairList, no filtering) ---
echo "[$(date)] Starting Arm A: Baseline (107 pairs, no filtering)..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_Static \
  --config "$CONFIGS_DIR/arm_a_static.json" \
  --config "$SECRETS" \
  $COMMON_ARGS 2>&1 | tee "$RESULTS_DIR/arm_a_baseline.txt"

# Copy result ZIP
LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip | head -1)
cp "$LATEST_ZIP" "$RESULTS_DIR/arm_a_baseline.zip"
echo "[$(date)] Arm A complete. Result: $RESULTS_DIR/arm_a_baseline.zip"
echo ""

# --- Arm B: Volume pairlist only ---
echo "[$(date)] Starting Arm B: Binance volume pairlist (top 75)..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_Static \
  --config "$CONFIGS_DIR/arm_b_volume.json" \
  --config "$SECRETS" \
  $COMMON_ARGS 2>&1 | tee "$RESULTS_DIR/arm_b_volume.txt"

LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip | head -1)
cp "$LATEST_ZIP" "$RESULTS_DIR/arm_b_volume.zip"
echo "[$(date)] Arm B complete. Result: $RESULTS_DIR/arm_b_volume.zip"
echo ""

# --- Arm C: Volume + Liquidity filter ---
echo "[$(date)] Starting Arm C: Volume + liquidity filter (min 500k)..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_Static \
  --config "$CONFIGS_DIR/arm_c_volume_liq.json" \
  --config "$SECRETS" \
  $COMMON_ARGS 2>&1 | tee "$RESULTS_DIR/arm_c_volume_liq.txt"

LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip | head -1)
cp "$LATEST_ZIP" "$RESULTS_DIR/arm_c_volume_liq.zip"
echo "[$(date)] Arm C complete. Result: $RESULTS_DIR/arm_c_volume_liq.zip"
echo ""

# --- Arm D: Volume + Liquidity + WhaleCap ---
echo "[$(date)] Starting Arm D: Volume + liquidity + whale cap (2.5% OI)..."
./freqtrade-gmx backtesting --strategy IchiV2_LS_Static_WhaleCap \
  --config "$CONFIGS_DIR/arm_d_volume_liq_whale.json" \
  --config "$SECRETS" \
  $COMMON_ARGS 2>&1 | tee "$RESULTS_DIR/arm_d_volume_liq_whale.txt"

LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip | head -1)
cp "$LATEST_ZIP" "$RESULTS_DIR/arm_d_volume_liq_whale.zip"
echo "[$(date)] Arm D complete. Result: $RESULTS_DIR/arm_d_volume_liq_whale.zip"
echo ""

echo "============================================="
echo "All backtests complete!"
echo "Results saved to: $RESULTS_DIR/"
echo "============================================="
ls -la "$RESULTS_DIR/"*.zip
