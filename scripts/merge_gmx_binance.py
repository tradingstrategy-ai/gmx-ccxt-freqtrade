#!/usr/bin/env python3
"""Merge GMX and Binance futures data to create a gap-free dataset.

Creates user_data/data/gmx_complete/futures/ with:
- Chainlink tokens copied as-is (clean oracle data)
- Non-Chainlink tokens gap-filled with Binance data where available
- All non-futures files (mark, funding_rate, open_interest, pool_liquidity) copied as-is

Only fills INTERNAL gaps (never extends backwards past GMX listing date).
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
GMX_DIR = BASE_DIR / "user_data" / "data" / "gmx" / "futures"
BINANCE_DIR = BASE_DIR / "user_data" / "data" / "binance" / "futures"
OUTPUT_DIR = BASE_DIR / "user_data" / "data" / "gmx_complete" / "futures"

# 33 Chainlink tokens — already have clean data, copy as-is
CHAINLINK_TOKENS = {
    "AAVE", "APE", "ARB", "ATOM", "AVAX", "BNB", "BTC", "CRV", "DAI",
    "DOGE", "ETH", "GMX", "LDO", "LINK", "LTC", "MKR", "NEAR", "OP",
    "PENDLE", "PEPE", "POL", "SEI", "SHIB", "SOL", "STETH", "TAO", "UNI",
    "USDC", "USDC.e", "USDT", "WBTC.b", "WIF", "XRP",
}

# GMX name -> Binance name (for tokens with different naming)
GMX_TO_BINANCE_NAME = {
    "BONK": "1000BONK",
    "FLOKI": "1000FLOKI",
}

# Price divisors for 1000x tokens
PRICE_DIVISORS = {
    "BONK": 1000,
    "FLOKI": 1000,
}

TIMEFRAMES_TO_MERGE = ["5m", "1h", "4h", "1d"]

TIMEFRAME_DELTAS = {
    "5m": pd.Timedelta(minutes=5),
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def discover_gmx_tokens() -> dict[str, list[Path]]:
    """Return {token_name: [list of feather files]} for all GMX tokens."""
    tokens: dict[str, list[Path]] = {}
    for f in sorted(GMX_DIR.glob("*.feather")):
        # e.g. BTC_USDC_USDC-1d-futures.feather -> token = BTC
        name = f.stem  # BTC_USDC_USDC-1d-futures
        token = name.split("_USDC_USDC-")[0] if "_USDC_USDC-" in name else None
        if token is None:
            continue
        tokens.setdefault(token, []).append(f)
    return tokens


def discover_binance_tokens() -> set[str]:
    """Return set of token names available in Binance data."""
    tokens = set()
    for f in BINANCE_DIR.glob("*.feather"):
        name = f.stem
        token = name.split("_USDT_USDT-")[0] if "_USDT_USDT-" in name else None
        if token:
            tokens.add(token)
    return tokens


def get_binance_name(gmx_token: str) -> str:
    """Map GMX token name to Binance token name."""
    return GMX_TO_BINANCE_NAME.get(gmx_token, gmx_token)


def binance_file_for(gmx_token: str, timeframe: str) -> Path:
    """Return the Binance feather file path for a given GMX token and timeframe."""
    bn_name = get_binance_name(gmx_token)
    return BINANCE_DIR / f"{bn_name}_USDT_USDT-{timeframe}-futures.feather"


def is_futures_file(path: Path, timeframe: str | None = None) -> bool:
    """Check if a file is a futures OHLCV file (not mark, funding_rate, etc.)."""
    stem = path.stem
    if timeframe:
        return stem.endswith(f"-{timeframe}-futures")
    return stem.endswith("-futures") and not any(
        stem.endswith(f"-{x}")
        for x in ["mark", "funding_rate"]
    ) and "open_interest" not in stem and "pool_liquidity" not in stem


def parse_timeframe(path: Path) -> str | None:
    """Extract timeframe from filename like BTC_USDC_USDC-1h-futures.feather."""
    stem = path.stem
    parts = stem.split("-")
    if len(parts) >= 3:
        return parts[-2]  # e.g. "1h"
    return None


def load_feather(path: Path) -> pd.DataFrame:
    """Load a feather file and ensure date column is proper datetime."""
    df = pd.read_feather(path)
    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True)
    return df


def find_gaps(df: pd.DataFrame, timeframe: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Find internal gaps in a sorted OHLCV dataframe.

    Returns list of (gap_start, gap_end) tuples where gap_start is the first
    missing timestamp and gap_end is the last missing timestamp.
    """
    if df.empty or len(df) < 2:
        return []

    delta = TIMEFRAME_DELTAS[timeframe]
    dates = df["date"].sort_values().reset_index(drop=True)

    # Find where consecutive differences exceed the expected delta
    diffs = dates.diff()
    gap_mask = diffs > delta

    gaps = []
    for idx in gap_mask[gap_mask].index:
        gap_start = dates.iloc[idx - 1] + delta  # first missing candle
        gap_end = dates.iloc[idx] - delta  # last missing candle
        if gap_start <= gap_end:
            gaps.append((gap_start, gap_end))

    return gaps


def fill_gaps_with_binance(
    gmx_df: pd.DataFrame,
    binance_path: Path,
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]],
    gmx_token: str,
) -> tuple[pd.DataFrame, int]:
    """Fill gaps in GMX data with Binance data. Returns (merged_df, candles_filled)."""
    if not binance_path.exists():
        return gmx_df, 0

    bn_df = load_feather(binance_path)
    if bn_df.empty:
        return gmx_df, 0

    divisor = PRICE_DIVISORS.get(gmx_token, 1)
    if divisor != 1:
        for col in ["open", "high", "low", "close"]:
            bn_df[col] = bn_df[col] / divisor
        bn_df["volume"] = bn_df["volume"] * divisor

    # Collect Binance rows that fall within gap periods
    fill_rows = []
    for gap_start, gap_end in gaps:
        mask = (bn_df["date"] >= gap_start) & (bn_df["date"] <= gap_end)
        chunk = bn_df[mask]
        if not chunk.empty:
            fill_rows.append(chunk)

    if not fill_rows:
        return gmx_df, 0

    fill_df = pd.concat(fill_rows, ignore_index=True)
    candles_filled = len(fill_df)

    # Merge: concat, sort, deduplicate (prefer GMX rows)
    merged = pd.concat([gmx_df, fill_df], ignore_index=True)
    merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="first")
    merged = merged.reset_index(drop=True)

    return merged, candles_filled


def copy_file(src: Path, dst: Path) -> None:
    """Copy a file, creating parent directories as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 70)
    print("GMX + Binance Data Merger")
    print("=" * 70)
    print(f"GMX source:     {GMX_DIR}")
    print(f"Binance source: {BINANCE_DIR}")
    print(f"Output:         {OUTPUT_DIR}")
    print()

    if not GMX_DIR.exists():
        print(f"ERROR: GMX directory not found: {GMX_DIR}")
        sys.exit(1)
    if not BINANCE_DIR.exists():
        print(f"ERROR: Binance directory not found: {BINANCE_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Discover tokens
    gmx_tokens = discover_gmx_tokens()
    binance_tokens = discover_binance_tokens()

    print(f"GMX tokens found:     {len(gmx_tokens)}")
    print(f"Binance tokens found: {len(binance_tokens)}")
    print()

    # Stats
    stats = {
        "chainlink_copied": 0,
        "merged": 0,
        "gmx_only_copied": 0,
        "total_gaps_found": 0,
        "total_candles_filled": 0,
        "total_files_copied": 0,
    }

    merge_details = []

    for token in sorted(gmx_tokens.keys()):
        files = gmx_tokens[token]
        is_chainlink = token in CHAINLINK_TOKENS
        bn_name = get_binance_name(token)
        has_binance = bn_name in binance_tokens

        if is_chainlink:
            # Copy all files as-is
            for f in files:
                dst = OUTPUT_DIR / f.name
                copy_file(f, dst)
                stats["total_files_copied"] += 1
            stats["chainlink_copied"] += 1
            continue

        if not has_binance:
            # No Binance equivalent — copy as-is
            for f in files:
                dst = OUTPUT_DIR / f.name
                copy_file(f, dst)
                stats["total_files_copied"] += 1
            stats["gmx_only_copied"] += 1
            continue

        # Non-Chainlink with Binance match — process futures files, copy rest
        token_gaps = 0
        token_filled = 0

        for f in files:
            dst = OUTPUT_DIR / f.name
            tf = parse_timeframe(f)

            # Only merge futures files for target timeframes
            if tf in TIMEFRAMES_TO_MERGE and is_futures_file(f, tf):
                gmx_df = load_feather(f)
                gaps = find_gaps(gmx_df, tf)

                if gaps:
                    bn_path = binance_file_for(token, tf)
                    merged_df, filled = fill_gaps_with_binance(
                        gmx_df, bn_path, gaps, token
                    )
                    token_gaps += len(gaps)
                    token_filled += filled
                    stats["total_gaps_found"] += len(gaps)
                    stats["total_candles_filled"] += filled

                    # Write merged data
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    pf.write_feather(merged_df, dst)
                    stats["total_files_copied"] += 1
                else:
                    # No gaps — copy as-is
                    copy_file(f, dst)
                    stats["total_files_copied"] += 1
            else:
                # Non-futures file or non-target timeframe — copy as-is
                copy_file(f, dst)
                stats["total_files_copied"] += 1

        stats["merged"] += 1

        if token_gaps > 0:
            merge_details.append((token, token_gaps, token_filled))

    # ---------------------------------------------------------------------------
    # Summary Report
    # ---------------------------------------------------------------------------
    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"Chainlink tokens (copied as-is):      {stats['chainlink_copied']}")
    print(f"Non-Chainlink merged with Binance:     {stats['merged']}")
    print(f"GMX-only (no Binance, copied as-is):   {stats['gmx_only_copied']}")
    print(f"Total files written:                   {stats['total_files_copied']}")
    print(f"Total gaps found:                      {stats['total_gaps_found']}")
    print(f"Total candles filled from Binance:     {stats['total_candles_filled']}")
    print()

    if merge_details:
        print("TOKENS WITH GAPS FILLED:")
        print(f"  {'Token':<20} {'Gaps':>6} {'Candles Filled':>16}")
        print(f"  {'-'*20} {'-'*6} {'-'*16}")
        for token, gaps, filled in sorted(merge_details):
            print(f"  {token:<20} {gaps:>6} {filled:>16}")
    else:
        print("No gaps found in any non-Chainlink token — all data was clean!")

    print()
    print(f"Output directory: {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
