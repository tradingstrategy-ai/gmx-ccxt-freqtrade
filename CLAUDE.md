# GMX CCXT Freqtrade

Algorithmic trading system for GMX DEX using Freqtrade with custom CCXT adapter.

## Architecture

- **Exchange adapter**: GMX ↔ CCXT bridge in `deps/web3-ethereum-defi/` (monkeypatched into Freqtrade)
- **Strategies**: `user_data/strategies/` — IchiV2 (Ichimoku v2) is the primary production strategy
- **Custom pairlists**: `plugins/pairlist/` — `HistoricalVolumePairList` (Binance volume proxy) + `GMXLiquidityFilter`
- **Data collector**: `gmx-data-collector/` submodule — collects candles from Chainlink oracles + GMX API
- **Freqtrade patches**: `freqtrade-develop/` — patched backtesting.py and pairlistmanager.py for dynamic pairlist support

## Data Pipeline

### Data directories

```
user_data/data/
├── gmx/                    # Raw GMX candles (from gmx-data-collector or freqtrade download-data)
├── gmx_complete/           # GMX candles gap-filled with Binance (output of merge_gmx_binance.py)
├── gmx_complete_w_binance/ # Final dataset: historical Binance backfill + GMX data (USE THIS FOR BACKTESTS)
├── binance/futures/        # Binance volume data (1d feathers for HistoricalVolumePairList)
└── market_cap_history.json # CoinGecko market cap data (for IchiV3 tier sizing)
```

**Always use `gmx_complete_w_binance` as the datadir for backtesting** — it has the deepest history.

### How to refresh data

There are two scenarios. Both require `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
# Fill in JSON_RPC_ARBITRUM and HYPERSYNC_API_TOKEN
```

#### Incremental update (daily use, ~10-30 min)

```bash
# Step 1: Update GMX candles via gmx-data-collector
source .env && make gmx-data

# Step 2: Gap-fill with Binance and create final dataset
python scripts/merge_gmx_binance.py
python scripts/backfill_1h_5m_from_binance.py
```

#### Full history rebuild (first-time setup or after data loss)

```bash
# Step 1: Collect full history from genesis (takes hours)
source .env
cd gmx-data-collector
poetry run python -m gmx_historical_data.cli collect --full --output-dir ./data --concurrency 5
poetry run python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet
poetry run python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir ../user_data/data
cd ..

# Step 2: Gap-fill with Binance and create final dataset
python scripts/merge_gmx_binance.py
python scripts/backfill_1h_5m_from_binance.py
```

#### Refresh Binance volume data only (for HistoricalVolumePairList)

The 1d Binance feathers in `user_data/data/binance/futures/` power the `HistoricalVolumePairList`.
These were originally downloaded via freqtrade and can be topped up by running a ccxt fetch
script inside the Docker container (no standalone script exists yet).

### Do NOT use `make data`

`make data` has been deprecated. It wrapped freqtrade's `download-data` which loads all data into
memory and will OOM on large pair sets. Use `make refresh-data` or `make full-data` instead —
they use the `gmx-data-collector` pipeline which is incremental, checkpointed, and memory-safe.

## Running backtests

```bash
# Via Makefile (uses Docker)
make backtest CONTAINER=ichiv2_gmx STRATEGY=IchiV2_LS_Static TIMEFRAME=1h TIMERANGE=20260101-20260319

# Via notebook (inline, with live comparison)
# See notebooks/analysis/live-vs-backtest/01-ichiv2_live_vs_backtest_gmx.ipynb
```

### Dynamic pairlist backtesting

For configs with `HistoricalVolumePairList` (e.g., vault configs), set `"enable_dynamic_pairlist": true`
in the config. The patched backtesting engine refreshes the pairlist daily during backtests using
historical Binance volume data.

## Production bots

Two bots run via `docker compose up -d`:

- **ichiv2_gmx** — Static 41-pair whitelist, config: `configs/ichiv2_gmx.json`
- **ichiv2_gmx_vault** — Dynamic top-40 via HistoricalVolumePairList, config: `configs/ichiv2_gmx_prod_vault.json`

Live DBs: `db/ichiv2_gmx.sqlite`, `db/ichiv2_gmx_vault.sqlite`
Archived DBs: `db/archive/`

## Key scripts

| Script | Purpose |
|--------|---------|
| `scripts/merge_gmx_binance.py` | Gap-fill raw GMX candles with Binance → `gmx_complete/` |
| `scripts/backfill_1h_5m_from_binance.py` | Prepend Binance historical data (1d/4h/1h/5m) → `gmx_complete_w_binance/` |
| `scripts/fetch_historical_mcaps_gmx.py` | Fetch CoinGecko market cap history (for IchiV3) |
| `scripts/db-backup` | Archive live trading databases |

## Configs

| Config | Use |
|--------|-----|
| `ichiv2_gmx.json` | Production static bot (41 pairs) |
| `ichiv2_gmx_prod_vault.json` | Production vault bot (107 pairs, dynamic pairlist) |
| `ichiv2_gmx_volume_pairlist.json` | Backtest config with full 3-layer pairlist (Static → Volume → Liquidity) |
| `ichiv2_gmx_full_universe.json` | All 174 pairs, static (baseline backtests) |

## Conventions

- Pair format: `TOKEN/USDC:USDC` (e.g., `BTC/USDC:USDC`)
- All feather files use UTC timestamps
- GMX has no on-chain volume (oracle-priced) — use Binance volume as proxy
- Strategies use 1h primary timeframe with 4h and 1d informative timeframes
