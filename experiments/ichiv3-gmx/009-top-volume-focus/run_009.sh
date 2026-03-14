#!/bin/bash
set -euo pipefail
cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV3_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/009-top-volume-focus/results"
CONFIGS_DIR="experiments/ichiv3-gmx/009-top-volume-focus/configs"
BASE_PARAMS=$(cat user_data/strategies/IchiV3_LS_Static.json)

# Write strategy sidecar JSON (same params for all arms)
# OI cap enabled, pool cap enabled, dust filters on
python3 -c "
import json
base = json.loads('''${BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['buy']['max_pool_share'] = 0.02
base['params']['buy']['max_oi_share'] = 0.025
base['params']['buy']['min_stake_ratio'] = 0.10
base['params']['buy']['min_position_pct'] = 0.01
with open('${STRATEGY_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
echo "Wrote ${STRATEGY_JSON}"

ARMS=("arm_a_top20" "arm_b_top30" "arm_c_top15" "arm_d_top25" "arm_e_top10")

for arm in "${ARMS[@]}"; do
    result_file="${RESULTS_DIR}/${arm}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP ${arm} (already exists) ==="
        continue
    fi

    echo "=== ${arm} ==="

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "${CONFIGS_DIR}/${arm}.json" \
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
done

rm -f "$STRATEGY_JSON"
echo ""
echo "=== EXPERIMENT 009 COMPLETE ==="
ls -la "$RESULTS_DIR"
