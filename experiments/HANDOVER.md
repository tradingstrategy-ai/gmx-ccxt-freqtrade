# GMX Dynamic Pairlist & Position Sizing — Handover Document

## What Was Built

### 1. Backtestable Dynamic Pairlist Infrastructure

**Problem:** GMX is a zero-volume DEX (oracle pricing), so Freqtrade's built-in volume pairlist doesn't work. We needed backtestable pairlists that change daily based on historical data.

**Solution:** Two custom pairlist handlers + backtester patches:

- **`freqtrade/plugins/pairlist/HistoricalVolumePairList.py`** — Sorts GMX pairs by Binance volume (cross-venue proxy). Reads Binance feather files, computes 7-day rolling average quoteVolume, returns top N. Has token mapping for naming differences (Binance `1000BONK` → GMX `BONK`). Config params: `data_source_dir`, `number_assets`, `lookback_days`, `min_value`, `pair_suffix`.

- **`freqtrade/plugins/pairlist/GMXLiquidityFilter.py`** — Filters pairs by GMX pool liquidity. Reads `futures_metrics/*-1d-pool_liquidity.feather`. Static threshold `min_pool_liquidity` (default $500k). **NOTE: This filter is rudimentary** — see "Open Issues" below.

- **`freqtrade/constants.py`** — Added both handler names to `AVAILABLE_PAIRLISTS` enum for JSON schema validation.

- **`freqtrade/optimize/backtesting.py`** (~line 1588) — Patched to pass `current_time` to pairlist manager. Only refreshes daily (not every hourly candle) via `_last_pairlist_date` check.

- **`freqtrade/plugins/pairlistmanager.py`** — Added `current_time` parameter to `refresh_pairlist()`, stored as `self._current_time` for handlers to access. Added daily logging.

### 2. OI-Based Position Cap ("Whale Cap" / "OI Cap")

Two strategy subclasses that add position sizing capped at `max_oi_share` (default 2.5%) of a pair's total open interest on GMX:

- **`user_data/strategies/IchiV2_LS_Static_WhaleCap.py`** — Subclass of `IchiV2_LS_Static`. Simple: `custom_stake_amount()` returns `min(proposed_stake, OI * 0.025 / leverage)`.

- **`user_data/strategies/IchiV3_LS_Static_WhaleCap.py`** — Subclass of `IchiV3_LS_Static`. Calls `super().custom_stake_amount()` first (market cap sizing), then applies OI cap on top. Two-layer sizing: mcap tiers → OI cap.

Both read OI from `futures_metrics/*-1d-open_interest.feather` files. Verified correct: 0 violations across 638 trades, positions capped at exactly 2.50% of OI.

### 3. Historical Market Cap Data

**`scripts/fetch_historical_mcaps_gmx.py`** — Fetches daily market cap history from CoinGecko Pro API for all 107 GMX tokens. Outputs to `user_data/data/market_cap_history.json` and `user_data/strategies/data/market_cap_history.json`.

- 105 symbols successfully fetched
- Date range: 2021-01-01 to 2026-03-13
- Used CoinGecko Pro key from `user_data/data/binance/futures/binance_static.secrets.json`
- IchiV3_LS_Static reads this via `_get_market_cap_value_at()` when `use_historical_mcap: 1`

### 4. Strategy Cleanup

Deleted all derivative strategy files that used the wrong approach (OI filtering in `confirm_trade_entry` instead of proper pairlist handlers):
- `IchiV2_LS_OI_Filter.py` (deleted)
- `IchiV2_LS_OI_WhaleCap.py` (deleted)
- `IchiV2_LS_Backtest.py` (deleted)
- `IchiV2_LS_Optimised.py` (deleted)

**`IchiV2_LS_Static.py`** is the single source of truth for IchiV2.

---

## Experiment Results

### Experiment 002: IchiV2 Pairlist Layers
**Location:** `experiments/ichiv2-gmx/002-volume-pairlist-layers/`

| Arm | Config | Strategy | Profit% | CAGR | MaxDD | Sharpe | Calmar |
|-----|--------|----------|---------|------|-------|--------|--------|
| A | Static 107 pairs | IchiV2_LS_Static | 306.1% | 35.6% | 24.2% | 1.20 | 1.47 |
| B | Vol top 75 | IchiV2_LS_Static | 203.0% | 27.2% | 28.1% | 1.17 | 0.97 |
| B2 | Vol top 100 | IchiV2_LS_Static | 202.8% | 27.2% | 27.9% | 1.02 | 0.97 |
| C | Vol75 + Liq $500k | IchiV2_LS_Static | 65.0% | 11.5% | 12.2% | 1.02 | 0.94 |
| D | Vol75 + Liq + OI cap | IchiV2_LS_Static_WhaleCap | 58.8% | 10.6% | 12.0% | 1.02 | 0.88 |
| E | Vol100 + OI cap | IchiV2_LS_Static_WhaleCap | 84.2% | 14.2% | 21.7% | 1.03 | 0.65 |

### Experiment 003: IchiV3 Pairlist Layers (with historical mcap)
**Location:** `experiments/ichiv3-gmx/003-volume-pairlist-layers/`

| Arm | Config | Strategy | Profit% | CAGR | MaxDD | Sharpe | Sortino | Calmar |
|-----|--------|----------|---------|------|-------|--------|---------|--------|
| A | Static 107 pairs | IchiV3_LS_Static | 396.9% | 41.7% | 37.1% | 1.37 | 3.00 | 1.12 |
| B | Vol top 75 | IchiV3_LS_Static | 281.0% | 33.8% | 39.1% | 1.40 | 3.30 | 0.86 |
| B2 | Vol top 100 | IchiV3_LS_Static | 330.5% | 37.3% | 39.1% | 1.35 | 2.98 | 0.96 |
| C | Vol75 + Liq $500k | IchiV3_LS_Static | 133.5% | 20.3% | 21.9% | 1.43 | 3.34 | 0.92 |
| D | Vol75 + Liq + OI cap | IchiV3_LS_Static_WhaleCap | 212.2% | 28.1% | 29.5% | **1.48** | 3.22 | 0.95 |
| E | Vol100 + OI cap | IchiV3_LS_Static_WhaleCap | 129.4% | 19.8% | 37.8% | 0.98 | 2.02 | 0.52 |

**IchiV3 uses historical mcap data** for position sizing (point-in-time, not lookahead). Market cap tier multipliers from `IchiV3_LS_Static.json`: Blue chip (>$100B) = 1.0x, Large (>$10B) = 2.0x, Mid (>$1B) = 2.0x, Degen = 1.5x. Per-pair cap 20%.

---

## Key Findings

### 1. The OI cap works as a capital concentrator, not just a risk limiter
In Arm D, the OI cap shrinks positions on low-OI pairs. The freed capital flows into high-OI pairs (SOL, LINK, ETH) where it compounds. Arm D beats Arm C by $79k despite taking fewer trades. The OI cap + liq filter pre-select tradeable pairs, then the OI cap optimizes allocation within them.

### 2. OI cap alone (without filtering) is the worst config
Arm E (vol + OI cap, no liq filter) has worst risk-adjusted returns (Sharpe 0.98, Calmar 0.52). 51% of trades have stakes under $10k, 20% under $1k. Dust positions on tiny-OI tokens waste trade slots and dilute capital from winners.

### 3. GMX execution costs are NOT modeled
GMX has no slippage (oracle pricing). But the backtest does not model:
- Position fees (~0.05-0.07% per trade)
- Impact factor fees (based on OI imbalance: `diffUsd^exponent * factor`)
- Funding rate costs (ongoing, depends on OI imbalance you cause)
- Borrowing fees
- Pool capacity limits

All profit numbers are overstated by the sum of these unmodeled costs.

### 4. The liquidity filter is crude
The current `GMXLiquidityFilter` uses a static $500k threshold on a `pool_liquidity` metric whose exact meaning is unclear — it doesn't match the UI's "Available Liquidity" values. It doesn't distinguish long vs short side, isn't relative to position size, and doesn't model the actual cost of being in the pool.

### 5. Shorts dominate
~70% of trades are shorts across all arms, generating 80-90% of P&L.

---

## Open Issues / Recommended Next Steps

### Replace liquidity filter with minimum OI floor
The current static $500k liquidity filter accidentally does the right thing (removes tiny pools) but uses the wrong metric. A cleaner approach: set a `min_oi` floor so that `OI * max_oi_share >= minimum_meaningful_position`. Example: if base stake is ~$10k and max_oi_share is 2.5%, require OI >= $400k. This uses the same OI data the cap already loads — no new data source needed.

### Model GMX execution costs
The biggest gap in backtest fidelity. Would need:
- Impact factor formula from PricingUtils contract (have the math from Avik)
- Funding rate data (or model based on OI imbalance)
- Position fee schedule per market
- Borrowing fee rates

### Consider a smarter pairlist approach
Instead of separate volume filter + liq filter + OI cap, consider a single handler that scores pairs by a composite of: Binance volume (market interest), GMX OI (market depth on-chain), and available capacity. This would replace three separate crude filters with one informed one.

### IchiV3 JSON params vs code defaults
The `IchiV3_LS_Static.json` overrides the code defaults with more conservative multipliers (1.0/2.0/2.0/1.5 vs code defaults 4.8/3.8/2.9/1.9). The backtests used the JSON params. Verify which params the live bot uses.

---

## File Locations (all relative to `/home/ubuntu/dev/gmx-ccxt-freqtrade/`)

### Core Code Changes
```
freqtrade-develop/freqtrade/constants.py                    # Added handler names to AVAILABLE_PAIRLISTS
freqtrade-develop/freqtrade/optimize/backtesting.py         # Patched for daily pairlist refresh + current_time
freqtrade-develop/freqtrade/plugins/pairlistmanager.py      # Added current_time param + daily logging
freqtrade-develop/freqtrade/plugins/pairlist/HistoricalVolumePairList.py  # Binance volume pairlist
freqtrade-develop/freqtrade/plugins/pairlist/GMXLiquidityFilter.py        # GMX liquidity filter
```

### Strategies
```
user_data/strategies/IchiV2_LS_Static.py                    # Source of truth (IchiV2)
user_data/strategies/IchiV2_LS_Static_WhaleCap.py           # + OI cap
user_data/strategies/IchiV3_LS_Static.py                    # Source of truth (IchiV3, mcap sizing)
user_data/strategies/IchiV3_LS_Static_WhaleCap.py           # + OI cap on top of mcap sizing
```

### Data
```
user_data/data/market_cap_history.json                      # 105 symbols, 2021-01-01 to 2026-03-13
user_data/strategies/data/market_cap_history.json            # Same (copy for strategy access)
user_data/data/gmx_complete_w_binance/futures_metrics/       # OI + liquidity feather files
user_data/data/gmx_complete_w_binance/                       # Binance volume data (feather)
```

### Experiments
```
experiments/ichiv2-gmx/002-volume-pairlist-layers/           # IchiV2 experiment (6 arms)
  configs/arm_{a,b,b2,c,d,e}_*.json
  results/arm_{a,b,b2,c,d,e}_*.zip
  comparison.ipynb
  run_002.sh

experiments/ichiv3-gmx/003-volume-pairlist-layers/           # IchiV3 experiment (6 arms)
  configs/arm_{a,b,b2,c,d,e}_*.json
  results/arm_{a,b,b2,c,d,e}_*.zip
  comparison.ipynb
  run_003.sh
```

### Scripts
```
scripts/fetch_historical_mcaps_gmx.py                        # CoinGecko historical mcap fetcher
```

### Configs
```
configs/ichiv2_gmx_full_universe.json                        # 107-pair GMX universe (base config)
configs/ichiv2_gmx_full_universe.secrets.json                # Secrets (API keys)
```

---

## Backtest Command Pattern

```bash
cd /home/ubuntu/dev/gmx-ccxt-freqtrade

# IchiV3 with OI cap (Arm D config as example)
./freqtrade-gmx backtesting \
  --strategy IchiV3_LS_Static_WhaleCap \
  --config experiments/ichiv3-gmx/003-volume-pairlist-layers/configs/arm_d_volume_liq_whale.json \
  --config configs/ichiv2_gmx_full_universe.secrets.json \
  --datadir user_data/data/gmx_complete_w_binance \
  --timeframe 1h \
  --timerange 20210106-20260312 \
  --cache none
```

Key flags:
- `--cache none` — required, otherwise freqtrade reuses cached results
- Dynamic pairlists are enabled via `"enable_dynamic_pairlist": true` in config
- 4GB swap was added (`/swapfile`) to prevent OOM on memory-heavy arms

## Memory Note
The server has 11GB RAM + 4GB swap. IchiV3 WhaleCap with vol100 (no liq filter) requires swap. The swap file is at `/swapfile` — can be removed with `sudo swapoff /swapfile && sudo rm /swapfile` if no longer needed.
