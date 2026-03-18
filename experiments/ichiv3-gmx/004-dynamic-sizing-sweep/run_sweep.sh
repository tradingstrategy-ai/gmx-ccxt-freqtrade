#!/bin/bash
# Experiment 004: Dynamic Sizing Parameter Sweep
# Sweeps max_pool_share × max_oi_share with fixed min_stake_ratio=0.05
# Then sweeps min_stake_ratio for the best combo found in phase 1.
#
# Usage: bash run_sweep.sh [phase]
#   phase 1 (default): sweep pool_share × oi_share (12 runs)
#   phase 2: sweep min_stake_ratio for best combo (edit BEST_* vars below first)

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV3_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"
BASE_CONFIG="experiments/ichiv3-gmx/004-dynamic-sizing-sweep/configs/base_sweep.json"
SECRETS_CONFIG="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/004-dynamic-sizing-sweep/results"

# Base params inherited from IchiV3_LS_Static.json (mcap sizing etc.)
# We read them once and merge our sweep params on top.
BASE_PARAMS=$(cat user_data/strategies/IchiV3_LS_Static.json)

PHASE="${1:-1}"

write_strategy_json() {
    local pool_share="$1"
    local oi_share="$2"
    local stake_ratio="$3"

    # Extract existing buy params from IchiV3_LS_Static.json and add our sweep params
    python3 -c "
import json, sys

base = json.loads('''${BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['buy']['max_pool_share'] = ${pool_share}
base['params']['buy']['max_oi_share'] = ${oi_share}
base['params']['buy']['min_stake_ratio'] = ${stake_ratio}

with open('${STRATEGY_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_backtest() {
    local label="$1"
    local pool_share="$2"
    local oi_share="$3"
    local stake_ratio="$4"

    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP $label (result exists) ==="
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "=== $label: pool=${pool_share} oi=${oi_share} ratio=${stake_ratio}"
    echo "=============================================="

    write_strategy_json "$pool_share" "$oi_share" "$stake_ratio"

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "$BASE_CONFIG" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -30

    # Copy latest result zip to our results dir
    LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip 2>/dev/null | head -1)
    if [ -n "$LATEST_ZIP" ]; then
        cp "$LATEST_ZIP" "$result_file"
        echo "=== $label DONE — saved to $result_file ==="
    else
        echo "=== $label DONE — WARNING: no zip found ==="
    fi
}

mkdir -p "$RESULTS_DIR"

if [ "$PHASE" = "1" ]; then
    echo "=== PHASE 1: pool_share × oi_share sweep (min_stake_ratio=0.05) ==="

    for pool_share in 0.02 0.04 0.06 0.08; do
        for oi_share in 0.01 0.025 0.05; do
            label="pool${pool_share}_oi${oi_share}_ratio0.05"
            run_backtest "$label" "$pool_share" "$oi_share" "0.05"
        done
    done

    echo ""
    echo "=== PHASE 1 COMPLETE ==="
    echo "Results in: $RESULTS_DIR"
    ls -la "$RESULTS_DIR"

elif [ "$PHASE" = "2" ]; then
    # Edit these after analyzing Phase 1 results
    BEST_POOL="${BEST_POOL:-0.04}"
    BEST_OI="${BEST_OI:-0.025}"

    echo "=== PHASE 2: min_stake_ratio sweep (pool=${BEST_POOL}, oi=${BEST_OI}) ==="

    for stake_ratio in 0.03 0.05 0.10; do
        label="pool${BEST_POOL}_oi${BEST_OI}_ratio${stake_ratio}"
        run_backtest "$label" "$BEST_POOL" "$BEST_OI" "$stake_ratio"
    done

    echo ""
    echo "=== PHASE 2 COMPLETE ==="
    echo "Results in: $RESULTS_DIR"
    ls -la "$RESULTS_DIR"
fi

# Restore original strategy JSON (clean up)
rm -f "$STRATEGY_JSON"
echo "Cleaned up ${STRATEGY_JSON}"
