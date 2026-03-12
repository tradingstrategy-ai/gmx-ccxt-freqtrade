# Justfile usage guide

Local (non-Docker) task runner using the `./freqtrade-gmx` wrapper script. RPC configuration is loaded from the secrets config file (`configs/<config>.secrets.json`).

## Prerequisites

- `just` command-line tool ([install guide](https://github.com/casey/just#installation))
- `./freqtrade-gmx` wrapper script (activates venv and runs patched freqtrade entrypoint)
- A secrets config file (`configs/<config>.secrets.json`) with your Arbitrum RPC endpoint

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `timeframe` | `5m` | Candle timeframe |
| `timerange` | *(empty)* | Date range filter (e.g. `20250115-`). Empty = use all available data per pair |
| `verbose` | *(empty)* | Verbosity flag (`-v`, `-vv`, or `-vvv`) |
| `epochs` | `500` | Number of hyperopt epochs |
| `spaces` | `buy sell` | Hyperopt parameter spaces to optimise |
| `loss` | `SharpeHyperOptLossDaily` | Hyperopt loss function |
| `jobs` | `-1` | Parallel jobs for hyperopt (`-1` = all CPU cores) |

Override any variable inline: `just backtest myconfig MyStrategy timeframe=1h timerange=20250115-`

## Recipes

All recipes accept extra arguments after the required positional args. Any additional flags are passed directly to freqtrade.

### Download data

```bash
just data <config>
just data ichiv2_ls_gmx_backtest_chainlink --timeframes 1h 4h
```

### List pairs

```bash
just list-pairs <config> [exchange]
just list-pairs ichiv2_ls_gmx_backtest_chainlink gmx
```

### Backtest

```bash
just backtest <config> <strategy>
just backtest ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised
just backtest ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised --timeframe-detail 5m --export signals
```

### Hyperopt

```bash
just hyperopt <config> <strategy>
just hyperopt ichiv2_ls_gmx_hyperopt_chainlink IchiV2_LS_Backtest epochs=100
just hyperopt ichiv2_ls_gmx_hyperopt_chainlink IchiV2_LS_Backtest epochs=200 spaces="sell" loss=SortinoHyperOptLossDaily
```

### Plot dataframe

```bash
just plot-dataframe <config> <strategy> [pairs] [backtest_filename]
just plot-dataframe ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised "BTC/USDC:USDC"
```

### Plot profit

```bash
just plot-profit <config> <strategy> [pairs] [backtest_filename] [trade_source] [db]
just plot-profit ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised
just plot-profit ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised "" "" DB mydb.sqlite
```

### Live trade

```bash
just trade <config> <strategy> [db] [freqai_model]
just trade ichiv2_ls_gmx_backtest_chainlink IchiV2_LS_Optimised mydb.sqlite
```

### Generate TOC

```bash
just toc
```

## Config and secrets

Each recipe loads two config files:
- `configs/<config>.json` — strategy and exchange settings
- `configs/<config>.secrets.json` — RPC URLs and credentials (gitignored)

## Available strategies

| Strategy | Description |
|----------|-------------|
| `IchiV2_LS_Backtest` | Dual long/short Ichimoku, all params `optimize=True` for hyperopt |
| `IchiV2_LS_Optimised` | Same strategy with hyperopt-tuned defaults, `optimize=False` |
| `IchiV2_LS_Static` | Full-featured version with daily cloud regime filter and ATR trailing stop |

## Available configs

| Config | Description |
|--------|-------------|
| `ichiv2_ls_gmx_backtest_chainlink` | 28 chainlink pairs, fixed-param backtesting |
| `ichiv2_ls_gmx_hyperopt_chainlink` | 28 chainlink pairs, hyperopt runs |
