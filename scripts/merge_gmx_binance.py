#!/usr/bin/env python3
"""Fill internal gaps in GMX futures data using Binance candles.

Operates IN-PLACE on user_data/data/gmx/futures/:
- Non-Chainlink tokens: fills internal OHLCV gaps with Binance data
- Chainlink tokens: skipped (already clean oracle data)

Only fills INTERNAL gaps (never extends backwards past GMX listing date).
"""

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 70)
    print("GMX + Binance Gap-Fill (in-place)")
    print("=" * 70)
    print(f"GMX data:       {GMX_DIR}")
    print(f"Binance source: {BINANCE_DIR}")
    print()

    if not GMX_DIR.exists():
        print(f"ERROR: GMX directory not found: {GMX_DIR}")
        sys.exit(1)
    if not BINANCE_DIR.exists():
        print(f"ERROR: Binance directory not found: {BINANCE_DIR}")
        sys.exit(1)

    gmx_tokens = discover_gmx_tokens()
    binance_tokens = discover_binance_tokens()

    print(f"GMX tokens found:     {len(gmx_tokens)}")
    print(f"Binance tokens found: {len(binance_tokens)}")
    print()

    total_gaps = 0
    total_filled = 0
    tokens_fixed = 0

    for token in sorted(gmx_tokens.keys()):
        files = gmx_tokens[token]

        if token in CHAINLINK_TOKENS:
            continue  # Clean oracle data, no gaps

        bn_name = get_binance_name(token)
        if bn_name not in binance_tokens:
            continue  # No Binance data available

        for f in files:
            tf = parse_timeframe(f)
            if tf not in TIMEFRAMES_TO_MERGE or not is_futures_file(f, tf):
                continue

            gmx_df = load_feather(f)
            gaps = find_gaps(gmx_df, tf)

            if gaps:
                bn_path = binance_file_for(token, tf)
                merged_df, filled = fill_gaps_with_binance(gmx_df, bn_path, gaps, token)
                if filled > 0:
                    pf.write_feather(merged_df, f)  # Write back in-place
                    total_gaps += len(gaps)
                    total_filled += filled

        if total_filled > 0:
            tokens_fixed += 1

    print(f"Gaps found: {total_gaps}, candles filled: {total_filled}, tokens fixed: {tokens_fixed}")
    print("Done!")


if __name__ == "__main__":
    main()
