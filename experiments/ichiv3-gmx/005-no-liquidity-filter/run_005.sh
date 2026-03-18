#!/bin/bash
# Experiment 005: No Liquidity Filter
#
# Hypothesis (Mikko): The static 500k liquidity filter is redundant given
# we're already capping position size dynamically by OI. The GMX universe
# is small enough that filtering may exclude pairs we could trade at
# appropriate size. Let OI cap do the weighting.
#
# Arms:
#   A (baseline): Vol75 + Liq $500k filter + OI cap + pool cap (current best)
#   B: Vol75 + OI cap only (no liq filter, no pool cap)
#   C: Vol100 + OI cap only (wider universe)
#   D: All 107 pairs + OI cap only (no volume filter, no liq filter)
#
# All arms use IchiV3_LS_Static_WhaleCap with mcap sizing.
# Arms B/C/D set max_pool_share=1.0 to effectively disable pool cap.
#
# Usage: bash run_005.sh

set -euo pipefail

cd /home/ubuntu/dev/gmx-ccxt-freqtrade

STRATEGY="IchiV3_LS_Static_WhaleCap"
STRATEGY_JSON="user_data/strategies/IchiV3_LS_Static_WhaleCap.json"
SECRETS_CONFIG="configs/ichiv2_gmx_full_universe.secrets.json"
DATADIR="user_data/data/gmx_complete_w_binance"
TIMERANGE="20210106-20260312"
RESULTS_DIR="experiments/ichiv3-gmx/005-no-liquidity-filter/results"
CONFIGS_DIR="experiments/ichiv3-gmx/005-no-liquidity-filter/configs"
LOG_FILE="experiments/ichiv3-gmx/005-no-liquidity-filter/run_005_log.txt"

# Base strategy params from IchiV3_LS_Static.json
BASE_PARAMS=$(cat user_data/strategies/IchiV3_LS_Static.json)

write_strategy_json() {
    local pool_share="$1"
    local oi_share="$2"
    local stake_ratio="$3"
    local min_pos_pct="$4"

    python3 -c "
import json

base = json.loads('''${BASE_PARAMS}''')
base['strategy_name'] = '${STRATEGY}'
base['params']['buy']['max_pool_share'] = ${pool_share}
base['params']['buy']['max_oi_share'] = ${oi_share}
base['params']['buy']['min_stake_ratio'] = ${stake_ratio}
base['params']['buy']['min_position_pct'] = ${min_pos_pct}

with open('${STRATEGY_JSON}', 'w') as f:
    json.dump(base, f, indent=2)
"
}

run_arm() {
    local label="$1"
    local config="$2"
    local pool_share="$3"
    local oi_share="$4"
    local stake_ratio="$5"
    local min_pos_pct="$6"

    local result_file="${RESULTS_DIR}/${label}.zip"

    if [ -f "$result_file" ]; then
        echo "=== SKIP $label (result exists) ===" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "" | tee -a "$LOG_FILE"
    echo "==============================================" | tee -a "$LOG_FILE"
    echo "=== $label: pool=${pool_share} oi=${oi_share} ratio=${stake_ratio} minpos=${min_pos_pct}" | tee -a "$LOG_FILE"
    echo "==============================================" | tee -a "$LOG_FILE"

    write_strategy_json "$pool_share" "$oi_share" "$stake_ratio" "$min_pos_pct"

    ./freqtrade-gmx backtesting \
        --strategy "$STRATEGY" \
        --config "$config" \
        --config "$SECRETS_CONFIG" \
        --datadir "$DATADIR" \
        --timeframe 1h \
        --timerange "$TIMERANGE" \
        --cache none \
        2>&1 | tail -30 | tee -a "$LOG_FILE"

    # Copy latest result zip
    LATEST_ZIP=$(ls -t user_data/backtest_results/backtest-result-*.zip 2>/dev/null | head -1)
    if [ -n "$LATEST_ZIP" ]; then
        cp "$LATEST_ZIP" "$result_file"
        echo "=== $label DONE — saved to $result_file ===" | tee -a "$LOG_FILE"
    else
        echo "=== $label DONE — WARNING: no zip found ===" | tee -a "$LOG_FILE"
    fi
}

mkdir -p "$RESULTS_DIR"
echo "=== Experiment 005: No Liquidity Filter ===" | tee "$LOG_FILE"
echo "=== Started: $(date) ===" | tee -a "$LOG_FILE"

# Arm A (baseline): Vol75 + Liq $500k + OI cap + pool cap
# Uses current best params from experiment 004: pool=0.02, oi=0.025, ratio=0.10, minpos=0.01
run_arm "arm_a_vol75_liq_oi" \
    "${CONFIGS_DIR}/arm_a_vol75_liq_oi.json" \
    0.02 0.025 0.10 0.01

# Arm B: Vol75 + OI cap only (no liq filter, pool cap disabled)
run_arm "arm_b_vol75_oi" \
    "${CONFIGS_DIR}/arm_b_vol75_oi.json" \
    1.0 0.025 0.10 0.01

# Arm C: Vol100 + OI cap only (wider universe, no liq filter)
run_arm "arm_c_vol100_oi" \
    "${CONFIGS_DIR}/arm_c_vol100_oi.json" \
    1.0 0.025 0.10 0.01

# Arm D: All 107 pairs + OI cap only (no volume filter, no liq filter)
run_arm "arm_d_all_pairs_oi" \
    "${CONFIGS_DIR}/arm_d_all_pairs_oi.json" \
    1.0 0.025 0.10 0.01

echo "" | tee -a "$LOG_FILE"
echo "=== Experiment 005 COMPLETE ===" | tee -a "$LOG_FILE"
echo "=== Finished: $(date) ===" | tee -a "$LOG_FILE"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG_FILE"
ls -la "$RESULTS_DIR" | tee -a "$LOG_FILE"

# Restore original strategy JSON
cat > "$STRATEGY_JSON" << 'RESTORE'
{
  "strategy_name": "IchiV3_LS_Static_WhaleCap",
  "params": {
    "roi": {
      "0": 10.0
    },
    "stoploss": {
      "stoploss": -0.129
    },
    "trailing": {
      "trailing_stop": false,
      "trailing_stop_positive": null,
      "trailing_stop_positive_offset": null,
      "trailing_only_offset_is_reached": false
    },
    "max_open_trades": {
      "max_open_trades": 10
    },
    "buy": {
      "daily_cloud_regime_enabled": true,
      "long_daily_cloud_filter": "green_cloud",
      "mcap_blue_chip_multiplier": 1.0,
      "mcap_blue_chip_threshold": 100.0,
      "mcap_degen_multiplier": 1.5,
      "mcap_large_cap_multiplier": 2.0,
      "mcap_large_cap_threshold": 10.0,
      "mcap_mid_cap_multiplier": 2.0,
      "mcap_mid_cap_threshold": 1.0,
      "per_pair_cap_pct": 0.2,
      "price_velocity_window": 10,
      "retest_lookback_window": 24,
      "max_pool_share": 0.02,
      "max_oi_share": 0.025,
      "min_stake_ratio": 0.1,
      "min_position_pct": 0.01
    },
    "sell": {
      "atr_stop_multiplier": 3.1,
      "rsi_tp_threshold": 25,
      "short_atr_trailing_activation": 0.03,
      "short_atr_trailing_enabled": true,
      "short_atr_trailing_multiplier": 6.1,
      "short_daily_cloud_filter": "all",
      "short_hard_stoploss": 0.071,
      "use_rsi_exit": 1,
      "velocity_tp_threshold": -0.098
    },
    "protection": {}
  },
  "ft_stratparam_v": 1,
  "export_time": "2026-03-06 17:59:23.444875+00:00"
}
RESTORE
echo "Restored ${STRATEGY_JSON}"
