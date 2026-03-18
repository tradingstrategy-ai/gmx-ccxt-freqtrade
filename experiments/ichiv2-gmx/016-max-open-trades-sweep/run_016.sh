#!/bin/bash
# Experiment 016: IchiV2+WC Max Open Trades Sweep
#
# Mirrors Exp 006 (IchiV3 slot sweep) for IchiV2.
# Hypothesis: Find the optimal slot count for V2+WC. OI cap already limits
# per-pair exposure; more slots spread capital thinner while fewer slots
# concentrate it. V2's equal-weight sizing makes this especially impactful.
#
# Arms:
#   A: 6 slots
#   B: 10 slots
#   C: 15 slots
#   D: 20 slots
#   E: 30 slots
#
# Base config: vol100 pairlist (best from Exp 013)
# WhaleCap params: best from Exp 014 (pool=1.0, oi=0.05, ratio=0.10, minpos=0.01)
#   Override via env vars: BEST_POOL, BEST_OI, BEST_RATIO, BEST_MINPOS
#
# Usage: bash run_016.sh 2>&1 | tee run_016_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV2_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/016-max-open-trades-sweep/results"
CONFIGS_DIR="experiments/ichiv2-gmx/016-max-open-trades-sweep/configs"

# WhaleCap params — update these based on Exp 014 phase 2 and Exp 015 results
BEST_POOL="${BEST_POOL:-1.0}"
BEST_OI="${BEST_OI:-0.05}"
BEST_RATIO="${BEST_RATIO:-0.10}"
BEST_MINPOS="${BEST_MINPOS:-0.01}"

V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)

restore_json() {
    rm -f "$STRATEGY_JSON"
    echo "Cleaned up $STRATEGY_JSON"
}
trap restore_json EXIT

write_strategy_json() {
    local max_trades="$1"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['max_open_trades']['max_open_trades'] = ${max_trades}
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

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "$config" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -30 || true

    mapfile -t _ZIPS < <(ls -t user_data/backtest_results/backtest-result-*.zip 2>/dev/null)
    LATEST_ZIP="${_ZIPS[0]:-}"
    if [ -n "$LATEST_ZIP" ]; then
        cp "$LATEST_ZIP" "$result_file"
        echo "=== $label DONE — saved to $result_file ==="
    else
        echo "=== $label FAILED — no zip found ==="
        exit 1
    fi
}

mkdir -p "$RESULTS_DIR"

echo "=== Experiment 016: IchiV2+WC Max Open Trades Sweep ==="
echo "=== WhaleCap: pool=${BEST_POOL} oi=${BEST_OI} ratio=${BEST_RATIO} minpos=${BEST_MINPOS} ==="
echo "=== Started: $(date) ==="

for slots in 6 10 15 20 30; do
    write_strategy_json "$slots"
    run_arm "arm_${slots}slots" "${CONFIGS_DIR}/arm_${slots}slots.json"
done

echo ""
echo "=== Experiment 016 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
