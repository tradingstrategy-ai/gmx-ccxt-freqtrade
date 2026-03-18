#!/bin/bash
# Experiment 019: IchiV2+WC Liquidity Threshold Sweep
#
# Mirrors Exp 010 (IchiV3 liquidity sweep) for IchiV2.
# Hypothesis: Find the optimal GMX pool liquidity floor for V2.
# V2 with equal-weight sizing may be more sensitive to liquidity thresholds
# than V3 (which sizes down small-cap positions via mcap tier anyway).
#
# Arms:
#   A: No liquidity filter       (baseline)
#   B: min_pool_liquidity $100k
#   C: min_pool_liquidity $500k
#   D: min_pool_liquidity $1M
#   E: min_pool_liquidity $2M
#   F: min_pool_liquidity $5M
#   G: min_pool_liquidity $10M
#
# Base pairlist: Vol100 (best from Exp 017)
# WhaleCap params: best from Exp 014/015/016
#   Override via env vars: BEST_POOL, BEST_OI, BEST_RATIO, BEST_MINPOS, BEST_SLOTS
#
# Usage: bash run_019.sh 2>&1 | tee run_019_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV2_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/019-liquidity-threshold-sweep/results"
CONFIGS_DIR="experiments/ichiv2-gmx/019-liquidity-threshold-sweep/configs"

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

echo "=== Experiment 019: IchiV2+WC Liquidity Threshold Sweep ==="
echo "=== WhaleCap: pool=${BEST_POOL} oi=${BEST_OI} ratio=${BEST_RATIO} minpos=${BEST_MINPOS} slots=${BEST_SLOTS} ==="
echo "=== Started: $(date) ==="

run_arm "arm_a_no_liq"   "${CONFIGS_DIR}/arm_a_no_liq.json"
run_arm "arm_b_liq100k"  "${CONFIGS_DIR}/arm_b_liq100k.json"
run_arm "arm_c_liq500k"  "${CONFIGS_DIR}/arm_c_liq500k.json"
run_arm "arm_d_liq1m"    "${CONFIGS_DIR}/arm_d_liq1m.json"
run_arm "arm_e_liq2m"    "${CONFIGS_DIR}/arm_e_liq2m.json"
run_arm "arm_f_liq5m"    "${CONFIGS_DIR}/arm_f_liq5m.json"
run_arm "arm_g_liq10m"   "${CONFIGS_DIR}/arm_g_liq10m.json"

echo ""
echo "=== Experiment 019 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
