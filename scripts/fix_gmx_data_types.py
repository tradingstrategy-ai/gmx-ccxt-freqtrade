#!/usr/bin/env python3
"""
fix_gmx_data_types.py
=====================
Automatically repair missing data-type files in the GMX futures data directory.

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

If ANY of these are missing, FreqTrade silently skips the pair and it produces
0 trades in the backtest — no error is raised.

Why files go missing
--------------------
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

Step 2 — Synthesise mark from futures
    For every USDC_USDC futures file that has no corresponding mark file,
    copy the futures file as the mark file.  Applies across all timeframes.

Step 3 — Synthesise index from mark
    For every USDC_USDC mark file that has no corresponding index file,
    copy the mark file as the index file.  Applies across all timeframes.

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

    # ── Summary ────────────────────────────────────────────────────────────
    total = n1 + n2 + n3
    action = "Would create" if dry_run else "Created"
    print("=" * 60)
    print(f" {action} {total} files  (rename={n1}, mark={n2}, index={n3})")
    if dry_run:
        print(" Re-run without --dry-run to apply changes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
