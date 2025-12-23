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