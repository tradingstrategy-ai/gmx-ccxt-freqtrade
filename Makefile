TIMEFRAME ?= 5m
TIMERANGE ?= 20250101-20251130
# Verbosity level for freqtrade commands (empty, -v, -vv, or -vvv)
VERBOSE ?=

# Generate a table of contents for README.md from Markdown headings.
# Places/updates the TOC above the "# Overview" section.
toc:
	python scripts/generate_toc.py

# Download historical market data from GMX for backtesting.
# Fetches candle data from GMX GraphQL endpoint and stores it locally.
data:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make data CONTAINER=YourContainer [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) download-data \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--timeframes $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--prepend \
		$(VERBOSE)

# List available trading pairs on the exchange.
# Defaults to GMX if no EXCHANGE is specified.
list-pairs:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make list-pairs CONTAINER=YourContainer [EXCHANGE=gmx] [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) list-pairs \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--exchange $(or $(EXCHANGE),gmx) \
		$(VERBOSE)

# Run a strategy backtest against historical data.
# Requires CONTAINER and STRATEGY; uses TIMEFRAME and TIMERANGE variables.
backtest:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make backtest CONTAINER=YourContainer STRATEGY=YourStrategy [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Error: STRATEGY is not set. Usage: make backtest CONTAINER=YourContainer STRATEGY=YourStrategy [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) backtesting \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		--timeframe $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--cache none \
		$(VERBOSE)

# Plot strategy entry/exit signals overlaid on price and indicator data.
# Generates an interactive HTML chart from backtest results.
plot-dataframe:
	@if [ -z "$(CONTAINER)" ] || [ -z "$(STRATEGY)" ]; then \
		echo "Error: CONTAINER and STRATEGY are required. Usage: make plot-dataframe CONTAINER=YourContainer STRATEGY=YourStrategy [PAIRS='BTC/USDT ETH/USDT']"; \
		echo "Optional: BACKTEST_FILENAME=path/to/backtest.zip (defaults to latest backtest in user_data/backtest_results)"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) plot-dataframe \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		$(if $(PAIRS),-p $(PAIRS)) \
		$(if $(TIMEFRAME),-i $(TIMEFRAME)) \
		$(if $(TIMERANGE),--timerange $(TIMERANGE)) \
		--backtest-filename $(if $(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results/$(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results) \
		$(if $(INDICATORS1),--indicators1 $(INDICATORS1)) \
		$(if $(INDICATORS2),--indicators2 $(INDICATORS2))

# Plot the equity curve showing cumulative profit over time.
# Can use backtest results or a live trading database as the data source.
plot-profit:
	@if [ -z "$(CONTAINER)" ] || [ -z "$(STRATEGY)" ]; then \
		echo "Error: CONTAINER and STRATEGY are required. Usage: make plot-profit CONTAINER=YourContainer STRATEGY=YourStrategy [PAIRS='BTC/USDT ETH/USDT']"; \
		echo "Optional: BACKTEST_FILENAME=path/to/backtest.zip (defaults to latest backtest in user_data/backtest_results)"; \
		echo "Optional: TRADE_SOURCE=DB DB=db_filename.sqlite (only use if you want database trades instead of backtest)"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) plot-profit \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		$(if $(PAIRS),-p $(PAIRS)) \
		$(if $(TIMEFRAME),-i $(TIMEFRAME)) \
		$(if $(TIMERANGE),--timerange $(TIMERANGE)) \
		$(if $(AUTO_OPEN),--auto-open) \
		$(if $(filter DB,$(TRADE_SOURCE)),--db-url sqlite:////freqtrade/db/$(DB) --trade-source DB,--backtest-filename $(if $(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results/$(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results))

# Run hyperparameter optimization on a strategy.
# Requires CONTAINER and STRATEGY; uses TIMEFRAME, TIMERANGE, EPOCHS, SPACES, and LOSS variables.
EPOCHS ?= 500
SPACES ?= buy sell
LOSS ?= SharpeHyperOptLossDaily
hyperopt:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make hyperopt CONTAINER=YourContainer STRATEGY=YourStrategy [EPOCHS=500] [SPACES='buy sell'] [LOSS=SharpeHyperOptLossDaily] [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Error: STRATEGY is not set. Usage: make hyperopt CONTAINER=YourContainer STRATEGY=YourStrategy [EPOCHS=500] [SPACES='buy sell'] [LOSS=SharpeHyperOptLossDaily] [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) hyperopt \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		--hyperopt-loss $(LOSS) \
		--spaces $(SPACES) \
		--epochs $(EPOCHS) \
		--timerange $(TIMERANGE) \
		$(VERBOSE)

# Start live trading with a given strategy via Docker.
# Requires CONTAINER and STRATEGY; optionally accepts DB and FREQAI_MODEL.
trade:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make trade CONTAINER=YourContainer STRATEGY=YourStrategy [DB=yourdb.sqlite] [FREQAI_MODEL=YourModel] [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Error: STRATEGY is not set. Usage: make trade CONTAINER=YourContainer STRATEGY=YourStrategy [DB=yourdb.sqlite] [FREQAI_MODEL=YourModel] [VERBOSE=-v/-vv/-vvv]"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) trade \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		$(if $(FREQAI_MODEL),--freqaimodel $(FREQAI_MODEL)) \
		$(if $(DB),--db-url sqlite:////freqtrade/db/$(DB)) \
		$(VERBOSE)

# ==============================================================================
# GMX data collection (uses gmx-data-collector submodule)
# ==============================================================================
# Collects candles + funding from GMX, exports to user_data/data/gmx/futures/
# Requires: source .env && make gmx-data (HYPERSYNC_API_TOKEN, JSON_RPC_ARBITRUM)
# ==============================================================================

GMX_COLLECTOR_DIR ?= ./gmx-data-collector
GMX_FEATHER_DIR ?= $(abspath ./user_data/data)
CONCURRENCY ?= 5

# Ensure submodule is initialized
gmx-data-collector-init:
	git submodule update --init --recursive gmx-data-collector

# Full GMX data pipeline: collect + export into user_data/data
# Invokes CLI directly so it works regardless of submodule Makefile version
gmx-data: gmx-data-collector-init
	@echo "Running GMX data collection and export..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli collect --update --output-dir ./data --concurrency $(CONCURRENCY)
	@cd $(GMX_COLLECTOR_DIR) && poetry run python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet --resume
	@echo "Exporting to Freqtrade format..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir $(GMX_FEATHER_DIR)
	@echo "GMX data ready in user_data/data/gmx/futures/"