#!/bin/bash
# Experiment 018: IchiV2+WC Top Volume Focus
#
# Mirrors Exp 009 (IchiV3 top volume focus) for IchiV2.
# Hypothesis: Can a very concentrated top-volume universe improve
# risk-adjusted returns for V2? Tests the sub-30 range more granularly.
#
# Arms:
#   A: Top 10
#   B: Top 15
#   C: Top 20
#   D: Top 25
#   E: Top 30
#
# WhaleCap params: best from Exp 014/015/016
#   Override via env vars: BEST_POOL, BEST_OI, BEST_RATIO, BEST_MINPOS, BEST_SLOTS
#
# Usage: bash run_018.sh 2>&1 | tee run_018_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV2_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/018-top-volume-focus/results"
CONFIGS_DIR="experiments/ichiv2-gmx/018-top-volume-focus/configs"

# WhaleCap params — update based on Exp 014/015/016 results
BEST_POOL="${BEST_POOL:-1.0}"
BEST_OI="${BEST_OI:-0.05}"
BEST_RATIO="${BEST_RATIO:-0.10}"
BEST_MINPOS="${BEST_MINPOS:-0.01}"
BEST_SLOTS="${BEST_SLOTS:-10}"

V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)

restore_json() {
    rm -f "$STRATEGY_JSON"
    echo "Cleaned up $STRATEGY_JSON"
}
trap restore_json EXIT

write_strategy_json() {
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['max_open_trades']['max_open_trades'] = ${BEST_SLOTS}
base['params']['buy']['max_pool_share']   = ${BEST_POOL}
base['params']['buy']['max_oi_share']     = ${BEST_OI}
base['params']['buy']['min_stake_ratio']  = ${BEST_RATIO}
base['params']['buy']['min_position_pct'] = ${BEST_MINPOS}
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

    # Snapshot existing zips before running
    local before_zips
    before_zips=$(ls user_data/backtest_results/backtest-result-*.zip 2>/dev/null | sort || true)

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "$config" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -30 || true

    # Find a NEW zip (not in the before-snapshot)
    local new_zip=""
    while IFS= read -r f; do
        if ! echo "$before_zips" | grep -qF "$f"; then
            new_zip="$f"
        fi
    done < <(ls user_data/backtest_results/backtest-result-*.zip 2>/dev/null | sort || true)

    if [ -n "$new_zip" ]; then
        cp "$new_zip" "$result_file"
        echo "=== $label DONE — saved to $result_file ==="
    else
        echo "=== $label FAILED — no new zip found (OOM or crash?) ==="
        exit 1
    fi
}

mkdir -p "$RESULTS_DIR"
write_strategy_json

echo "=== Experiment 018: IchiV2+WC Top Volume Focus ==="
echo "=== WhaleCap: pool=${BEST_POOL} oi=${BEST_OI} ratio=${BEST_RATIO} minpos=${BEST_MINPOS} slots=${BEST_SLOTS} ==="
echo "=== Started: $(date) ==="

run_arm "arm_top10" "${CONFIGS_DIR}/arm_top10.json"
run_arm "arm_top15" "${CONFIGS_DIR}/arm_top15.json"
run_arm "arm_top20" "${CONFIGS_DIR}/arm_top20.json"
run_arm "arm_top25" "${CONFIGS_DIR}/arm_top25.json"
run_arm "arm_top30" "${CONFIGS_DIR}/arm_top30.json"

echo ""
echo "=== Experiment 018 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
