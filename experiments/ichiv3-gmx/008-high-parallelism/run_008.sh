#!/bin/bash
set -euo pipefail
cd /home/ubuntu/dev/gmx-ccxt-freqtrade

SECRETS_CONFIG="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/008-high-parallelism/results"
CONFIGS_DIR="experiments/ichiv3-gmx/008-high-parallelism/configs"
BASE_PARAMS=$(cat user_data/strategies/IchiV3_LS_Static.json)

write_whalecap_json() {
    python3 -c "
import json
base = json.loads('''${BASE_PARAMS}''')
base['strategy_name'] = 'IchiV3_LS_Static_WhaleCap'
base['params']['buy']['max_pool_share'] = 0.02
base['params']['buy']['max_oi_share'] = 0.025
base['params']['buy']['min_stake_ratio'] = 0.10
base['params']['buy']['min_position_pct'] = 0.01
with open('user_data/strategies/IchiV3_LS_Static_WhaleCap.json', 'w') as f:
    json.dump(base, f, indent=2)
"
}

write_highpar_json() {
    local base_stake_pct=$1
    python3 -c "
import json
base = json.loads('''${BASE_PARAMS}''')
base['strategy_name'] = 'IchiV3_LS_Static_HighPar'
base['params']['buy']['max_pool_share'] = 0.02
base['params']['buy']['max_oi_share'] = 0.025
base['params']['buy']['min_stake_ratio'] = 0.10
base['params']['buy']['min_position_pct'] = 0.01
base['params']['buy']['base_stake_pct'] = ${base_stake_pct}
with open('user_data/strategies/IchiV3_LS_Static_HighPar.json', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_arm() {
    local arm=$1
    local strategy=$2
    local config=$3

    result_file="${RESULTS_DIR}/${arm}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP ${arm} (already exists) ==="
        return
    fi

    echo "=== ${arm} (strategy=${strategy}) ==="

    ./freqtrade-gmx backtesting \
        --strategy "$strategy" \
        --config "${config}" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -5

    LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip 2>/dev/null | head -1)
    if [ -n "$LATEST_ZIP" ]; then
        cp "$LATEST_ZIP" "$result_file"
        echo "=== ${arm} DONE — saved to ${result_file} ==="
    else
        echo "=== ${arm} FAILED — no zip found ==="
    fi
}

# Arm A: WhaleCap baseline (10 trades)
write_whalecap_json
run_arm "arm_a_10trades" "IchiV3_LS_Static_WhaleCap" "${CONFIGS_DIR}/arm_a_10trades.json"

# Arm B: HighPar 30 trades, base_stake_pct=0.05
write_highpar_json 0.05
run_arm "arm_b_30trades" "IchiV3_LS_Static_HighPar" "${CONFIGS_DIR}/arm_b_30trades.json"

# Arm C: HighPar 40 trades, base_stake_pct=0.07
write_highpar_json 0.07
run_arm "arm_c_40trades" "IchiV3_LS_Static_HighPar" "${CONFIGS_DIR}/arm_c_40trades.json"

# Arm D: HighPar 50 trades, base_stake_pct=0.10
write_highpar_json 0.10
run_arm "arm_d_50trades" "IchiV3_LS_Static_HighPar" "${CONFIGS_DIR}/arm_d_50trades.json"

# Cleanup
rm -f user_data/strategies/IchiV3_LS_Static_WhaleCap.json
rm -f user_data/strategies/IchiV3_LS_Static_HighPar.json

echo ""
echo "=== EXPERIMENT 008 COMPLETE ==="
ls -la "$RESULTS_DIR"
