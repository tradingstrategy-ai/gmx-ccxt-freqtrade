#!/usr/bin/env python3
"""
fix_gmx_data_types.py
=====================
Repair missing **and stale** data-type files in the GMX futures data directory.

Background
----------
FreqTrade futures backtesting requires **four** candle-type files per token per
timeframe:

    {TOKEN}_USDC_USDC-{tf}-futures.feather      — OHLCV price candles
    {TOKEN}_USDC_USDC-{tf}-mark.feather         — mark price (used for P&L /
                                                   stop-loss calculation)
    {TOKEN}_USDC_USDC-{tf}-index.feather        — index price (used for
                                                   liquidation price tracking)
    {TOKEN}_USDC_USDC-{tf}-funding_rate.feather — 8h funding rate

If ANY of these are missing OR stale, FreqTrade silently skips the pair and
produces 0 trades in the backtest — no error is raised.

Why files go missing or become stale
-------------------------------------
1.  **No index from CEX downloads**
    Binance, Bybit, and OKX do not expose "index" candles via their CCXT
    download endpoints.  Only futures, mark, and funding_rate are downloaded.

2.  **No mark/index for GMXAPI-only tokens**
    Tokens fetched via GMXAPI (e.g. APT, BOME, FLOKI, KTA, MEME, MEW, OM,
    PI, WELL) have no CEX listing, so no mark or index files are downloaded
    at all.

3.  **Stale USDT_USDT-named files**
    Earlier download passes wrote files as {TOKEN}_USDT_USDT-* instead of the
    GMX-required {TOKEN}_USDC_USDC-* naming convention.  FreqTrade looks for
    USDC_USDC and never finds the USDT_USDT files.

4.  **Stale mark/index after re-download**
    CEX downloads only provide 1h mark candles, not 4h or 1d.  When futures
    data is re-downloaded with a longer timerange, the 4h/1d mark and all
    index files remain at the old (shorter) date range.  FreqTrade cannot
    compute indicators over a gap, so these tokens produce 0 trades.

Why synthesising mark / index from futures is valid on GMX
----------------------------------------------------------
GMX is an oracle-based DEX: trade execution uses Chainlink / GMX oracle prices
directly.  Therefore:

    oracle price  ≡  mark price  ≈  index price

This has been verified empirically: BTC_USDC_USDC-1h-futures.feather and
BTC_USDC_USDC-1h-mark.feather are identical (close == close at every candle).
Using futures data as a proxy for mark/index introduces no meaningful error in
backtesting.

What this script does (in order)
---------------------------------
Step 1 — Rename USDT_USDT → USDC_USDC
    Copy any *_USDT_USDT-* file to the USDC_USDC equivalent when the USDC
    version does not already exist.  Does NOT delete the USDT originals (they
    are harmless and may be needed as a source in later steps).

Step 2 — Synthesise mark from futures (missing only)
    For every USDC_USDC futures file that has no corresponding mark file,
    copy the futures file as the mark file.  Applies across all timeframes.

Step 3 — Synthesise index from mark (missing only)
    For every USDC_USDC mark file that has no corresponding index file,
    copy the mark file as the index file.  Applies across all timeframes.

Step 4 — Refresh stale mark from futures
    CEX downloads only provide 1h mark candles.  After a re-download with a
    longer timerange, 4h/1d mark files remain at the old shorter date range
    while the corresponding futures file has been extended.  This step
    overwrites any mark file whose row count is less than the corresponding
    futures file.  Requires pandas.

Step 5 — Refresh stale index from mark
    After Steps 3/4 update mark files, any index file that no longer matches
    the mark file's row count is overwritten.  Requires pandas.

Usage
-----
    python3 scripts/fix_gmx_data_types.py [GMX_DATA_DIR]

    GMX_DATA_DIR defaults to user_data/data/gmx/futures relative to the
    repository root (two directories above this script).

    Pass --dry-run to print what would be copied without touching files.

Example
-------
    # From repo root:
    python3 scripts/fix_gmx_data_types.py

    # Or explicitly:
    python3 scripts/fix_gmx_data_types.py user_data/data/gmx/futures

    # Preview only:
    python3 scripts/fix_gmx_data_types.py --dry-run
"""

import os
import shutil
import sys
from pathlib import Path


def resolve_gmx_dir(args: list[str]) -> Path:
    """Return the GMX futures data directory from CLI args or default."""
    non_flag_args = [a for a in args if not a.startswith("--")]
    if non_flag_args:
        return Path(non_flag_args[0]).resolve()
    # Default: two levels up from this script → repo root → data dir
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "user_data" / "data" / "gmx" / "futures"


def step_rename_usdt_to_usdc(gmx_dir: Path, files: set[str], dry_run: bool) -> int:
    """
    Step 1: Copy *_USDT_USDT-* files to *_USDC_USDC-* equivalents.

    Some older download passes produced files named TOKEN_USDT_USDT-* instead
    of the required TOKEN_USDC_USDC-* format.  FreqTrade looks strictly for
    USDC_USDC naming and silently skips pairs whose files use USDT_USDT.

    Only copies when the USDC_USDC version does not already exist.
    """
    copied = 0
    for fname in sorted(f for f in files if "_USDT_USDT-" in f):
        usdc_name = fname.replace("_USDT_USDT-", "_USDC_USDC-")
        if usdc_name not in files:
            src = gmx_dir / fname
            dst = gmx_dir / usdc_name
            print(f"  [rename] {fname}  →  {usdc_name}")
            if not dry_run:
                shutil.copy2(src, dst)
                files.add(usdc_name)
            copied += 1
    return copied


def step_synthesise_mark(gmx_dir: Path, files: set[str], dry_run: bool) -> int:
    """
    Step 2: Copy futures → mark for tokens with no mark file.

    GMXAPI-only tokens (e.g. APT, BOME, FLOKI, KTA, MEME, MEW, OM, PI, WELL)
    are not listed on any CEX, so no mark file is ever downloaded for them.
    On GMX, the oracle/futures price equals the mark price, so using the
    futures candles as mark data is accurate.

    Covers all timeframes found in the directory.
    """
    copied = 0
    for fname in sorted(f for f in files if "_USDC_USDC-" in f and f.endswith("-futures.feather")):
        mark_name = fname.replace("-futures.feather", "-mark.feather")
        if mark_name not in files:
            src = gmx_dir / fname
            dst = gmx_dir / mark_name
            print(f"  [mark]   {fname}  →  {mark_name}")
            if not dry_run:
                shutil.copy2(src, dst)
                files.add(mark_name)
            copied += 1
    return copied


def step_synthesise_index(gmx_dir: Path, files: set[str], dry_run: bool) -> int:
    """
    Step 3: Copy mark → index for tokens with no index file.

    CEX exchanges (Binance, Bybit, OKX) do not expose index price candles via
    CCXT, so index files are never downloaded.  On GMX, the index price is the
    same oracle-derived price used for mark, making this copy accurate.

    Covers all timeframes found in the directory.
    """
    copied = 0
    for fname in sorted(f for f in files if "_USDC_USDC-" in f and f.endswith("-mark.feather")):
        index_name = fname.replace("-mark.feather", "-index.feather")
        if index_name not in files:
            src = gmx_dir / fname
            dst = gmx_dir / index_name
            print(f"  [index]  {fname}  →  {index_name}")
            if not dry_run:
                shutil.copy2(src, dst)
                files.add(index_name)
            copied += 1
    return copied


def step_refresh_mark(gmx_dir: Path, files: set[str], dry_run: bool) -> int:
    """
    Step 4: Overwrite stale mark files whose row count is less than futures.

    CEX downloads only provide 1h mark candles.  When data is re-downloaded
    with a longer timerange, the futures file grows but the 4h/1d mark files
    remain at the old shorter length.  Any mark file with fewer rows than its
    corresponding futures file is overwritten with the futures data.

    On GMX, futures price ≡ mark price (oracle DEX), so this copy is accurate.
    Requires pandas to read row counts from feather files.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [skip] pandas not available — skipping stale mark refresh")
        return 0

    refreshed = 0
    futures_files = sorted(
        f for f in files if "_USDC_USDC-" in f and f.endswith("-futures.feather")
    )
    for fname in futures_files:
        mark_name = fname.replace("-futures.feather", "-mark.feather")
        if mark_name not in files:
            continue  # missing entirely — Step 2 handles this
        fut_rows = len(pd.read_feather(gmx_dir / fname))
        mark_rows = len(pd.read_feather(gmx_dir / mark_name))
        if mark_rows < fut_rows:
            print(f"  [refresh-mark]  {fname} ({fut_rows}) → {mark_name} (was {mark_rows})")
            if not dry_run:
                shutil.copy2(gmx_dir / fname, gmx_dir / mark_name)
            refreshed += 1
    return refreshed


def step_refresh_index(gmx_dir: Path, files: set[str], dry_run: bool) -> int:
    """
    Step 5: Overwrite stale index files whose row count differs from mark.

    After Steps 3/4 update mark files, the corresponding index files may be
    left at an older shorter length.  This step overwrites any index file
    whose row count no longer matches the mark file.

    Requires pandas to read row counts from feather files.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [skip] pandas not available — skipping stale index refresh")
        return 0

    refreshed = 0
    mark_files = sorted(
        f for f in files if "_USDC_USDC-" in f and f.endswith("-mark.feather")
    )
    for fname in mark_files:
        index_name = fname.replace("-mark.feather", "-index.feather")
        if index_name not in files:
            continue  # missing entirely — Step 3 handles this
        mark_df = pd.read_feather(gmx_dir / fname)
        index_df = pd.read_feather(gmx_dir / index_name)
        if len(mark_df) != len(index_df) or mark_df["date"].min() != index_df["date"].min():
            print(f"  [refresh-index] {fname} ({len(mark_df)}) → {index_name} (was {len(index_df)})")
            if not dry_run:
                shutil.copy2(gmx_dir / fname, gmx_dir / index_name)
            refreshed += 1
    return refreshed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    gmx_dir = resolve_gmx_dir([a for a in sys.argv[1:] if a != "--dry-run"])

    if not gmx_dir.is_dir():
        print(f"ERROR: GMX data directory not found: {gmx_dir}", file=sys.stderr)
        sys.exit(1)

    files: set[str] = set(os.listdir(gmx_dir))
    total_feather = sum(1 for f in files if f.endswith(".feather"))

    print("=" * 60)
    print(" GMX data-type fixer")
    print(f" Dir      : {gmx_dir}")
    print(f" Files    : {total_feather} .feather files")
    print(f" Dry run  : {dry_run}")
    print("=" * 60)
    print()

    # ── Step 1 ─────────────────────────────────────────────────────────────
    print("Step 1: Rename USDT_USDT → USDC_USDC ...")
    n1 = step_rename_usdt_to_usdc(gmx_dir, files, dry_run)
    print(f"  → {n1} files copied\n")

    # ── Step 2 ─────────────────────────────────────────────────────────────
    print("Step 2: Synthesise missing mark files from futures ...")
    n2 = step_synthesise_mark(gmx_dir, files, dry_run)
    print(f"  → {n2} files synthesised\n")

    # ── Step 3 ─────────────────────────────────────────────────────────────
    print("Step 3: Synthesise missing index files from mark ...")
    n3 = step_synthesise_index(gmx_dir, files, dry_run)
    print(f"  → {n3} files synthesised\n")

    # ── Step 4 ─────────────────────────────────────────────────────────────
    print("Step 4: Refresh stale mark files from futures ...")
    n4 = step_refresh_mark(gmx_dir, files, dry_run)
    print(f"  → {n4} files refreshed\n")

    # ── Step 5 ─────────────────────────────────────────────────────────────
    print("Step 5: Refresh stale index files from mark ...")
    n5 = step_refresh_index(gmx_dir, files, dry_run)
    print(f"  → {n5} files refreshed\n")

    # ── Summary ────────────────────────────────────────────────────────────
    total = n1 + n2 + n3 + n4 + n5
    action = "Would create/refresh" if dry_run else "Created/refreshed"
    print("=" * 60)
    print(f" {action} {total} files")
    print(f"   rename={n1}, mark-new={n2}, index-new={n3}, mark-stale={n4}, index-stale={n5}")
    if dry_run:
        print(" Re-run without --dry-run to apply changes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
