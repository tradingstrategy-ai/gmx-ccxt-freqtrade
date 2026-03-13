#!/usr/bin/env bash
# Download missing 1h/4h/1d futures data for non-Chainlink GMX tokens
# from Binance (43), Bybit (3: CRO, MNT, PI), and OKX (2: OKB, OM),
# then copy/rename into GMX format.
#
# NOTE: KTA and WELL are GMX-native perps with no CEX listing.
#       Fetch them separately via GMXAPI (see scripts/fetch_kta_well_gmx.py).
#
# NOTE: All downloads land in $TMP_DIR/data/futures/ (flat dir, no exchange
#       subdirectory) regardless of source exchange — that is how freqtrade-gmx
#       stores data. The copy step reads from that single directory.
#
# Usage:
#   bash scripts/download_missing_gmx_data.sh             # fetch all available history
#   bash scripts/download_missing_gmx_data.sh 20240101-   # from specific date
#
# Requirements: my-strategies repo at ../my-strategies (relative to this repo)

set -euo pipefail

TIMERANGE="${1:-}"   # empty = no --timerange flag → download oldest available data
MYSTRATEGIES_DIR="$(cd "$(dirname "$0")/../.." && pwd)/my-strategies"
TMP_DIR="/private/tmp/ft-dl-userdata"
TMP_DATA_DIR="$TMP_DIR/data/futures"   # freqtrade-gmx stores here (flat, no exchange subdir)
GMX_DIR="$(cd "$(dirname "$0")/.." && pwd)/user_data/data/gmx/futures"
FT_CMD="$MYSTRATEGIES_DIR/scripts/freqtrade-gmx"

TIMERANGE_LABEL="${TIMERANGE:-all available history}"
echo "=================================================="
echo " GMX missing data downloader"
echo " Timerange : $TIMERANGE_LABEL"
echo " Tmp dir   : $TMP_DATA_DIR"
echo " GMX dest  : $GMX_DIR"
echo "=================================================="
echo ""

# ── helpers ────────────────────────────────────────────────────────────────

run_download() {
    local exchange_config="$1"
    local label="$2"
    echo ">>> Downloading [$label] ..."
    "$FT_CMD" download-data \
        --config "$MYSTRATEGIES_DIR/freqtrade_start/configs/$exchange_config" \
        ${TIMERANGE:+--timerange "$TIMERANGE"} \
        --timeframes 1h 4h 1d \
        --trading-mode futures \
        --datadir "$TMP_DIR/data" \
        --prepend \
        || echo "WARN: some pairs may have failed for $label — continuing"
    echo ""
}

copy_rename() {
    local label="$1"
    echo ">>> Copying [$label] files to GMX dir ..."

    local copied=0

    # Copy futures, mark, and funding_rate files
    for f in "$TMP_DATA_DIR"/*_USDT_USDT-*.feather; do
        [ -f "$f" ] || continue
        base=$(basename "$f")

        token="${base%%_USDT_USDT-*}"
        suffix="${base#*_USDT_USDT-}"   # e.g. "1h-futures.feather", "1h-mark.feather"

        # Apply naming overrides (exchange symbol → GMX symbol)
        case "$token" in
            1000BONK)   gmx_token="BONK" ;;
            1000SATS)   gmx_token="SATS" ;;
            SPX)        gmx_token="SPX6900" ;;
            *)          gmx_token="$token" ;;
        esac

        dest="$GMX_DIR/${gmx_token}_USDC_USDC-${suffix}"
        cp "$f" "$dest"
        echo "  $base  →  $(basename "$dest")"
        ((copied++))
    done

    echo "  Copied $copied files"
    echo ""
}

# ── Step 1: Binance (43 tokens) ────────────────────────────────────────────

run_download "config_binance_gmx_missing_v2.json" "Binance (43 tokens)"

# ── Step 2: Bybit (CRO, MNT, PI) ──────────────────────────────────────────

run_download "config_bybit_gmx_missing.json" "Bybit (CRO, MNT, PI)"

# ── Step 3: OKX (OKB, OM) ──────────────────────────────────────────────────

run_download "config_okx_gmx_missing.json" "OKX (OKB, OM)"

# ── Step 4: Copy all downloaded files to GMX dir ──────────────────────────
# All exchanges write to the same flat $TMP_DATA_DIR regardless of exchange name.

copy_rename "all exchanges"

# ── Step 4b: Synthesize missing and refresh stale mark/index files ────────
# Delegates to fix_gmx_data_types.py which handles:
#   - missing mark (GMXAPI-only tokens with no CEX listing)
#   - missing index (CEX exchanges don't provide index candles)
#   - stale mark/index (CEX downloads only provide 1h mark; 4h/1d become
#     stale after a re-download with a longer timerange)

echo ">>> Fixing mark/index files (missing + stale) ..."
python3 "$(dirname "$0")/fix_gmx_data_types.py" "$GMX_DIR"
echo ""

# ── Step 5: Verification ──────────────────────────────────────────────────

echo "=================================================="
echo " Verification — checking all 48 CEX-sourced tokens"
echo "=================================================="
echo ""

CEX_TOKENS=(AERO AIXBT ALGO ANIME AR AVNT BERA BONK BRETT CC CHZ CRO CVX
            DASH DOLO DYDX EIGEN FET FIL HBAR ICP IP JTO JUP KAS
            LIT MELANIA MET MNT MON MORPHO OKB OM ORDI PI RENDER S SATS
            SKY SPX6900 STX SYRUP TIA VIRTUAL VVV XMR ZEC ZRO)

ok=0
missing=0

for token in "${CEX_TOKENS[@]}"; do
    has_all=true
    for tf in 1h 4h 1d; do
        f="$GMX_DIR/${token}_USDC_USDC-${tf}-futures.feather"
        [ -f "$f" ] || { has_all=false; break; }
    done

    if $has_all; then
        echo "  OK    $token"
        ((ok++))
    else
        echo "  MISS  $token  (check manually)"
        ((missing++))
    fi
done

echo ""
echo "Result: $ok / ${#CEX_TOKENS[@]} downloaded, $missing still missing"
echo ""
echo "Note: KTA and WELL are fetched separately via GMXAPI — not checked here."
echo ""
echo "Done. Run backtest with:"
echo "  just backtest ichiv2_ls_gmx_backtest_full IchiV2_LS_Static --timeframe-detail 5m"
