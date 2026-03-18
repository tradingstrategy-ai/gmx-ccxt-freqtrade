#!/bin/bash
# Experiment 020: V2+WC vs V3+WC Final Comparison
#
# Goal: Direct head-to-head using each strategy's own best-found config from
# the full experiment battery (Exp 013-019 for V2, Exp 003-010 for V3).
# Also tests pool cap removal for both strategies.
#
# Arms:
#   A: IchiV2+WC — best config from 013–019
#   B: IchiV2+WC — best config, pool_share=1.0 (no pool cap)
#   C: IchiV2+WC — best config @ 6 slots
#   D: IchiV3+WC — best V3 config (from Exp 003–010)
#   E: IchiV3+WC — best V3 config @ 6 slots
#   F: IchiV3+WC — best V3 config, pool_share=1.0
#
# ⚠ UPDATE THESE PARAMS BEFORE RUNNING based on previous experiment results:
#
#   V2 best params (from Exp 014/015/016/017/018/019):
#     V2_POOL, V2_OI, V2_RATIO, V2_MINPOS, V2_SLOTS, V2_UNIVERSE (number_assets)
#
#   V3 best params (from Exp 003-010):
#     V3_POOL, V3_OI, V3_RATIO, V3_MINPOS, V3_SLOTS
#
#   Config pairlist (update arm configs' number_assets if V2 best universe != 100):
#     Arm configs currently use vol100 pairlist; update arm_a/b/c configs if needed.
#
# Usage: bash run_020.sh 2>&1 | tee run_020_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

V2WC_STRATEGY="IchiV2_LS_Static_WhaleCap"
V2WC_JSON="user_data/strategies/IchiV2_LS_Static_WhaleCap.json"
V3WC_STRATEGY="IchiV3_LS_Static_WhaleCap"
V3WC_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"

SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv2-gmx/020-v2wc-vs-v3wc-final/results"
CONFIGS_DIR="experiments/ichiv2-gmx/020-v2wc-vs-v3wc-final/configs"

# ── V2 best params (UPDATE THESE based on Exp 013-019 results) ────────────────
V2_POOL="${V2_POOL:-1.0}"
V2_OI="${V2_OI:-0.05}"
V2_RATIO="${V2_RATIO:-0.10}"
V2_MINPOS="${V2_MINPOS:-0.01}"
V2_SLOTS="${V2_SLOTS:-10}"

# ── V3 best params (UPDATE THESE based on Exp 003-010 results) ────────────────
V3_POOL="${V3_POOL:-0.02}"
V3_OI="${V3_OI:-0.025}"
V3_RATIO="${V3_RATIO:-0.10}"
V3_MINPOS="${V3_MINPOS:-0.01}"
V3_SLOTS="${V3_SLOTS:-10}"

V2_BASE_PARAMS=$(cat user_data/strategies/IchiV2_LS_Static.json)
V3WC_JSON_ORIG=$(cat "$V3WC_JSON")

restore_jsons() {
    rm -f "$V2WC_JSON"
    echo "$V3WC_JSON_ORIG" > "$V3WC_JSON"
    echo "Restored strategy JSONs."
}
trap restore_jsons EXIT

write_v2wc_json() {
    local pool="$1"
    local oi="$2"
    local slots="$3"
    python3 -c "
import json
base = json.loads('''${V2_BASE_PARAMS}''')
base['strategy_name'] = '${V2WC_STRATEGY}'
base['params']['max_open_trades']['max_open_trades'] = ${slots}
base['params']['buy']['max_pool_share']   = ${pool}
base['params']['buy']['max_oi_share']     = ${oi}
base['params']['buy']['min_stake_ratio']  = ${V2_RATIO}
base['params']['buy']['min_position_pct'] = ${V2_MINPOS}
with open('${V2WC_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

write_v3wc_json() {
    local pool="$1"
    local oi="$2"
    local slots="$3"
    python3 -c "
import json
base = json.loads('''${V3WC_JSON_ORIG}''')
base['params']['max_open_trades']['max_open_trades'] = ${slots}
base['params']['buy']['max_pool_share']   = ${pool}
base['params']['buy']['max_oi_share']     = ${oi}
base['params']['buy']['min_stake_ratio']  = ${V3_RATIO}
base['params']['buy']['min_position_pct'] = ${V3_MINPOS}
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
        echo "=== SKIP $label (result exists) ==="
        return 0
    fi

    echo ""
    echo "=============================================="
    echo "=== $label (strategy=${strategy})"
    echo "=============================================="

    local before_zips
    before_zips=$(ls user_data/backtest_results/backtest-result-*.zip 2>/dev/null | sort || true)

    ./freqtrade-gmx backtesting \
        --strategy "$strategy" \
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
        return 1
    fi
}

mkdir -p "$RESULTS_DIR"

echo "=== Experiment 020: V2+WC vs V3+WC Final Comparison ==="
echo "=== V2 params: pool=${V2_POOL} oi=${V2_OI} ratio=${V2_RATIO} minpos=${V2_MINPOS} slots=${V2_SLOTS} ==="
echo "=== V3 params: pool=${V3_POOL} oi=${V3_OI} ratio=${V3_RATIO} minpos=${V3_MINPOS} slots=${V3_SLOTS} ==="
echo "=== Started: $(date) ==="

# Arm A: V2+WC — best config
write_v2wc_json "$V2_POOL" "$V2_OI" "$V2_SLOTS"
run_arm "arm_a_v2wc_best" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_a_v2wc_best.json"

# Arm B: V2+WC — best config, no pool cap
write_v2wc_json 1.0 "$V2_OI" "$V2_SLOTS"
run_arm "arm_b_v2wc_no_pool" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_b_v2wc_no_pool.json"

# Arm C: V2+WC — best config @ 6 slots
write_v2wc_json "$V2_POOL" "$V2_OI" 6
run_arm "arm_c_v2wc_6slots" "$V2WC_STRATEGY" "${CONFIGS_DIR}/arm_c_v2wc_6slots.json"

# Arm D: V3+WC — best V3 config
write_v3wc_json "$V3_POOL" "$V3_OI" "$V3_SLOTS"
run_arm "arm_d_v3wc_best" "$V3WC_STRATEGY" "${CONFIGS_DIR}/arm_d_v3wc_best.json"

# Arm E: V3+WC — best V3 config @ 6 slots
write_v3wc_json "$V3_POOL" "$V3_OI" 6
run_arm "arm_e_v3wc_6slots" "$V3WC_STRATEGY" "${CONFIGS_DIR}/arm_e_v3wc_6slots.json"

# Arm F: V3+WC — best V3 config, no pool cap
write_v3wc_json 1.0 "$V3_OI" "$V3_SLOTS"
run_arm "arm_f_v3wc_no_pool" "$V3WC_STRATEGY" "${CONFIGS_DIR}/arm_f_v3wc_no_pool.json"

echo ""
echo "=== Experiment 020 COMPLETE ==="
echo "=== Finished: $(date) ==="
ls -la "$RESULTS_DIR"
