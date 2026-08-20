FROM freqtradeorg/freqtrade:2026.7

# Switch user to root to install build dependencies
USER root

# Install build dependencies for web3-ethereum-defi and uv for fast Python installs.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        python3-dev \
        libgmp-dev \
        libmpfr-dev \
        libmpc-dev && \
    python -m pip install --no-cache-dir uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install web3-ethereum-defi dependency with extras
COPY deps/web3-ethereum-defi /tmp/web3-ethereum-defi
RUN uv pip install --system --force-reinstall "/tmp/web3-ethereum-defi[ccxt]"

# Install plotly for freqtrade plotting commands
RUN uv pip install --system plotly

# Switch back to ftuser
USER ftuser

# Install custom pairlist plugins into freqtrade's plugin directory
COPY plugins/pairlist/HistoricalVolumePairList.py /freqtrade/freqtrade/plugins/pairlist/
COPY plugins/pairlist/GMXLiquidityFilter.py /freqtrade/freqtrade/plugins/pairlist/


# Use the patched entrypoint
ENTRYPOINT ["python", "-u", "-B", "-m", "eth_defi.gmx.freqtrade.patched_entrypoint", "freqtrade"]
# Default to trade mode
CMD ["trade"]
