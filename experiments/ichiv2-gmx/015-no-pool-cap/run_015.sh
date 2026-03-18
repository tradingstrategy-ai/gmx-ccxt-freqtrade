#!/bin/bash
# Experiment 015: IchiV2+WC No Pool Cap
#
# Mirrors Exp 005 (IchiV3 no pool cap) for IchiV2.
# Hypothesis: Is the pool cap adding value, or does the OI cap alone do the
# filtering? Also tests the user's explicit "try without pool 2% restriction."
#
# Arms (all use oi=2.5% to isolate the pool cap variable):
#   A: Vol75 + Liq $500k + OI cap  pool=2%   oi=2.5%  (baseline, mirrors 013D)
#   B: Vol75 + OI cap only         pool=off  oi=2.5%
#   C: Vol100 + OI cap only        pool=off  oi=2.5%
#   D: Static 107 + OI cap only    pool=off  oi=2.5%
#
# WhaleCap params (all): ratio=0.10, minpos=0.01, max_open_trades=10
#
# Usage: bash run_015.sh 2>&1 | tee run_015_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV2_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/015-no-pool-cap/results"
CONFIGS_DIR="experiments/ichiv2-gmx/015-no-pool-cap/configs"

V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)

restore_json() {
    rm -f "$STRATEGY_JSON"
    echo "Cleaned up $STRATEGY_JSON"
}
trap restore_json EXIT

write_strategy_json() {
    local pool_share="$1"
    local oi_share="$2"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['buy']['max_pool_share']   = ${pool_share}
base['params']['buy']['max_oi_share']     = ${oi_share}
base['params']['buy']['min_stake_ratio']  = 0.10
base['params']['buy']['min_position_pct'] = 0.01
with open('${STRATEGY_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_arm() {
    local label="$1"
    local config="$2"
    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP $label (result exists) ==="
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "=== $label"
    echo "=============================================="

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
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

echo "=== Experiment 015: IchiV2+WC No Pool Cap ==="
echo "=== Started: $(date) ==="

# Arm A: Vol75 + Liq + pool cap 2% (baseline matching 013D)
write_strategy_json 0.02 0.025
run_arm "arm_a_vol75_liq_wc" "${CONFIGS_DIR}/arm_a_vol75_liq_wc.json"

# Arm B: Vol75 + OI cap only (pool cap disabled)
write_strategy_json 1.0 0.025
run_arm "arm_b_vol75_no_pool" "${CONFIGS_DIR}/arm_b_vol75_no_pool.json"

# Arm C: Vol100 + OI cap only (pool cap disabled)
write_strategy_json 1.0 0.025
run_arm "arm_c_vol100_no_pool" "${CONFIGS_DIR}/arm_c_vol100_no_pool.json"

# Arm D: Static 107 + OI cap only (pool cap disabled)
write_strategy_json 1.0 0.025
run_arm "arm_d_static_no_pool" "${CONFIGS_DIR}/arm_d_static_no_pool.json"

echo ""
echo "=== Experiment 015 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
