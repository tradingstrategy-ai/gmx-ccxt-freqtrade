#!/bin/bash
# Experiment 011: IchiV2 vs IchiV3 — 6-slot vs 10-slot comparison
#
# Hypothesis: IchiV2 @ 6 max_open_trades may outperform IchiV3 @ 10 on a
# risk-adjusted basis, based on live dry-run observations. Fewer slots means
# larger per-slot stake; IchiV2 has no mcap sizing overhead so all capital
# compounds cleanly. This experiment provides the controlled backtest to
# confirm or disprove that intuition.
#
# Arms:
#   A: IchiV2_LS_Static         @ 10 slots  (V2 baseline)
#   B: IchiV2_LS_Static         @  6 slots  (V2 hypothesis)
#   C: IchiV3_LS_Static_WhaleCap @ 10 slots  (V3 baseline, replicates exp006 arm A)
#   D: IchiV3_LS_Static_WhaleCap @  6 slots  (V3 reduced)
#
# All arms: static 107-pair universe, no pairlist filters
# Timerange: 20210106-20260312 (clamps to GMX data start ~2021-07-18)
#
# Usage: bash run_011.sh 2>&1 | tee run_011_log.txt

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

V2_STRATEGY="IchiV2_LS_Static"
V2_JSON="user_data/strategies/IchiV2_LS_Static.json"
V3_STRATEGY="IchiV3_LS_Static_WhaleCap"
V3_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"

SECRETS_CONFIG="configs/ichiv2_gmx_backtest.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/011-v2-vs-v3-slots/results"
CONFIGS_DIR="experiments/ichiv3-gmx/011-v2-vs-v3-slots/configs"

# Snapshot original JSONs so we can restore them
V2_JSON_ORIG=$(cat "$V2_JSON")
V3_JSON_ORIG=$(cat "$V3_JSON")

restore_jsons() {
    echo "$V2_JSON_ORIG" > "$V2_JSON"
    echo "$V3_JSON_ORIG" > "$V3_JSON"
    echo "Restored original strategy JSONs."
}
trap restore_jsons EXIT

write_v2_json() {
    local max_trades="$1"
    python3 -c "
import json
d = json.loads('''${V2_JSON_ORIG}''')
d['strategy_name'] = '${V2_STRATEGY}'
d['params']['max_open_trades']['max_open_trades'] = ${max_trades}
with open('${V2_JSON}', 'w') as f:
    json.dump(d, f, indent=2)
"
}

write_v3_json() {
    local max_trades="$1"
    python3 -c "
import json
d = json.loads('''${V3_JSON_ORIG}''')
d['strategy_name'] = '${V3_STRATEGY}'
d['params']['max_open_trades']['max_open_trades'] = ${max_trades}
with open('${V3_JSON}', 'w') as f:
    json.dump(d, f, indent=2)
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

echo "=== Experiment 011: IchiV2 vs IchiV3 — 6-slot vs 10-slot ==="
echo "=== Started: $(date) ==="

# Arm A: IchiV2 @ 10 slots (V2 baseline)
write_v2_json 10
run_arm "arm_a_v2_10slots" "$V2_STRATEGY" "${CONFIGS_DIR}/arm_a_v2_10slots.json"

# Arm B: IchiV2 @ 6 slots (the hypothesis)
write_v2_json 6
run_arm "arm_b_v2_6slots" "$V2_STRATEGY" "${CONFIGS_DIR}/arm_b_v2_6slots.json"

# Arm C: IchiV3 @ 10 slots (V3 baseline — replicates exp006 arm A)
write_v3_json 10
run_arm "arm_c_v3_10slots" "$V3_STRATEGY" "${CONFIGS_DIR}/arm_c_v3_10slots.json"

# Arm D: IchiV3 @ 6 slots
write_v3_json 6
run_arm "arm_d_v3_6slots" "$V3_STRATEGY" "${CONFIGS_DIR}/arm_d_v3_6slots.json"

echo ""
echo "=== Experiment 011 COMPLETE ==="
echo "=== Finished: $(date) ==="
echo "Results in: $RESULTS_DIR"
ls -la "$RESULTS_DIR"
