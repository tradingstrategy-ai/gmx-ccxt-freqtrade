#!/bin/bash
# Experiment 010: Liquidity Threshold Sweep
# Tests different min_pool_liquidity values with Vol75 + WhaleCap (IchiV3_LS_Static_WhaleCap)
# Baseline: E003 arm D setup (vol75 + liq $500k + whale cap 2.5% OI)
#
# Arms:
#   A — No liquidity filter (volume 75 + whale cap only)
#   B — min_pool_liquidity = $100k
#   C — min_pool_liquidity = $500k  (E003 arm D baseline)
#   D — min_pool_liquidity = $1M
#   E — min_pool_liquidity = $2M
#   F — min_pool_liquidity = $5M
#   G — min_pool_liquidity = $10M

set -e

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

EXP_DIR="experiments/ichiv3-gmx/010-liquidity-threshold-sweep"
RESULTS_DIR="$EXP_DIR/results"
CONFIGS_DIR="$EXP_DIR/configs"
SECRETS="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
COMMON_ARGS="--datadir $DATADIR --timeframe 1h --timerange 20210106-20260312 --cache none"
STRATEGY="IchiV3_LS_Static_WhaleCap"

mkdir -p "$RESULTS_DIR"

echo "============================================="
echo "Experiment 010: Liquidity Threshold Sweep"
echo "Starting capital: \$100,000 USDC"
echo "Strategy: $STRATEGY"
echo "Base: Vol75 + WhaleCap (2.5% OI)"
echo "Sweep: min_pool_liquidity thresholds"
echo "============================================="
echo ""

run_arm() {
    local ARM_NAME="$1"
    local ARM_LABEL="$2"
    local CONFIG_FILE="$3"
    local OUTPUT_NAME="$4"

    echo "[$(date)] Starting $ARM_NAME: $ARM_LABEL..."
    ./freqtrade-gmx backtesting --strategy $STRATEGY \
      --config "$CONFIGS_DIR/$CONFIG_FILE" \
      --config "$SECRETS" \
      $COMMON_ARGS 2>&1 | tee "$RESULTS_DIR/${OUTPUT_NAME}.txt"

    LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip | head -1)
    cp "$LATEST_ZIP" "$RESULTS_DIR/${OUTPUT_NAME}.zip"
    echo "[$(date)] $ARM_NAME complete. Result: $RESULTS_DIR/${OUTPUT_NAME}.zip"
    echo ""
}

# --- Arm A: No liquidity filter (baseline) ---
run_arm "Arm A" "No liquidity filter (vol75 + whale cap only)" \
    "arm_a_no_liq_filter.json" "arm_a_no_liq_filter"

# --- Arm B: $100k liquidity threshold ---
run_arm "Arm B" "Min pool liquidity \$100k" \
    "arm_b_liq_100k.json" "arm_b_liq_100k"

# --- Arm C: $500k liquidity threshold (E003 baseline) ---
run_arm "Arm C" "Min pool liquidity \$500k (E003 baseline)" \
    "arm_c_liq_500k.json" "arm_c_liq_500k"

# --- Arm D: $1M liquidity threshold ---
run_arm "Arm D" "Min pool liquidity \$1M" \
    "arm_d_liq_1m.json" "arm_d_liq_1m"

# --- Arm E: $2M liquidity threshold ---
run_arm "Arm E" "Min pool liquidity \$2M" \
    "arm_e_liq_2m.json" "arm_e_liq_2m"

# --- Arm F: $5M liquidity threshold ---
run_arm "Arm F" "Min pool liquidity \$5M" \
    "arm_f_liq_5m.json" "arm_f_liq_5m"

# --- Arm G: $10M liquidity threshold ---
run_arm "Arm G" "Min pool liquidity \$10M" \
    "arm_g_liq_10m.json" "arm_g_liq_10m"

echo "============================================="
echo "All backtests complete!"
echo "Results saved to: $RESULTS_DIR/"
echo "============================================="
ls -la "$RESULTS_DIR/"*.zip
