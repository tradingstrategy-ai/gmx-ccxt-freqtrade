TIMEFRAME ?= 5m
# GMX's data API serves a rolling ~6-month window ending yesterday; a hardcoded
# date range goes dead the moment it falls outside that window.
DATE_BIN := $(shell if date -d yesterday +%Y%m%d >/dev/null 2>&1; then printf date; elif command -v gdate >/dev/null 2>&1; then printf gdate; else printf missing; fi)
ifeq ($(DATE_BIN),missing)
$(error GNU date is required; install coreutils with Homebrew on macOS)
endif
TIMERANGE ?= $(shell $(DATE_BIN) -d '5 months ago' +%Y%m%d)-$(shell $(DATE_BIN) -d 'yesterday' +%Y%m%d)
# Verbosity level for freqtrade commands (empty, -v, -vv, or -vvv)
VERBOSE ?=

# Load .env file if it exists (for JSON_RPC_ARBITRUM, HYPERSYNC_API_TOKEN)
-include .env
export

# Config to use for backtesting/hyperopt (override with CONFIG=...)
CONFIG ?= adxmomentum_gmx

# Generate a table of contents for README.md from Markdown headings.
toc:
	python scripts/generate_toc.py

# DEPRECATED: 'make data' used freqtrade download-data which OOMs on large datasets.
data:
	@echo ""
	@echo "ERROR: 'make data' has been removed."
	@echo ""
	@echo "  Incremental update:  make refresh-data"
	@echo "  Full history:        make full-data"
	@echo ""
	@exit 1

# ==============================================================================
# Backtesting & analysis (uses dedicated backtest-runner container)
# ==============================================================================
# These targets use a separate 'backtest-runner' container that shares data
# volumes with the live bots but runs independently. Live bots are never
# touched or interrupted.

# Run a strategy backtest.
backtest:
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Usage: make backtest STRATEGY=YourStrategy [CONFIG=adxmomentum_gmx] [TIMEFRAME=1h] [TIMERANGE=20260101-20260319]"; \
		exit 1; \
	fi
	docker compose run --rm backtest-runner backtesting \
		--config /freqtrade/configs/$(CONFIG).json \
		--config /freqtrade/configs/$(CONFIG).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		--timeframe $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--cache none \
		$(VERBOSE)

# Run hyperparameter optimization.
EPOCHS ?= 500
SPACES ?= buy sell
LOSS ?= SharpeHyperOptLossDaily
hyperopt:
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Usage: make hyperopt STRATEGY=YourStrategy [CONFIG=adxmomentum_gmx] [EPOCHS=500] [SPACES='buy sell']"; \
		exit 1; \
	fi
	docker compose run --rm backtest-runner hyperopt \
		--config /freqtrade/configs/$(CONFIG).json \
		--config /freqtrade/configs/$(CONFIG).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		--hyperopt-loss $(LOSS) \
		--spaces $(SPACES) \
		--epochs $(EPOCHS) \
		--timerange $(TIMERANGE) \
		$(VERBOSE)

# List available trading pairs on the exchange.
list-pairs:
	docker compose run --rm backtest-runner list-pairs \
		--config /freqtrade/configs/$(CONFIG).json \
		--config /freqtrade/configs/$(CONFIG).secrets.json \
		--exchange $(or $(EXCHANGE),gmx) \
		$(VERBOSE)

# Plot strategy signals overlaid on price data.
plot-dataframe:
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Usage: make plot-dataframe STRATEGY=YourStrategy [CONFIG=adxmomentum_gmx]"; \
		exit 1; \
	fi
	docker compose run --rm backtest-runner plot-dataframe \
		--config /freqtrade/configs/$(CONFIG).json \
		--config /freqtrade/configs/$(CONFIG).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		$(if $(PAIRS),-p $(PAIRS)) \
		$(if $(TIMEFRAME),-i $(TIMEFRAME)) \
		$(if $(TIMERANGE),--timerange $(TIMERANGE)) \
		--backtest-filename $(if $(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results/$(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results) \
		$(if $(INDICATORS1),--indicators1 $(INDICATORS1)) \
		$(if $(INDICATORS2),--indicators2 $(INDICATORS2))

# Plot equity curve.
plot-profit:
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Usage: make plot-profit STRATEGY=YourStrategy [CONFIG=adxmomentum_gmx]"; \
		exit 1; \
	fi
	docker compose run --rm backtest-runner plot-profit \
		--config /freqtrade/configs/$(CONFIG).json \
		--config /freqtrade/configs/$(CONFIG).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		$(if $(PAIRS),-p $(PAIRS)) \
		$(if $(TIMEFRAME),-i $(TIMEFRAME)) \
		$(if $(TIMERANGE),--timerange $(TIMERANGE)) \
		$(if $(AUTO_OPEN),--auto-open) \
		$(if $(filter DB,$(TRADE_SOURCE)),--db-url sqlite:////freqtrade/db/$(DB) --trade-source DB,--backtest-filename $(if $(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results/$(BACKTEST_FILENAME),/freqtrade/user_data/backtest_results))

# ==============================================================================
# Data refresh
# ==============================================================================

# Incremental data refresh: top up ALL local data in one command.
# Downloads last 30 days of GMX candles, refreshes Binance volume, OI, liquidity,
# then fills gaps with Binance. No external API tokens needed.
# Uses docker exec on the live vault container — zero extra memory.
REFRESH_DAYS ?= 30
REFRESH_CONTAINER ?= adxmomentum_gmx
REFRESH_CONFIG ?= adxmomentum_gmx
refresh-data:
	@echo "Step 1/4: Downloading last $(REFRESH_DAYS) days of GMX candles..."
	@START=$$($(DATE_BIN) -d "-$(REFRESH_DAYS) days" +%Y%m%d); \
	END=$$($(DATE_BIN) +%Y%m%d); \
	echo "  Timerange: $$START-$$END"; \
	docker exec $(REFRESH_CONTAINER) \
		python -u -B -m eth_defi.gmx.freqtrade.patched_entrypoint \
		freqtrade download-data \
		--config /freqtrade/configs/$(REFRESH_CONFIG).json \
		--config /freqtrade/configs/$(REFRESH_CONFIG).secrets.json \
		--timeframes 1h 4h 1d \
		--timerange $$START-$$END \
		--prepend
	@echo ""
	@echo "Step 2/4: Refreshing Binance volume + GMX OI + pool liquidity..."
	python3 scripts/refresh_all_data.py
	@echo ""
	@echo "Step 3/4: Filling internal gaps with Binance data..."
	python3 scripts/merge_gmx_binance.py
	@echo ""
	@echo "Step 4/4: Backfilling historical data from Binance..."
	python3 scripts/backfill_1h_5m_from_binance.py
	@echo ""
	@echo "✓ All data ready in user_data/data/gmx/"

# ==============================================================================
# GMX data collection (uses gmx-data-collector submodule)
# ==============================================================================

GMX_COLLECTOR_DIR ?= ./gmx-data-collector
GMX_FEATHER_DIR ?= $(abspath ./user_data/data)
CONCURRENCY ?= 5

gmx-data-collector-init:
	git submodule update --init --recursive gmx-data-collector

gmx-data: gmx-data-collector-init
	@echo "Running GMX data collection and export..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli collect --update --output-dir ./data --concurrency $(CONCURRENCY)
	@cd $(GMX_COLLECTOR_DIR) && poetry run python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet --resume
	@echo "Exporting to Freqtrade format..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir $(GMX_FEATHER_DIR)
	@echo "GMX data ready in user_data/data/gmx/futures/"

# Full history rebuild from genesis. Slow (hours). Requires .env.
full-data: gmx-data-collector-init
	@echo "Step 1/4: Full GMX data collection from genesis (this will take a while)..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli collect --full --output-dir ./data --concurrency $(CONCURRENCY)
	@cd $(GMX_COLLECTOR_DIR) && poetry run python scripts/extract_unified_funding.py --network arbitrum --output-dir ./data/funding --output parquet
	@echo ""
	@echo "Step 2/4: Exporting to Freqtrade format..."
	@cd $(GMX_COLLECTOR_DIR) && poetry run python -m gmx_historical_data.cli export-freqtrade --data-dir ./data --output-dir $(GMX_FEATHER_DIR)
	@echo ""
	@echo "Step 3/4: Filling internal gaps with Binance data..."
	python3 scripts/merge_gmx_binance.py
	@echo ""
	@echo "Step 4/4: Backfilling historical data from Binance..."
	python3 scripts/backfill_1h_5m_from_binance.py
	@echo ""
	@echo "✓ Full data ready in user_data/data/gmx/"

# ==============================================================================
# Security
# ==============================================================================

.PHONY: install-hooks scan-secrets

install-hooks: ## Install pre-commit hooks (nbstripout + gitleaks + secret patterns)
	pre-commit install
	@echo "Pre-commit hooks installed"

scan-secrets: ## Scan entire working tree for secrets (via gitleaks)
	gitleaks detect --source . --verbose
