#!/usr/bin/env python3
"""
Fetch historical daily market cap data for all GMX backtest pairs.

Uses CoinGecko Pro API to build a date-indexed market cap history file.
Output: user_data/data/market_cap_history.json (also copied to user_data/strategies/data/)

Usage:
  python3 scripts/fetch_historical_mcaps_gmx.py
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]

# GMX full universe config
PAIRLIST_CONFIG = REPO_ROOT / "configs" / "ichiv2_gmx_full_universe.json"

# Secrets file with CoinGecko Pro key
SECRETS_FILE = REPO_ROOT / "user_data" / "data" / "binance" / "futures" / "binance_static.secrets.json"

# Output locations
OUTPUT_FILE = REPO_ROOT / "user_data" / "data" / "market_cap_history.json"
STRATEGY_DATA_DIR = REPO_ROOT / "user_data" / "strategies" / "data"

# Start from 2021-01-01 to cover full backtest range (20210106-20260312)
HISTORY_START = datetime(2021, 1, 1, tzinfo=timezone.utc)

# CoinGecko Pro rate limit: ~30 req/min
API_DELAY = 2.5

# Token prefix mappings
SYMBOL_PREFIXES = ("1000", "K")


def load_api_key(secrets_path: Path) -> tuple[str, bool]:
    with open(secrets_path) as f:
        data = json.load(f)
    cg = data.get("coingecko", {})
    return cg.get("api_key", ""), cg.get("is_demo", True)


def get_pairs_from_config(config_path: Path) -> list[str]:
    with open(config_path) as f:
        cfg = json.load(f)
    return cfg.get("exchange", {}).get("pair_whitelist", [])


def extract_symbol(pair: str) -> str:
    base = pair.split("/")[0].upper()
    for prefix in SYMBOL_PREFIXES:
        if base.startswith(prefix) and len(base) > len(prefix):
            return base[len(prefix):]
    return base


def build_symbol_to_id_map(cg, symbols: set[str]) -> dict[str, str]:
    symbol_to_id: dict[str, str] = {}
    symbol_to_mcap: dict[str, float] = {}

    logger.info("Fetching top-500 coins from CoinGecko to build symbol map...")
    for page in (1, 2):
        data = cg.get_coins_markets(
            vs_currency="usd",
            order="market_cap_desc",
            per_page=250,
            page=page,
            sparkline=False,
        )
        for coin in data:
            sym = coin["symbol"].upper()
            mcap = coin.get("market_cap") or 0
            if sym in symbols:
                if sym not in symbol_to_mcap or mcap > symbol_to_mcap[sym]:
                    symbol_to_id[sym] = coin["id"]
                    symbol_to_mcap[sym] = mcap
        logger.info("  Page %d: found %d coins", page, len(data))
        time.sleep(API_DELAY)

    # Search for missing symbols
    missing = symbols - set(symbol_to_id)
    if missing:
        logger.info("Searching for %d symbols not in top 500: %s", len(missing), sorted(missing))
        for sym in sorted(missing):
            try:
                result = cg.search(query=sym)
                coins = result.get("coins", [])
                for c in coins:
                    if c.get("symbol", "").upper() == sym:
                        symbol_to_id[sym] = c["id"]
                        logger.info("  %s -> %s (via search)", sym, c["id"])
                        break
                else:
                    logger.warning("  %s: no exact match, skipping", sym)
                time.sleep(API_DELAY)
            except Exception as e:
                logger.warning("  Search failed for %s: %s", sym, e)

    return symbol_to_id


def fetch_market_cap_history(cg, coin_id: str, start_dt: datetime) -> dict[str, float]:
    from_ts = int(start_dt.timestamp())
    to_ts = int(datetime.now(tz=timezone.utc).timestamp())

    data = cg.get_coin_market_chart_range_by_id(
        id=coin_id,
        vs_currency="usd",
        from_timestamp=from_ts,
        to_timestamp=to_ts,
    )

    history: dict[str, float] = {}
    for ts_ms, mcap in data.get("market_caps", []):
        date_str = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        history[date_str] = mcap

    return history


def main():
    api_key, is_demo = load_api_key(SECRETS_FILE)
    if not api_key:
        logger.error("No CoinGecko API key found in %s", SECRETS_FILE)
        return 1

    logger.info("CoinGecko API key loaded (demo=%s)", is_demo)

    from pycoingecko import CoinGeckoAPI
    if is_demo:
        cg = CoinGeckoAPI(demo_api_key=api_key, retries=3)
    else:
        cg = CoinGeckoAPI(api_key=api_key, retries=3)

    # Load pairs and extract symbols
    pairs = get_pairs_from_config(PAIRLIST_CONFIG)
    symbols = {extract_symbol(p) for p in pairs}
    logger.info("Loaded %d pairs -> %d unique symbols", len(pairs), len(symbols))

    # Load existing history for incremental update
    existing: dict[str, dict[str, float]] = {}
    existing_sym_to_id: dict[str, str] = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        existing = data.get("history", {})
        existing_sym_to_id = data.get("symbol_to_id", {})
        logger.info("Loaded existing history for %d symbols", len(existing))

    # Build symbol -> coin_id mapping
    symbol_to_id = build_symbol_to_id_map(cg, symbols)
    # Merge with existing mappings
    for sym, cid in existing_sym_to_id.items():
        if sym not in symbol_to_id and sym in symbols:
            symbol_to_id[sym] = cid

    logger.info("Symbol map: %d/%d symbols resolved", len(symbol_to_id), len(symbols))

    not_found = symbols - set(symbol_to_id)
    if not_found:
        logger.warning("No CoinGecko ID for: %s (will use 'degen' tier)", sorted(not_found))

    # Fetch history
    history: dict[str, dict[str, float]] = dict(existing)
    failed: list[str] = []

    # Only fetch symbols we don't already have, or that need extending back to 2021
    to_fetch = []
    for sym in sorted(symbol_to_id.keys()):
        if sym not in history:
            to_fetch.append((sym, "new"))
        else:
            dates = sorted(history[sym].keys())
            if dates and dates[0] > "2021-01-15":
                to_fetch.append((sym, f"extend (earliest={dates[0]})"))

    logger.info("%d symbols need fetching: %s", len(to_fetch),
                [(s, r) for s, r in to_fetch[:10]])

    for i, (sym, reason) in enumerate(to_fetch):
        coin_id = symbol_to_id[sym]
        logger.info("[%d/%d] Fetching %s (%s) — %s", i + 1, len(to_fetch), sym, coin_id, reason)
        try:
            sym_history = fetch_market_cap_history(cg, coin_id, HISTORY_START)
            if sym in history:
                # Merge: keep existing data, add older dates
                merged = dict(sym_history)
                merged.update(history[sym])  # existing takes priority for overlapping dates
                history[sym] = merged
            else:
                history[sym] = sym_history
            logger.info(
                "  %s: %d data points (%s -> %s)",
                sym, len(history[sym]),
                min(history[sym]) if history[sym] else "N/A",
                max(history[sym]) if history[sym] else "N/A",
            )
        except Exception as e:
            logger.error("  FAILED for %s (%s): %s", sym, coin_id, e)
            failed.append(sym)

        time.sleep(API_DELAY)

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "history": history,
        "symbol_to_id": symbol_to_id,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        "history_start": HISTORY_START.date().isoformat(),
        "pairs_config": str(PAIRLIST_CONFIG),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)

    # Also copy to strategy data dir (where the strategy looks for it)
    STRATEGY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    strategy_output = STRATEGY_DATA_DIR / "market_cap_history.json"
    with open(strategy_output, "w") as f:
        json.dump(output, f)

    logger.info(
        "\nDone! %d symbols saved to %s and %s (failed: %s)",
        len(history), OUTPUT_FILE, strategy_output,
        failed or "none",
    )

    # Summary
    for sym in ["BTC", "ETH", "SOL", "DOGE", "PEPE"]:
        if sym in history:
            dates = sorted(history[sym].keys())
            logger.info(
                "  %s: %d days, %s -> %s",
                sym, len(dates), dates[0], dates[-1]
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
