# Justfile usage guide

Local (non-Docker) task runner using the `./freqtrade-gmx` wrapper script. All recipes require `$ARBITRUM_CHAIN_JSON_RPC` to be set in your environment.

## Prerequisites

- `just` command-line tool ([install guide](https://github.com/casey/just#installation))
- `./freqtrade-gmx` wrapper script (activates venv and runs patched freqtrade entrypoint)
- `$ARBITRUM_CHAIN_JSON_RPC` environment variable pointing to an Arbitrum RPC endpoint

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
just data my_strategy_gmx --timeframes 1h 4h
```

### List pairs

```bash
just list-pairs <config> [exchange]
just list-pairs my_strategy_gmx gmx
```

### Backtest

```bash
just backtest <config> <strategy>
just backtest my_strategy_gmx MyStrategy
just backtest my_strategy_gmx MyStrategy --timeframe-detail 5m --export signals
```

### Hyperopt

```bash
just hyperopt <config> <strategy>
just hyperopt my_strategy_gmx MyStrategy epochs=100
just hyperopt my_strategy_gmx MyStrategy epochs=200 spaces="sell" loss=SortinoHyperOptLossDaily
```

### Plot dataframe

```bash
just plot-dataframe <config> <strategy> [pairs] [backtest_filename]
just plot-dataframe my_strategy_gmx MyStrategy "BTC/USDC:USDC"
```

### Plot profit

```bash
just plot-profit <config> <strategy> [pairs] [backtest_filename] [trade_source] [db]
just plot-profit my_strategy_gmx MyStrategy
just plot-profit my_strategy_gmx MyStrategy "" "" DB mydb.sqlite
```

### Live trade

```bash
just trade <config> <strategy> [db] [freqai_model]
just trade my_strategy_gmx MyStrategy mydb.sqlite
```

### Generate TOC

```bash
just toc
```

## Config and secrets

Each recipe loads two config files:
- `configs/<config>.json` — strategy and exchange settings
- `configs/<config>.secrets.json` — RPC URLs and credentials (gitignored)
