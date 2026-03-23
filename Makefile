TIMEFRAME ?= 5m
TIMERANGE ?= 20250101-20251130
# Verbosity level for freqtrade commands (empty, -v, -vv, or -vvv)
VERBOSE ?=

# Load .env file if it exists (for JSON_RPC_ARBITRUM, HYPERSYNC_API_TOKEN)
-include .env
export

# Generate a table of contents for README.md from Markdown headings.
# Places/updates the TOC above the "# Overview" section.
toc:
	python scripts/generate_toc.py

# DEPRECATED: 'make data' used freqtrade download-data which OOMs on large datasets.
# Use 'make refresh-data' or 'make full-data' instead.
data:
	@echo ""
	@echo "ERROR: 'make data' has been removed."
	@echo ""
	@echo "  Incremental update:  source .env && make refresh-data"
	@echo "  Full history:        source .env && make full-data"
	@echo ""
	@exit 1

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
	@cd $(GMX_COLLECTOR_DIR) && python -m gmx_historical_data.cli collect --update --output-dir ./data --concurrency $(CONCURRENCY)
	@cd $(GMX_COLLECTOR_DIR) && python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet --resume
	@echo "Exporting to Freqtrade format..."
	@cd $(GMX_COLLECTOR_DIR) && python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir $(GMX_FEATHER_DIR)
	@echo "GMX data ready in user_data/data/gmx/futures/"

# Incremental data refresh: top up local GMX data + merge + backfill from Binance.
# Downloads the last 30 days of GMX data (safe, small memory footprint) using the
# vault config's full pair universe, then rebuilds the merged dataset.
# No external API tokens needed — uses the same GMX GraphQL API as live trading.
REFRESH_DAYS ?= 30
REFRESH_CONTAINER ?= ichiv2_gmx_vault
REFRESH_CONFIG ?= ichiv2_gmx_prod_vault
refresh-data:
	@echo "Step 1/3: Downloading last $(REFRESH_DAYS) days of GMX data..."
	@START=$$(date -d "-$(REFRESH_DAYS) days" +%Y%m%d); \
	END=$$(date +%Y%m%d); \
	echo "  Timerange: $$START-$$END"; \
	docker compose run --rm $(REFRESH_CONTAINER) download-data \
		--config /freqtrade/configs/$(REFRESH_CONFIG).json \
		--config /freqtrade/configs/$(REFRESH_CONFIG).secrets.json \
		--timeframes 1h 4h 1d \
		--timerange $$START-$$END \
		--prepend
	@echo ""
	@echo "Step 2/3: Merging GMX candles with Binance gap-fill..."
	python scripts/merge_gmx_binance.py
	@echo ""
	@echo "Step 3/3: Backfilling historical data from Binance..."
	python scripts/backfill_1h_5m_from_binance.py
	@echo ""
	@echo "✓ Data ready in user_data/data/gmx_complete_w_binance/"

# Full history rebuild: collect all GMX data from genesis + merge + backfill.
# Use this for first-time setup or after data loss. Slow (hours).
# Requires .env with JSON_RPC_ARBITRUM and HYPERSYNC_API_TOKEN.
# Uses gmx-data-collector submodule for memory-safe collection with checkpoints.
full-data: gmx-data-collector-init
	@echo "Step 1/4: Full GMX data collection from genesis (this will take a while)..."
	@cd $(GMX_COLLECTOR_DIR) && python -m gmx_historical_data.cli collect --full --output-dir ./data --concurrency $(CONCURRENCY)
	@cd $(GMX_COLLECTOR_DIR) && python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet
	@echo ""
	@echo "Step 2/4: Exporting to Freqtrade format..."
	@cd $(GMX_COLLECTOR_DIR) && python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir $(GMX_FEATHER_DIR)
	@echo ""
	@echo "Step 3/4: Merging GMX candles with Binance gap-fill..."
	python scripts/merge_gmx_binance.py
	@echo ""
	@echo "Step 4/4: Backfilling historical data from Binance..."
	python scripts/backfill_1h_5m_from_binance.py
	@echo ""
	@echo "✓ Full data ready in user_data/data/gmx_complete_w_binance/"

# ==============================================================================
# Security
# ==============================================================================

.PHONY: install-hooks scan-secrets

install-hooks: ## Install pre-commit hooks (nbstripout + gitleaks + secret patterns)
	pre-commit install
	@echo "Pre-commit hooks installed"

scan-secrets: ## Scan entire working tree for secrets (via gitleaks)
	gitleaks detect --source . --verbose
