#!/usr/bin/env bash
# fetch_all_gmx_data.sh
# =====================
# Download ALL data needed for GMX backtesting in one command.
#
# What this does (in order):
#   Step 1 — GMX API download
#             Downloads directly from GMX oracle for all pairs in the full
#             backtest config (1h, 4h, 1d, 15m). These are the canonical
#             on-chain prices used for trade execution.
#
#   Step 2 — CEX supplement download
#             Some tokens have much longer price history on centralised
#             exchanges (Binance, Bybit, OKX) than GMX keeps on-chain.
#             Downloads 1h/4h/1d for the 48 CEX-sourced tokens and copies
#             them into the GMX data dir with USDC_USDC naming.
#
#   Step 3 — Fix mark / index files
#             CEX downloads don't include index candles, and 4h/1d mark
#             files are not provided by Binance. Synthesises missing files
#             and refreshes any stale ones so every token has the full
#             required set: futures + mark + index + funding_rate.
#
#   Step 4 — Clean up /tmp
#             Removes the temporary CEX download cache to free disk space.
#
# Usage:
#   bash scripts/fetch_all_gmx_data.sh             # all available history
#   bash scripts/fetch_all_gmx_data.sh 20230101-   # from specific date
#
# Requirements:
#   - my-strategies repo at ../my-strategies (for CEX download configs)
#   - ./freqtrade-gmx wrapper in repo root

set -euo pipefail

TIMERANGE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GMX_DIR="$REPO_ROOT/user_data/data/gmx/futures"
TMP_DATA_DIR="/private/tmp/ft-dl-userdata/data"

echo "=================================================="
echo " GMX full data fetch"
echo " Timerange : ${TIMERANGE:-all available history}"
echo " GMX dest  : $GMX_DIR"
echo "=================================================="
echo ""

# ── Step 1: GMX API (all pairs, all timeframes) ────────────────────────────
# Downloads oracle price data directly from Arbitrum via freqtrade-gmx.
# Uses --prepend to extend existing data backwards without re-fetching what
# we already have.

echo ">>> Step 1: GMX API — downloading all pairs (1h, 4h, 1d, 15m) ..."
cd "$REPO_ROOT"
./freqtrade-gmx download-data \
    --config configs/ichiv2_ls_gmx_backtest_full.json \
    --config configs/ichiv2_ls_gmx_backtest_chainlink.secrets.json \
    --timeframes 1h 4h 1d 15m \
    --trading-mode futures \
    --datadir user_data/data \
    --prepend \
    ${TIMERANGE:+--timerange "$TIMERANGE"} \
    || echo "WARN: some GMX API pairs may have failed — continuing"
echo ""

# ── Step 2: CEX supplement (Binance / Bybit / OKX) ────────────────────────
# For tokens where Binance/Bybit/OKX have longer history than GMX on-chain.
# The download script handles copy/rename to USDC_USDC format and runs
# fix_gmx_data_types.py at the end.

echo ">>> Step 2: CEX supplement — Binance / Bybit / OKX ..."
bash "$SCRIPT_DIR/download_missing_gmx_data.sh" ${TIMERANGE:+"$TIMERANGE"}
echo ""

# ── Step 3: Final fix pass ─────────────────────────────────────────────────
# Re-run the fixer in case the GMX API download in Step 1 introduced new
# gaps (e.g. a newly listed token now has futures but no mark/index yet).

echo ">>> Step 3: Final fix pass (mark / index) ..."
python3 "$SCRIPT_DIR/fix_gmx_data_types.py" "$GMX_DIR"
echo ""

# ── Step 4: Clean up /tmp ──────────────────────────────────────────────────
# The CEX download cache is no longer needed once data is copied to GMX dir.

echo ">>> Step 4: Cleaning up /tmp cache ..."
if [ -d "$TMP_DATA_DIR" ]; then
    rm -rf "$TMP_DATA_DIR"
    echo "  Removed $TMP_DATA_DIR"
else
    echo "  $TMP_DATA_DIR not found — nothing to clean"
fi
echo ""

echo "=================================================="
echo " All done."
echo " Run backtest with:"
echo "   just backtest ichiv2_ls_gmx_backtest_full IchiV2_LS_Static --timeframe-detail 15m"
echo "=================================================="
