FROM freqtradeorg/freqtrade:2025.10

# Switch user to root to install build dependencies
USER root

# Install build dependencies for web3-ethereum-defi
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        python3-dev \
        libgmp-dev \
        libmpfr-dev \
        libmpc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch back to ftuser
USER ftuser

# Copy and install web3-ethereum-defi dependency with extras
COPY deps/web3-ethereum-defi /tmp/web3-ethereum-defi
RUN pip install --user --force-reinstall "/tmp/web3-ethereum-defi[web3v7]"

# Install plotly for freqtrade plotting commands
RUN pip install --user plotly

# Install custom pairlist plugins into freqtrade's plugin directory
COPY plugins/pairlist/HistoricalVolumePairList.py /freqtrade/freqtrade/plugins/pairlist/
COPY plugins/pairlist/GMXLiquidityFilter.py /freqtrade/freqtrade/plugins/pairlist/

# Apply minimal freqtrade patches for GMX compatibility
# Fix: taker fee KeyError for GMX markets (market dict missing 'taker' key)
RUN sed -i 's/taker_fee_rate = market\["taker"\] or/taker_fee_rate = market.get("taker") or/' \
    /freqtrade/freqtrade/exchange/exchange.py && \
    sed -i 's/\.get("taker", 0.001)/.get("taker", 0.001) or 0.0006/' \
    /freqtrade/freqtrade/exchange/exchange.py

# Use the patched entrypoint
ENTRYPOINT ["python", "-u", "-B", "-m", "eth_defi.gmx.freqtrade.patched_entrypoint", "freqtrade"]
# Default to trade mode
CMD ["trade"]

