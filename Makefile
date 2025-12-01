TIMEFRAME ?= 1m
TIMERANGE ?= 20250101-20251130

data:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make data CONTAINER=YourContainer"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) download-data \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--timeframes $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--prepend

backtest:
	@if [ -z "$(CONTAINER)" ]; then \
		echo "Error: CONTAINER is not set. Usage: make backtest CONTAINER=YourContainer STRATEGY=YourStrategy"; \
		exit 1; \
	fi
	@if [ -z "$(STRATEGY)" ]; then \
		echo "Error: STRATEGY is not set. Usage: make backtest CONTAINER=YourContainer STRATEGY=YourStrategy"; \
		exit 1; \
	fi
	docker compose run --rm $(CONTAINER) backtesting \
		--config /freqtrade/configs/$(CONTAINER).json \
		--config /freqtrade/configs/$(CONTAINER).secrets.json \
		--strategy-path /freqtrade/strategies \
		--strategy $(STRATEGY) \
		--timerange $(TIMERANGE)
