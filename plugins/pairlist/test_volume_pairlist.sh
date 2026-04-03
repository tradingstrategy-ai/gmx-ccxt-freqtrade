#!/bin/bash
# =============================================================================
# Test Volume Pairlist - runs test-pairlist in a fresh container
#
# What this does:
#   1. Mounts our custom HistoricalVolumePairList + GMXLiquidityFilter into the container
#   2. Patches freqtrade's config schema to accept our custom pairlist names
#   3. Runs freqtrade test-pairlist (read-only, no trading, exits immediately)
#   4. Shows the full pairlist chain output with detailed logging
#
# What this does NOT do:
#   - No trading (test-pairlist only)
#   - No wallet interaction (dry_run: true)
#   - Does NOT touch running containers
#
# Data sources it will hit:
#   - Binance public API (fetch_tickers, no credentials needed)
#   - GMX REST API (arbitrum-api.gmxinfra.io for market data, via RPC URLs in secrets)
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="gmx-ccxt-freqtrade-adxmomentum_gmx"
PAIRLIST_DIR="${REPO_DIR}/freqtrade-develop/freqtrade/plugins/pairlist"
SCRIPTS_DIR="${REPO_DIR}/scripts"

echo "============================================"
echo " Volume Pairlist Test"
echo "============================================"
echo ""
echo "Image:   ${IMAGE}"
echo "Config:  plugins/pairlist/test_volume_pairlist.json"
echo "Secrets: configs/<your_strategy>.secrets.json (RPC URLs only, dry_run=true)"
echo ""
echo "Custom plugins mounted:"
echo "  - HistoricalVolumePairList.py (Binance volume ranking)"
echo "  - GMXLiquidityFilter.py (GMX pool liquidity filter)"
echo ""
echo "This will:"
echo "  1. Load 107 pairs from StaticPairList"
echo "  2. Fetch Binance futures tickers (public API) -> rank top 40"
echo "  3. Filter by GMX pool liquidity (>= \$500k)"
echo "  4. Print final pairlist and exit"
echo ""
echo "============================================"
echo ""

docker run --rm \
    --entrypoint python \
    -v "${REPO_DIR}/user_data:/freqtrade/user_data" \
    -v "${REPO_DIR}/configs:/freqtrade/configs" \
    -v "${PAIRLIST_DIR}/HistoricalVolumePairList.py:/freqtrade/freqtrade/plugins/pairlist/HistoricalVolumePairList.py:ro" \
    -v "${PAIRLIST_DIR}/GMXLiquidityFilter.py:/freqtrade/freqtrade/plugins/pairlist/GMXLiquidityFilter.py:ro" \
    -v "${SCRIPTS_DIR}/test_pairlist_runner.py:/freqtrade/plugins/pairlist/test_pairlist_runner.py:ro" \
    "${IMAGE}" \
    -u -B /freqtrade/plugins/pairlist/test_pairlist_runner.py \
        --config /freqtrade/plugins/pairlist/test_volume_pairlist.json \
        --config /freqtrade/configs/<your_strategy>.secrets.json \
        -vvv

echo ""
echo "============================================"
echo " Test complete"
echo "============================================"
