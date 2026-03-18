# Experiment 001: OI Filter Layers — Incremental Impact on GMX Universe

**Strategy:** IchiV2_LS_Backtest / IchiV2_LS_OI_Filter / IchiV2_LS_OI_WhaleCap
**Type:** B (code-divergent — compares 3 strategy variants with incremental features)
**Status:** COMPLETE
**Created:** 2026-03-12
**Baseline:** IchiV2_LS_Backtest (no OI/liquidity filtering — step A0)
**Config:** configs/ichiv2_gmx_full_universe.json + secrets
**Exchange/Timerange:** GMX (Arbitrum) via gmx_complete_w_binance, 20210106-20260312

## Hypothesis

Adding OI-based pair ranking and pool liquidity filtering to IchiV2 on GMX should improve
risk-adjusted returns by:
1. **OI sorting** — concentrating trades on pairs with highest open interest (more liquid, tighter spreads)
2. **Liquidity filtering** — excluding pairs with insufficient pool liquidity (avoid slippage/execution risk)
3. **Whale cap** — sizing positions relative to OI so we never represent >2.5% of a market's OI

Each layer should provide incremental benefit. This experiment measures the marginal contribution of each.

## Design

| Step | Strategy | OI Sort | Liquidity Filter | Whale Cap | What's Being Tested |
|------|----------|---------|-----------------|-----------|---------------------|
| A0   | IchiV2_LS_Backtest | OFF | OFF | OFF | Baseline — all 107 pairs, no filtering |
| A1   | IchiV2_LS_OI_Filter | ON (top 75) | OFF (min_pool=0) | OFF | Impact of OI-based pair ranking alone |
| A2   | IchiV2_LS_OI_Filter | ON (top 75) | ON (min_pool=500k) | OFF | + liquidity filter |
| A3   | IchiV2_LS_OI_WhaleCap | ON (top 75) | ON (min_pool=500k) | ON (2.5%) | + whale cap position sizing |

## Backtest Commands

```bash
cd /home/ubuntu/dev/gmx-ccxt-freqtrade
EXP_DIR=experiments/ichiv2-gmx/001-oi-filter-layers
BASE="--config configs/ichiv2_gmx_full_universe.json \
  --config configs/ichiv2_gmx_full_universe.secrets.json \
  --datadir user_data/data/gmx_complete_w_binance \
  --timeframe-detail 5m --timerange 20210106-20260312 --timeframe 1h"

# A0: Baseline
./freqtrade-gmx backtesting --strategy IchiV2_LS_Backtest $BASE 2>&1 | tee $EXP_DIR/results/A0_baseline.txt

# A1: OI sort only (set liquidity_filter_min_pool=0 in JSON)
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_Filter $BASE 2>&1 | tee $EXP_DIR/results/A1_oi_sort_only.txt

# A2: OI sort + liquidity filter (set liquidity_filter_min_pool=500000 in JSON)
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_Filter $BASE 2>&1 | tee $EXP_DIR/results/A2_oi_plus_liquidity.txt

# A3: OI sort + liquidity + whale cap
./freqtrade-gmx backtesting --strategy IchiV2_LS_OI_WhaleCap $BASE 2>&1 | tee $EXP_DIR/results/A3_oi_liq_whalecap.txt
```

## Results

**Note:** Chainlink baseline used 5m timeframe detail. A0-A3 used 1h only (OI data + 5m detail exceeds 11GB RAM).
A3 whale cap has no effect at $100 balance — positions already small relative to OI.

| Step | Config | Profit % | Sharpe | Calmar | Max DD % | Trades | Win % | vs A0 (profit pp) |
|------|--------|----------|--------|--------|----------|--------|-------|-------------------|
| CL   | Chainlink 41 pairs (5m) | 194.64 | 1.75 | 13.84 | 15.84 | 2080 | — | — |
| A0   | No filter, 107 pairs (1h) | 291.75 | 1.81 | 21.18 | 15.51 | 2590 | 36.9 | — |
| A1   | OI sort only | 265.57 | 1.71 | 23.22 | 12.88 | 1663 | 40.0 | -26.18 |
| A2   | OI sort + liquidity 500k | 153.90 | 1.18 | 18.33 | 9.45 | 904 | 41.5 | -137.85 |
| A3   | OI + liq + whale cap 2.5% | 153.90 | 1.18 | 18.33 | 9.45 | 904 | 41.5 | -137.85 |

## Findings

1. **OI sorting (A1) is the sweet spot**: Reduces trades by 36% (2590→1663) while keeping strong returns (265.57%). Best Calmar ratio (23.22) thanks to lower drawdown (12.88% vs 15.51%). Win rate improves from 36.9% to 40.0%.

2. **Liquidity filter (A2) cuts too aggressively**: Drops to only 904 trades and 153.90% profit. The 500k min pool threshold eliminates many profitable pairs. However, it achieves the lowest drawdown (9.45%) and highest win rate (41.5%).

3. **Whale cap (A3) = A2 at small scale**: With $100 starting balance, position sizes (~$14 avg) are far below 2.5% of any pair's OI. Whale cap is only relevant at production-scale balances ($100k+).

4. **Full universe (A0) >> Chainlink subset**: 291.75% vs 194.64% — the additional 66 pairs provide significant alpha, especially on shorts.

5. **Short side dominates**: In all configurations, shorts generate 3-8x more profit than longs.

## Decision

**PARTIAL ADOPT** — Adopt A1 (OI sorting) for production. The liquidity filter threshold (A2) at 500k is too aggressive and should be re-tested at lower thresholds (100k-250k). Whale cap should be re-validated at production balance levels.
