# OI-based pairlist filter for IchiV2 on GMX — handover document

## Goal

Create and backtest a new IchiV2 strategy variant (`IchiV2_LS_OI_Filter`) that dynamically selects pairs based on **Open Interest (OI)** rankings and **pool liquidity** thresholds, since GMX doesn't provide trade volume data (OHLCV volume is always 0).

This mirrors the approach in [PR #131](https://github.com/tradingstrategy-ai/freqtrade-strategies/pull/131) which adds volume-based pairlist filtering to IchiV2/V3 via `confirm_trade_entry()`, but substitutes OI for volume.

## Why OI instead of volume?

GMX is a decentralised perps exchange — it doesn't have traditional order book volume. All OHLCV volume fields are 0. However, GMX does expose:
- **Open Interest**: how much capital is deployed in each market (proxy for activity/interest)
- **Pool liquidity**: how much liquidity backs each market (proxy for tradability/slippage)

Both are already exported as feather files by `gmx-data-collector`.

## What was built

### Strategy: `user_data/strategies/IchiV2_LS_OI_Filter.py`

Copy of `IchiV2_LS_Static.py` with these additions:

1. **Hyperopt parameters** (in `buy` space):
   - `oi_filter_enabled` (0/1, default=1, not optimised)
   - `oi_filter_top_n` (20–108, default=75, optimisable)
   - `oi_filter_lookback_days` (3–30, default=7, optimisable)
   - `oi_filter_min_oi` (0–500k, default=10k, optimisable)
   - `liquidity_filter_min_pool` (0–1M, default=500k, optimisable)

2. **`_load_oi_data()`**: Lazily reads all `*-1d-open_interest.feather` and `*-1d-pool_liquidity.feather` files from `config['datadir']/futures_metrics/`. Builds wide DataFrames (dates × pairs).

3. **`_build_oi_rankings()`**: For each day, computes rolling mean OI over the lookback window, filters by min OI and min pool liquidity, ranks descending, takes top N. Stores as `{date_str: set_of_allowed_pairs}`. Called once, cached.

4. **`confirm_trade_entry()`**: Added OI gate at the top — if the pair isn't in today's allowed set, returns False (trade rejected). Existing ATR storage logic preserved below.

### Sidecar params: `user_data/strategies/IchiV2_LS_OI_Filter.json`

Contains all strategy parameters including the OI filter defaults. Matches the hyperopt parameter definitions in the .py file.

### Config: `configs/ichiv2_gmx_oi_filter_backtest.json`

Backtest-specific config with:
- All 107 tradeable GMX pairs (matches `ichiv2_gmx_full_universe.json`)
- `dry_run: true`, `dry_run_wallet: 1000`
- `trading_fees: {entry: 0.0007, exit: 0.0007}`
- `timeframe: "1h"`, exchange: `gmx`

### Secrets: `configs/ichiv2_gmx_oi_filter_backtest.secrets.json`

Minimal secrets with public Arbitrum RPC. For backtesting only — no private key needed.

### Docker: `docker-compose.yml`

Added `ichiv2_gmx_oi_filter_backtest` service entry.

## How to run the backtest

```bash
cd /home/ubuntu/dev/gmx-ccxt-freqtrade

./freqtrade-gmx backtesting \
    --strategy IchiV2_LS_OI_Filter \
    --config configs/ichiv2_gmx_full_universe.json \
    --config configs/ichiv2_gmx_full_universe.secrets.json \
    --datadir user_data/data/gmx_complete \
    --timeframe-detail 5m \
    --timerange 20210106-20260312
```

Key details:
- `./freqtrade-gmx` is a wrapper that applies the GMX CCXT monkeypatch before running freqtrade (`python -m eth_defi.gmx.freqtrade.patched_entrypoint freqtrade "$@"`)
- `--datadir user_data/data/gmx_complete` points to the gap-filled dataset (Binance backfill for 4h/1d, native GMX for 1h)
- `--timeframe-detail 5m` matches the pattern used by other IchiV2 backtests
- The `ichiv2_gmx_full_universe.json` config has the 107-pair whitelist and is also used for live trading
- You can also use `configs/ichiv2_gmx_oi_filter_backtest.json` + `configs/ichiv2_gmx_oi_filter_backtest.secrets.json` as a backtest-only alternative (same pairs, no live trading config)

### Hyperopt (for tuning filter params)

```bash
./freqtrade-gmx hyperopt \
    --strategy IchiV2_LS_OI_Filter \
    --config configs/ichiv2_gmx_full_universe.json \
    --config configs/ichiv2_gmx_full_universe.secrets.json \
    --datadir user_data/data/gmx_complete \
    --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy --epochs 100 \
    --timerange 20210106-20260312
```

## Data layout

All data lives under `user_data/data/`:

```
user_data/data/
├── gmx/futures/              # Original GMX data (native only)
├── gmx/futures_metrics/      # OI + liquidity metrics (separated from futures/)
├── gmx_complete/futures/     # Gap-filled OHLCV/mark/funding_rate (GMX + Binance backfill)
│   ├── BTC_USDC_USDC-1h-futures.feather        # OHLCV price data
│   ├── BTC_USDC_USDC-4h-futures.feather
│   ├── BTC_USDC_USDC-1d-futures.feather
│   ├── BTC_USDC_USDC-1h-mark.feather
│   └── ...
├── gmx_complete/futures_metrics/  # OI + liquidity (invisible to freqtrade scanner)
│   ├── BTC_USDC_USDC-1d-open_interest.feather   # OI data (used by filter)
│   ├── BTC_USDC_USDC-1d-pool_liquidity.feather  # Liquidity data (used by filter)
│   └── ...
└── binance/                  # Binance source data used for backfill
```

- **OHLCV price files** (`*-futures.feather`): In `futures/`. Used by freqtrade for candle data. 1h data goes back ~6 months (2025-09-10) for most pairs; 4h/1d data goes back to 2021–2023 via Binance backfill.
- **OI files** (`*-open_interest.feather`): In `futures_metrics/`. OHLCV format (date, open, high, low, close, volume=0). The strategy reads the `close` column as the OI value for each day.
- **Liquidity files** (`*-pool_liquidity.feather`): In `futures_metrics/`. Same format. The `close` column is the pool depth in USD.

**Why separate?** Freqtrade's `migrate_funding_fee_timeframe()` scans all `.feather` files in `futures/` and tries to parse filenames as CandleType enum values. OI/liquidity suffixes are not valid CandleType values, causing a crash. Moving them to `futures_metrics/` keeps them accessible to the strategy but invisible to the scanner.

### Data path resolution

Freqtrade's `create_datadir()` always overwrites `config['datadir']`:
- No `--datadir` CLI flag → resolves to `user_data/data/gmx` (appends exchange name automatically)
- With `--datadir user_data/data/gmx_complete` → uses that path as-is

The strategy's `_load_oi_data()` reads from `self.config['datadir'] / 'futures'`, which works correctly in both cases.

### Data ordering issue (RESOLVED)

The OHLCV `-futures.feather` and `-mark.feather` files were stored in **reverse chronological order** (newest first). This was fixed on 2026-03-12: 677 files re-sorted to ascending order, upstream exporter patched. OI and liquidity files were always correctly ordered.

## How the OI filter works

On the first call to `confirm_trade_entry()`:

1. **Load data**: Read all 1d OI and liquidity feather files into wide DataFrames (dates × pairs)
2. **Build rankings**: For each calendar day:
   - Compute rolling mean OI over `lookback_days` window
   - Drop pairs below `min_oi` threshold
   - Drop pairs below `min_pool` liquidity threshold
   - Rank remaining by OI descending, take top `top_n`
   - Store as `{date_str: set_of_allowed_pairs}`
3. **Gate trades**: On each entry signal, check if the pair is in today's allowed set. If not, return False.

This means:
- Pairs with no OI data are never traded
- Pairs with low liquidity are excluded regardless of OI
- The trading universe expands/contracts daily as markets list/delist
- The filter is stateless between days — no lookahead bias

## Design rationale

- **`top_n=75`**: Cast a wide net. The liquidity filter ($500k min pool) is the primary safety gate that removes untradeable pairs. OI ranking is secondary, mainly excluding the long tail of dead/tiny markets.
- **`lookback_days=7`**: Smooths daily noise while remaining responsive to market changes.
- **`min_oi=10000`**: Low floor — let the top-N ranking do the work rather than an absolute threshold.
- **`min_pool=500000`**: Primary safety filter. Ensures sufficient pool depth to execute trades without excessive slippage.

### CandleType crash (FIXED)

Freqtrade's `migrate_funding_fee_timeframe()` scans all `.feather` files in `futures/` and calls `CandleType.from_string()` on parsed suffixes. OI/liquidity files had non-standard suffixes that aren't valid CandleType enum values.

**Fix applied**: Moved all `*-open_interest*.feather` and `*-pool_liquidity*.feather` files from `futures/` to `futures_metrics/` (2,196 files per data directory). Updated `_load_oi_data()` to read from `futures_metrics/` instead. No freqtrade source code changes needed.

**Note**: The upstream GMX data exporter (`gmx-data-collector/src/gmx_historical_data/oi_liquidity_exporter.py`) still writes to `futures/`. It should be updated to write to `futures_metrics/` to prevent the problem from recurring after future data exports.

### Validator fix (DONE)

Changed `gmx_exchange.py` `_validate_backtest_timerange()` from raising `InsufficientHistoricalDataError` to logging warnings when pairs don't have data for the full requested timerange. This matches standard freqtrade behaviour.

**File modified**: `deps/web3-ethereum-defi/eth_defi/gmx/freqtrade/gmx_exchange.py`

## What hasn't been done yet

1. **Fix the CandleType crash** (see above) — this is the immediate blocker
2. **The backtest has not been run yet** — blocked by the CandleType crash
3. **No comparison** yet between OI-filtered results and the static 27-pair IchiV2_LS_Static baseline
4. **No hyperopt** of the filter parameters yet
5. **The `ichiv2_gmx_oi_filter_backtest.json` config** has been created but is now redundant if using `ichiv2_gmx_full_universe.json` directly — both have the same 107 pairs

## Related files and references

- Base strategy: `user_data/strategies/IchiV2_LS_Static.py` / `.json`
- Volume filter PR: https://github.com/tradingstrategy-ai/freqtrade-strategies/pull/131
- GMX CCXT monkeypatch: `deps/web3-ethereum-defi/eth_defi/gmx/freqtrade/patched_entrypoint.py`
- GMX exchange class: `deps/web3-ethereum-defi/eth_defi/gmx/freqtrade/gmx_exchange.py`
- OI/liquidity exporter: `/home/ubuntu/dev/gmx-data-collector/src/gmx_historical_data/oi_liquidity_exporter.py`
- Data fix session: fixed 677 reversed feather files on 2026-03-12
