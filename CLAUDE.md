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
├── gmx/
│   ├── futures/            # OHLCV candles + funding rates (freqtrade download-data writes here)
│   └── futures_metrics/    # OI + pool liquidity (refresh_all_data.py writes here)
├── binance/futures/        # Binance 1d volume data (for HistoricalVolumePairList)
└── market_cap_history.json # CoinGecko market cap data (for IchiV3 tier sizing)
```

All backtesting uses `datadir = user_data/data/gmx`. The `GMXLiquidityFilter` reads from
`{datadir}/futures_metrics/` and `HistoricalVolumePairList` reads from its own `data_source_dir`
(configured as `user_data/data/binance` in pairlist config).

### How to refresh data

#### Incremental update (daily use, ~5 min)

```bash
make refresh-data
```

Downloads the last 30 days of GMX data via the vault container (safe, small memory), then
merges with Binance and rebuilds the final dataset. No external API tokens needed.

Customize: `make refresh-data REFRESH_DAYS=60` for a wider window.

#### Full history rebuild (first-time setup or after data loss)

Requires `.env` with `JSON_RPC_ARBITRUM` and `HYPERSYNC_API_TOKEN` (copy from `.env.example`).
Uses `gmx-data-collector` submodule for memory-safe collection with checkpoints.

```bash
make full-data
```

### Do NOT use `make data`

`make data` has been removed. It used freqtrade's `download-data` which loads all data into
memory and OOMs on large pair sets. Use `make refresh-data` instead.

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
