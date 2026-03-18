#!/bin/bash
# Experiment 013: IchiV2+WC Pairlist Layers
#
# Mirrors Exp 003 (IchiV3 pairlist layers) for IchiV2.
# Hypothesis: Does applying progressively tighter pairlist filters improve
# IchiV2's risk-adjusted returns the same way it did for IchiV3?
#
# Arms:
#   A: IchiV2_LS_Static,     static 107 pairs           (baseline, no WC)
#   B: IchiV2_LS_Static,     vol top-75                 (no WC)
#   C: IchiV2_LS_Static,     vol75 + liq $500k           (no WC)
#   D: IchiV2_LS_Static_WhaleCap, vol75 + liq + OI cap   pool=2% oi=2.5%
#   E: IchiV2_LS_Static_WhaleCap, vol100 + OI cap only   pool=off oi=2.5%
#
# WhaleCap params (D/E): oi=0.025, ratio=0.10, minpos=0.01
#
# Usage: bash run_013.sh 2>&1 | tee run_013_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

V2_STRATEGY="IchiV2_LS_Static"
V2_JSON="user_data/strategies/IchiV2_LS_Static.json"
V2WC_STRATEGY="IchiV2_LS_Static_WhaleCap"
V2WC_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"

SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/013-pairlist-layers/results"
CONFIGS_DIR="experiments/ichiv2-gmx/013-pairlist-layers/configs"

V2_BASE_PARAMS=$(cat "$V2_JSON")

restore_jsons() {
    rm -f "$V2WC_JSON"
    echo "Cleaned up $V2WC_JSON"
}
trap restore_jsons EXIT

write_v2wc_json() {
    local pool_share="$1"
    local oi_share="$2"
    local max_trades="$3"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${V2WC_STRATEGY}'
base['params']['max_open_trades']['max_open_trades'] = ${max_trades}
base['params']['buy']['max_oi_share']     = ${oi_share}
base['params']['buy']['max_pool_share']   = ${pool_share}
base['params']['buy']['min_stake_ratio']  = 0.10
base['params']['buy']['min_position_pct'] = 0.01
with open('${V2WC_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_arm() {
    local label="$1"
    local strategy="$2"
    local config="$3"
    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP $label (result exists) ==="
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "=== $label (strategy=${strategy})"
    echo "=============================================="

    ./freqtrade-gmx backtesting \
        --strategy "$strategy" \
        --config "$config" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -30

    LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip 2>/dev/null | head -1)
    if [ -n "$LATEST_ZIP" ]; then
        cp "$LATEST_ZIP" "$result_file"
        echo "=== $label DONE — saved to $result_file ==="
    else
        echo "=== $label FAILED — no zip found ==="
        exit 1
    fi
}

mkdir -p "$RESULTS_DIR"

echo "=== Experiment 013: IchiV2+WC Pairlist Layers ==="
echo "=== Started: $(date) ==="

# Arm A: IchiV2 baseline — static 107 pairs, no WC
run_arm "arm_a_static" "$V2_STRATEGY" "${CONFIGS_DIR}/arm_a_static.json"

# Arm B: IchiV2 — vol top-75, no WC
run_arm "arm_b_vol75" "$V2_STRATEGY" "${CONFIGS_DIR}/arm_b_vol75.json"

# Arm C: IchiV2 — vol75 + liq $500k, no WC
run_arm "arm_c_vol75_liq" "$V2_STRATEGY" "${CONFIGS_DIR}/arm_c_vol75_liq.json"

# Arm D: IchiV2+WC — vol75 + liq + OI cap (pool=2%)
write_v2wc_json 0.02 0.025 10
run_arm "arm_d_vol75_liq_wc" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_d_vol75_liq_wc.json"

# Arm E: IchiV2+WC — vol100 + OI cap (pool cap off)
write_v2wc_json 1.0 0.025 10
run_arm "arm_e_vol100_wc" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_e_vol100_wc.json"

echo ""
echo "=== Experiment 013 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
