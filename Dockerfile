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
RUN pip install --user --force-reinstall --no-deps "/tmp/web3-ethereum-defi[web3v7]"

# Use the patched entrypoint
ENTRYPOINT ["python", "-u", "-B", "-m", "eth_defi.gmx.freqtrade.patched_entrypoint", "freqtrade"]
# Default to trade mode
CMD ["trade"]

