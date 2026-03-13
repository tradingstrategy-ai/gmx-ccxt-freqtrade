# Justfile — local (non-Docker) runner using ./freqtrade-gmx wrapper
# Usage: just <recipe> config=<config-name> strategy=<strategy-name> [options...]
# Extra args: append any freqtrade flags after the required args, e.g.:
#   just backtest myconfig MyStrategy --timeframe-detail 5m --export signals

# Default variables
timeframe := "5m"
timerange := ""
verbose := ""
epochs := "500"
spaces := "buy sell"
loss := "SharpeHyperOptLossDaily"
jobs := "-1"

# Generate a table of contents for README.md from Markdown headings.
toc:
    python scripts/generate_toc.py

# Download ALL GMX data: GMX API + CEX supplement + fix mark/index + clean /tmp.
# This is the single command to run when you need fresh or complete data.
# Pass a timerange to limit history, e.g.: just fetch-all-data 20230101-
fetch-all-data timerange="20230101-":
    bash scripts/fetch_all_gmx_data.sh {{timerange}}

# Fix GMX data type files only (synthesise missing + refresh stale mark/index).
# Run after any manual data edits or if backtest shows 0 trades for some pairs.
fix-gmx-data:
    python3 scripts/fix_gmx_data_types.py

# Download historical market data from GMX for backtesting.
data config *args:
    ./freqtrade-gmx download-data \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --timeframes {{timeframe}} \
        {{ if timerange != "" { "--timerange " + timerange } else { "" } }} \
        --prepend \
        {{verbose}} {{args}}

# List available trading pairs on the exchange.
list-pairs config exchange="gmx" *args:
    ./freqtrade-gmx list-pairs \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --exchange {{exchange}} \
        {{verbose}} {{args}}

# Run a strategy backtest against historical data.
backtest config strategy *args:
    ./freqtrade-gmx backtesting \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --strategy-path user_data/strategies \
        --strategy {{strategy}} \
        --timeframe {{timeframe}} \
        {{ if timerange != "" { "--timerange " + timerange } else { "" } }} \
        --cache none \
        {{verbose}} {{args}}

# Run hyperparameter optimization on a strategy.
hyperopt config strategy *args:
    ./freqtrade-gmx hyperopt \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --strategy-path user_data/strategies \
        --strategy {{strategy}} \
        --hyperopt-loss {{loss}} \
        --spaces {{spaces}} \
        --epochs {{epochs}} \
        --jobs {{jobs}} \
        {{ if timerange != "" { "--timerange " + timerange } else { "" } }} \
        {{verbose}} {{args}}

# Plot strategy entry/exit signals overlaid on price and indicator data.
plot-dataframe config strategy pairs="" backtest_filename="" *args:
    ./freqtrade-gmx plot-dataframe \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --strategy-path user_data/strategies \
        --strategy {{strategy}} \
        {{ if pairs != "" { "-p " + pairs } else { "" } }} \
        -i {{timeframe}} \
        {{ if timerange != "" { "--timerange " + timerange } else { "" } }} \
        --backtest-filename {{ if backtest_filename != "" { "user_data/backtest_results/" + backtest_filename } else { "user_data/backtest_results" } }} \
        {{args}}

# Plot the equity curve showing cumulative profit over time.
plot-profit config strategy pairs="" backtest_filename="" trade_source="" db="" *args:
    ./freqtrade-gmx plot-profit \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --strategy-path user_data/strategies \
        --strategy {{strategy}} \
        {{ if pairs != "" { "-p " + pairs } else { "" } }} \
        -i {{timeframe}} \
        {{ if timerange != "" { "--timerange " + timerange } else { "" } }} \
        {{ if trade_source == "DB" { "--db-url sqlite:///db/" + db + " --trade-source DB" } else { "--backtest-filename " + if backtest_filename != "" { "user_data/backtest_results/" + backtest_filename } else { "user_data/backtest_results" } } }} \
        {{args}}

# Start live trading with a given strategy.
trade config strategy db="" freqai_model="" *args:
    ./freqtrade-gmx trade \
        --config configs/{{config}}.json \
        --config configs/{{config}}.secrets.json \
        --strategy-path user_data/strategies \
        --strategy {{strategy}} \
        {{ if freqai_model != "" { "--freqaimodel " + freqai_model } else { "" } }} \
        {{ if db != "" { "--db-url sqlite:///db/" + db } else { "" } }} \
        {{verbose}} {{args}}
