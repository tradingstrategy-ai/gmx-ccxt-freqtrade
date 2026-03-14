#!/usr/bin/env python3
"""Create gmx_complete_w_binance by copying gmx_complete and prepending Binance 1h/5m data.

For each token:
1. Find the token's earliest date across ALL timeframes in gmx_complete (= GMX listing date)
2. For 1h and 5m: if their start date is later than the listing date, prepend Binance data
   from listing_date up to where the GMX 1h/5m data begins
3. Tokens that only appeared recently (all timeframes start ~same date) get no backfill

This creates a new directory so the original gmx_complete is preserved.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd
import pyarrow.feather as pf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "user_data" / "data" / "gmx_complete"
OUTPUT_DIR = BASE_DIR / "user_data" / "data" / "gmx_complete_w_binance"
BINANCE_DIR = BASE_DIR / "user_data" / "data" / "binance" / "futures"

# GMX name -> Binance name
GMX_TO_BINANCE_NAME = {
    "BONK": "1000BONK",
    "FLOKI": "1000FLOKI",
}

PRICE_DIVISORS = {
    "BONK": 1000,
    "FLOKI": 1000,
}

TIMEFRAMES_TO_BACKFILL = ["1h", "5m"]

# Minimum gap (days) between earliest date and 1h/5m start to warrant backfill
MIN_GAP_DAYS = 7


def get_binance_name(gmx_token: str) -> str:
    return GMX_TO_BINANCE_NAME.get(gmx_token, gmx_token)


def main() -> None:
    print("=" * 70)
    print("Backfill 1h/5m from Binance into gmx_complete_w_binance")
    print("=" * 70)

    if not SRC_DIR.exists():
        print(f"ERROR: Source directory not found: {SRC_DIR}")
        sys.exit(1)
    if not BINANCE_DIR.exists():
        print(f"ERROR: Binance directory not found: {BINANCE_DIR}")
        sys.exit(1)

    # Step 1: Copy gmx_complete -> gmx_complete_w_binance
    if OUTPUT_DIR.exists():
        print(f"Removing existing output directory: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    print(f"Copying {SRC_DIR} -> {OUTPUT_DIR} ...")
    shutil.copytree(SRC_DIR, OUTPUT_DIR)
    print("Copy complete.")
    print()

    # Step 2: Discover per-token earliest dates from gmx_complete/futures
    futures_dir = OUTPUT_DIR / "futures"
    token_dates: dict[str, dict[str, pd.Timestamp]] = {}

    for f in sorted(futures_dir.glob("*-futures.feather")):
        stem = f.stem
        if "_USDC_USDC-" not in stem:
            continue
        token = stem.split("_USDC_USDC-")[0]
        tf = stem.split("_USDC_USDC-")[1].replace("-futures", "")
        token_dates.setdefault(token, {})
        df = pd.read_feather(f)
        token_dates[token][tf] = df["date"].min()

    print(f"Tokens discovered: {len(token_dates)}")

    # Step 3: For each token, backfill 1h and 5m
    stats = {"backfilled": 0, "skipped_no_gap": 0, "skipped_no_binance": 0, "total_candles": 0}
    details = []

    for token in sorted(token_dates):
        tfs = token_dates[token]
        earliest = min(tfs.values())

        for tf in TIMEFRAMES_TO_BACKFILL:
            gmx_start = tfs.get(tf)
            if gmx_start is None:
                continue

            gap_days = (gmx_start - earliest).days
            if gap_days < MIN_GAP_DAYS:
                stats["skipped_no_gap"] += 1
                continue

            # Find Binance file
            bn_name = get_binance_name(token)
            bn_path = BINANCE_DIR / f"{bn_name}_USDT_USDT-{tf}-futures.feather"
            if not bn_path.exists():
                stats["skipped_no_binance"] += 1
                print(f"  SKIP {token} {tf}: no Binance file ({bn_name})")
                continue

            # Load both
            gmx_file = futures_dir / f"{token}_USDC_USDC-{tf}-futures.feather"
            if not gmx_file.exists():
                continue

            gmx_df = pd.read_feather(gmx_file)
            bn_df = pd.read_feather(bn_path)

            # Ensure date columns are datetime
            for df in [gmx_df, bn_df]:
                if not pd.api.types.is_datetime64_any_dtype(df["date"]):
                    df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True)

            # Apply price divisor
            divisor = PRICE_DIVISORS.get(token, 1)
            if divisor != 1:
                bn_df = bn_df.copy()
                for col in ["open", "high", "low", "close"]:
                    bn_df[col] = bn_df[col] / divisor
                bn_df["volume"] = bn_df["volume"] * divisor

            # Extract Binance rows from earliest to just before gmx_start
            mask = (bn_df["date"] >= earliest) & (bn_df["date"] < gmx_start)
            prepend_df = bn_df[mask].copy()

            if prepend_df.empty:
                stats["skipped_no_binance"] += 1
                print(f"  SKIP {token} {tf}: Binance has no data in range {str(earliest)[:10]} -> {str(gmx_start)[:10]}")
                continue

            candles = len(prepend_df)
            stats["total_candles"] += candles
            stats["backfilled"] += 1

            # Merge: prepend + original, sort, deduplicate
            merged = pd.concat([prepend_df, gmx_df], ignore_index=True)
            merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="last")  # prefer GMX
            merged = merged.reset_index(drop=True)

            # Write back
            pf.write_feather(merged, gmx_file)
            details.append((token, tf, candles, str(earliest)[:10], str(gmx_start)[:10]))
            print(f"  OK   {token} {tf}: +{candles} candles ({str(earliest)[:10]} -> {str(gmx_start)[:10]})")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files backfilled:           {stats['backfilled']}")
    print(f"Total candles prepended:    {stats['total_candles']}")
    print(f"Skipped (no significant gap): {stats['skipped_no_gap']}")
    print(f"Skipped (no Binance data):    {stats['skipped_no_binance']}")
    print()

    if details:
        print(f"{'Token':<20} {'TF':<5} {'Candles':>10} {'From':<12} {'To':<12}")
        print("-" * 60)
        for token, tf, candles, frm, to in details:
            print(f"{token:<20} {tf:<5} {candles:>10} {frm:<12} {to:<12}")

    print()
    print(f"Output: {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
