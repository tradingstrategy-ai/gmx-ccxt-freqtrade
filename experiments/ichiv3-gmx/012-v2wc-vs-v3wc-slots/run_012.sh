#!/bin/bash
# Experiment 012: IchiV2+WhaleCap vs IchiV3+WhaleCap — 6-slot vs 10-slot
#
# Goal: Apples-to-apples comparison. Both strategies use identical WhaleCap
# params (OI cap 2.5%, pool cap 2%, min_stake 10%, min_pos 1%) so positions
# are bounded by what GMX can actually absorb. V2 uses equal-weight sizing
# (balance/slots), V3 adds market-cap tier multipliers on top.
#
# Arms:
#   A: IchiV2_LS_Static_WhaleCap @ 10 slots
#   B: IchiV2_LS_Static_WhaleCap @  6 slots
#   C: IchiV3_LS_Static_WhaleCap @ 10 slots  (reference)
#   D: IchiV3_LS_Static_WhaleCap @  6 slots
#
# WhaleCap params (all arms): oi=2.5%, pool=2%, min_stake=10%, min_pos=1%
# Pair universe: static 107 pairs
# Timerange: 20210106-20260312
#
# Usage: bash run_012.sh 2>&1 | tee run_012_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

V2WC_STRATEGY="IchiV2_LS_Static_WhaleCap"
V2WC_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
V3WC_STRATEGY="IchiV3_LS_Static_WhaleCap"
V3WC_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"

SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/012-v2wc-vs-v3wc-slots/results"
CONFIGS_DIR="experiments/ichiv3-gmx/012-v2wc-vs-v3wc-slots/configs"

# WhaleCap params — identical for both strategies for fair comparison
OI_SHARE=0.025
POOL_SHARE=0.02
MIN_STAKE_RATIO=0.10
MIN_POS_PCT=0.01

# Snapshot originals for restore
V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)
V3WC_JSON_ORIG=$(cat "$V3WC_JSON")

restore_jsons() {
    # V2WC has no persistent JSON — just remove it
    rm -f "$V2WC_JSON"
    echo "$V3WC_JSON_ORIG" > "$V3WC_JSON"
    echo "Restored strategy JSONs."
}
trap restore_jsons EXIT

write_v2wc_json() {
    local max_trades="$1"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${V2WC_STRATEGY}'
base['params']['max_open_trades']['max_open_trades'] = ${max_trades}
base['params']['buy']['max_oi_share']      = ${OI_SHARE}
base['params']['buy']['max_pool_share']    = ${POOL_SHARE}
base['params']['buy']['min_stake_ratio']   = ${MIN_STAKE_RATIO}
base['params']['buy']['min_position_pct']  = ${MIN_POS_PCT}
with open('${V2WC_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

write_v3wc_json() {
    local max_trades="$1"
    python3 -c "
import json
base = json.loads('''${V3WC_JSON_ORIG}''')
base['params']['max_open_trades']['max_open_trades'] = ${max_trades}
base['params']['buy']['max_oi_share']      = ${OI_SHARE}
base['params']['buy']['max_pool_share']    = ${POOL_SHARE}
base['params']['buy']['min_stake_ratio']   = ${MIN_STAKE_RATIO}
base['params']['buy']['min_position_pct']  = ${MIN_POS_PCT}
with open('${V3WC_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_arm() {
    local label="$1"
    local strategy="$2"
    local config="$3"

    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo ""
        echo "=== SKIP $label (result already exists) ==="
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

echo "=== Experiment 012: IchiV2+WC vs IchiV3+WC — 6-slot vs 10-slot ==="
echo "=== WhaleCap: OI=${OI_SHARE} pool=${POOL_SHARE} min_stake=${MIN_STAKE_RATIO} min_pos=${MIN_POS_PCT} ==="
echo "=== Started: $(date) ==="

# Arm A: IchiV2+WC @ 10 slots
write_v2wc_json 10
run_arm "arm_a_v2wc_10slots" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_a_v2wc_10slots.json"

# Arm B: IchiV2+WC @ 6 slots
write_v2wc_json 6
run_arm "arm_b_v2wc_6slots" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_b_v2wc_6slots.json"

# Arm C: IchiV3+WC @ 10 slots (reference)
write_v3wc_json 10
run_arm "arm_c_v3wc_10slots" "$V3WC_STRATEGY" "${CONFIGS_DIR}/arm_c_v3wc_10slots.json"

# Arm D: IchiV3+WC @ 6 slots
write_v3wc_json 6
run_arm "arm_d_v3wc_6slots" "$V3WC_STRATEGY" "${CONFIGS_DIR}/arm_d_v3wc_6slots.json"

echo ""
echo "=== Experiment 012 COMPLETE ==="
echo "=== Finished: $(date) ==="
echo "Results in: $RESULTS_DIR"
ls -la "$RESULTS_DIR"
