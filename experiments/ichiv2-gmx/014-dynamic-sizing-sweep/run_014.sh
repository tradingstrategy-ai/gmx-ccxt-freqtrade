#!/bin/bash
# Experiment 014: IchiV2+WC Dynamic Sizing Sweep
#
# Mirrors Exp 004 (IchiV3 sizing sweep) for IchiV2.
# Hypothesis: V2's equal-weight sizing may have different optimal OI%/pool%
# thresholds than V3's mcap-tiered sizing. Find V2's own optimal caps.
#
# Phase 1: Grid sweep — pool_share x oi_share (12 arms)
#   pool_share: [0.02, 0.04, 0.06, 0.08]
#   oi_share:   [0.01, 0.025, 0.05]
#   Fixed: min_stake_ratio=0.10, min_pos_pct=0.01, max_open_trades=10
#
# Phase 2: Fine-tune min_stake_ratio for best Phase 1 combo
#   Set BEST_POOL and BEST_OI env vars before running phase 2
#   min_stake_ratio: [0.03, 0.05, 0.10, 0.20]
#   min_pos_pct:     [0.005, 0.01, 0.02]
#
# Usage:
#   Phase 1:  bash run_014.sh 1 2>&1 | tee run_014_phase1_log.txt
#   Phase 2:  BEST_POOL=0.02 BEST_OI=0.025 bash run_014.sh 2 2>&1 | tee run_014_phase2_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV2_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
BASE_CONFIG="experiments/ichiv2-gmx/014-dynamic-sizing-sweep/configs/base_sweep.json"
SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/014-dynamic-sizing-sweep/results"

V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)
PHASE="${1:-1}"

restore_json() {
    rm -f "$STRATEGY_JSON"
    echo "Cleaned up $STRATEGY_JSON"
}
trap restore_json EXIT

write_strategy_json() {
    local pool_share="$1"
    local oi_share="$2"
    local stake_ratio="$3"
    local min_pos="$4"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['buy']['max_pool_share']   = ${pool_share}
base['params']['buy']['max_oi_share']     = ${oi_share}
base['params']['buy']['min_stake_ratio']  = ${stake_ratio}
base['params']['buy']['min_position_pct'] = ${min_pos}
with open('${STRATEGY_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_backtest() {
    local label="$1"
    local pool_share="$2"
    local oi_share="$3"
    local stake_ratio="$4"
    local min_pos="$5"
    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP $label (result exists) ==="
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "=== $label: pool=${pool_share} oi=${oi_share} ratio=${stake_ratio} minpos=${min_pos}"
    echo "=============================================="

    write_strategy_json "$pool_share" "$oi_share" "$stake_ratio" "$min_pos"

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "$BASE_CONFIG" \
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

if [ "$PHASE" = "1" ]; then
    echo "=== Experiment 014 Phase 1: pool_share x oi_share sweep ==="
    echo "=== Started: $(date) ==="

    for pool_share in 0.02 0.04 0.06 0.08; do
        for oi_share in 0.01 0.025 0.05; do
            label="pool${pool_share}_oi${oi_share}"
            run_backtest "$label" "$pool_share" "$oi_share" "0.10" "0.01"
        done
    done

    echo ""
    echo "=== Experiment 014 Phase 1 COMPLETE ==="
    echo "=== Finished: $(date) ==="
    ls -la "$RESULTS_DIR"

elif [ "$PHASE" = "2" ]; then
    BEST_POOL="${BEST_POOL:-0.02}"
    BEST_OI="${BEST_OI:-0.025}"

    echo "=== Experiment 014 Phase 2: min_stake_ratio + min_pos_pct sweep ==="
    echo "=== Best from Phase 1: pool=${BEST_POOL} oi=${BEST_OI} ==="
    echo "=== Started: $(date) ==="

    for stake_ratio in 0.03 0.05 0.10 0.20; do
        label="pool${BEST_POOL}_oi${BEST_OI}_ratio${stake_ratio}"
        run_backtest "$label" "$BEST_POOL" "$BEST_OI" "$stake_ratio" "0.01"
    done

    for min_pos in 0.005 0.02; do
        label="pool${BEST_POOL}_oi${BEST_OI}_ratio0.10_minpos${min_pos}"
        run_backtest "$label" "$BEST_POOL" "$BEST_OI" "0.10" "$min_pos"
    done

    echo ""
    echo "=== Experiment 014 Phase 2 COMPLETE ==="
    echo "=== Finished: $(date) ==="
    ls -la "$RESULTS_DIR"

else
    echo "Usage: bash run_014.sh [1|2]"
    exit 1
fi
