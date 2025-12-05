TIMEFRAME ?= 5m
TIMERANGE ?= 20250101-20251130
# Verbosity level for freqtrade commands (empty, -v, -vv, or -vvv)
VERBOSE ?=

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
