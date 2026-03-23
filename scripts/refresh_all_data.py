#!/usr/bin/env python3
"""Refresh all supplementary data: Binance volume, GMX open interest, and pool liquidity.

Run inside the Docker container (has ccxt + GMX API access):
    docker compose exec ichiv2_gmx_vault python /freqtrade/scripts/refresh_all_data.py

Or from host via make:
    make refresh-data  (calls this as part of the pipeline)

Updates:
  - user_data/data/binance/futures/*-1d-futures.feather  (Binance volume for HistoricalVolumePairList)
  - user_data/data/gmx_complete/futures_metrics/*-1d-open_interest*.feather  (OI for whale cap / filters)
  - user_data/data/gmx_complete/futures_metrics/*-1d-pool_liquidity*.feather (liquidity for GMXLiquidityFilter)
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.feather as pf


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
BINANCE_DIR = BASE_DIR / "user_data" / "data" / "binance" / "futures"
METRICS_DIR = BASE_DIR / "user_data" / "data" / "gmx" / "futures_metrics"

GMX_API_BASE = "https://arbitrum-api.gmxinfra.io"


# ---------------------------------------------------------------------------
# 1. Refresh Binance 1d volume data
# ---------------------------------------------------------------------------
def refresh_binance_volume():
    """Fetch recent Binance futures 1d OHLCV and append to existing feather files."""
    print("=" * 60)
    print("Refreshing Binance 1d volume data...")
    print("=" * 60)

    try:
        import ccxt
    except ImportError:
        print("  SKIP: ccxt not available (run inside Docker container)")
        return

    exchange = ccxt.binanceusdm({"enableRateLimit": True})
    exchange.load_markets()

    feather_files = sorted(BINANCE_DIR.glob("*-1d-futures.feather"))
    if not feather_files:
        print(f"  No existing feather files in {BINANCE_DIR}")
        return

    print(f"  Found {len(feather_files)} files to update")
    updated = 0
    skipped = 0

    for fp in feather_files:
        parts = fp.name.split("-1d-futures.feather")[0].split("_")
        symbol = f"{parts[0]}/USDT:USDT"

        if symbol not in exchange.markets:
            skipped += 1
            continue

        df = pd.read_feather(fp)
        last_date = pd.Timestamp(df["date"].max())
        now = pd.Timestamp.now(tz="UTC")

        if (now - last_date).days < 2:
            skipped += 1
            continue

        since_ms = int(last_date.timestamp() * 1000)
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, "1d", since=since_ms, limit=30)
        except Exception:
            skipped += 1
            continue

        if len(ohlcv) <= 1:
            skipped += 1
            continue

        new_df = pd.DataFrame(ohlcv, columns=["date", "open", "high", "low", "close", "volume"])
        new_df["date"] = pd.to_datetime(new_df["date"], unit="ms", utc=True)

        new_rows = new_df[new_df["date"] > last_date]
        if len(new_rows) > 0:
            combined = pd.concat([df, new_rows], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
            pf.write_feather(combined, fp)
            updated += 1

    print(f"  Updated {updated}, skipped {skipped} (up-to-date or unavailable)")


# ---------------------------------------------------------------------------
# 2. Refresh GMX open interest data
# ---------------------------------------------------------------------------
def _gmx_api_get(path: str) -> dict:
    """GET from GMX REST API."""
    url = f"{GMX_API_BASE}{path}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; gmx-data-refresh/1.0)",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def refresh_gmx_open_interest():
    """Fetch current OI from GMX API and append daily snapshots."""
    print("\n" + "=" * 60)
    print("Refreshing GMX open interest data...")
    print("=" * 60)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        data = _gmx_api_get("/markets/info")
    except Exception as e:
        print(f"  ERROR fetching GMX market info: {e}")
        return

    markets = data if isinstance(data, list) else data.get("markets", data.get("data", []))
    if not markets:
        print("  No market data returned")
        return

    today = pd.Timestamp(datetime.now(timezone.utc).date(), tz="UTC")

    # Aggregate across collateral variants per token (e.g., BTC has WBTC.b-USDC, tBTC-USDC pools)
    aggregated: dict[str, dict[str, float]] = {}

    for market in markets:
        name = market.get("name", "")
        if "/" not in name:
            continue
        symbol = name.split("/")[0].strip()
        if not symbol:
            continue

        try:
            oi_long = float(market.get("openInterestLong", 0)) / 1e30
            oi_short = float(market.get("openInterestShort", 0)) / 1e30
            liq_long = float(market.get("availableLiquidityLong", 0)) / 1e30
            liq_short = float(market.get("availableLiquidityShort", 0)) / 1e30
        except (TypeError, ValueError):
            continue

        if symbol not in aggregated:
            aggregated[symbol] = {"oi_long": 0, "oi_short": 0, "liq_long": 0, "liq_short": 0}
        aggregated[symbol]["oi_long"] += oi_long
        aggregated[symbol]["oi_short"] += oi_short
        aggregated[symbol]["liq_long"] += liq_long
        aggregated[symbol]["liq_short"] += liq_short

    # Write aggregated metrics
    for symbol, vals in aggregated.items():
        pair_prefix = f"{symbol}_USDC_USDC"
        oi_total = vals["oi_long"] + vals["oi_short"]
        liq_total = vals["liq_long"] + vals["liq_short"]

        for suffix, value in [
            ("open_interest", oi_total),
            ("open_interest_long", vals["oi_long"]),
            ("open_interest_short", vals["oi_short"]),
            ("pool_liquidity", liq_total),
        ]:
            _append_daily_metric(pair_prefix, "1d", suffix, today, value)

    print(f"  Updated OI + liquidity for {len(aggregated)} tokens")


def _append_daily_metric(pair_prefix: str, tf: str, suffix: str, today: pd.Timestamp, value: float):
    """Append a daily metric value to its feather file."""
    fp = METRICS_DIR / f"{pair_prefix}-{tf}-{suffix}.feather"

    new_row = pd.DataFrame([{"date": today, "open": value, "high": value, "low": value, "close": value, "volume": 0.0}])

    if fp.exists():
        df = pd.read_feather(fp)
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"], utc=True)
        # Only append if today isn't already present
        if today in df["date"].values:
            return
        df = pd.concat([df, new_row], ignore_index=True)
        df = df.sort_values("date").reset_index(drop=True)
    else:
        df = new_row

    pf.write_feather(df, fp)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    refresh_binance_volume()
    refresh_gmx_open_interest()
    elapsed = time.time() - t0
    print(f"\n✓ All supplementary data refreshed in {elapsed:.0f}s")


if __name__ == "__main__":
    main()
