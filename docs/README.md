# Documentation

Complete documentation for GMX Freqtrade backtesting setup.

## Getting Started

New to this project? Start here:

### [Quick Start](QUICKSTART.md)
Get up and running with the ADX strategy in 10 minutes. Covers setup, downloading data, backtesting, and generating equity curves.

**Start here if:** You want to see results quickly.

---

### [Getting Started](getting-started.md)
Complete installation guide and your first backtest. Covers prerequisites, Python/uv setup, data download, and running backtests.

**Start here if:** You're setting up for the first time.

---

## Core Documentation

### [GMX Specifics](gmx-specifics.md)
Understanding how GMX differs from traditional exchanges. Essential reading before building strategies.

**Topics:**
- What is GMX and how it works
- Key differences (no volume data, funding fees)
- Available data and trading implications
- Cost structure (fees, gas, funding)
- Liquidity pool model vs order books

**Read this if:** You want to understand GMX constraints and opportunities.

---

### [Equity Curves](equity-curves.md)
Generating and analyzing equity curves from backtest results.

**Topics:**
- Creating custom equity curve visualizations with Python
- Analyzing drawdowns and performance patterns
- Monthly returns heatmap analysis
- Complete example script (equity_curve.png + monthly_returns.png)

**Read this if:** You want to visualize backtest performance over time.

---

## Technical Documentation

### [Architecture](architecture.md)
Technical deep dive into how GMX integration works. For developers and advanced users.

**Topics:**
- Monkeypatch approach explained
- Component architecture
- CCXT integration layer
- Freqtrade integration layer
- Data flow diagrams
- Extending the system

**Read this if:** You want to understand or modify the integration.

---

### [Troubleshooting](troubleshooting.md)
Common issues and solutions.

**Topics:**
- Installation problems (venv, dependencies, system packages)
- Configuration errors (pairs, secrets, RPC)
- Data download issues (GraphQL, timerange)
- Backtest failures (no trades, strategy errors)
- GMX-specific issues (exchange not recognized, monkeypatch)
- Diagnostic commands

**Read this if:** Something isn't working.

---

## Quick Links

### By User Type

**Traders/Analysts:**
1. [Quick Start](QUICKSTART.md) - 10-minute setup with ADX strategy
2. [Getting Started](getting-started.md) - Detailed setup guide
3. [GMX Specifics](gmx-specifics.md) - Understand GMX differences
4. [Equity Curves](equity-curves.md) - Visualize performance

**Developers:**
1. [Architecture](architecture.md) - Technical implementation
2. [GMX Specifics](gmx-specifics.md) - GMX integration details
3. [Troubleshooting](troubleshooting.md) - Debug issues

### By Task

**Quick start (10 min):**
→ [Quick Start Guide](QUICKSTART.md)

**Installing:**
→ [Getting Started](getting-started.md)

**First backtest:**
→ [Getting Started - Your First Backtest](getting-started.md#your-first-backtest)

**Generating equity curves:**
→ [Equity Curves](equity-curves.md)

**Solving problems:**
→ [Troubleshooting](troubleshooting.md)

**Understanding GMX:**
→ [GMX Specifics](gmx-specifics.md)

**Technical details:**
→ [Architecture](architecture.md)

---

## External Resources

### Freqtrade
- [Official Documentation](https://www.freqtrade.io/en/stable/)
- [Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Backtesting](https://www.freqtrade.io/en/stable/backtesting/)
- [Discord Community](https://discord.gg/freqtrade)

### GMX
- [GMX Documentation](https://docs.gmx.io)
- [GMX Stats](https://stats.gmx.io)
- [GMX Discord](https://discord.gg/gmx)

### web3-ethereum-defi
- [GitHub Repository](https://github.com/tradingstrategy-ai/web3-ethereum-defi)
- [GMX Module Documentation](https://github.com/tradingstrategy-ai/web3-ethereum-defi/tree/master/eth_defi/gmx)

### Technical
- [CCXT Documentation](https://docs.ccxt.com/)
- [TA-Lib Indicators](https://mrjbq7.github.io/ta-lib/func_groups/momentum_indicators.html)
- [Pandas Documentation](https://pandas.pydata.org/docs/)

---

## Documentation Structure

```
docs/
├── README.md                    # This file (documentation index)
├── QUICKSTART.md               # 10-minute ADX strategy setup
├── getting-started.md          # Installation and first backtest
├── gmx-specifics.md            # GMX differences and characteristics
├── equity-curves.md            # Generating equity curves
├── architecture.md             # Technical implementation
└── troubleshooting.md          # Common issues and solutions
```

---

## Contributing to Documentation

Found an error? Want to improve documentation?

1. Fork the repository
2. Edit markdown files in `docs/`
3. Test locally (markdown preview)
4. Submit pull request

**Documentation guidelines:**
- Clear, concise writing
- Code examples with explanations
- Real-world use cases
- GMX-specific considerations highlighted

---

## Getting Help

**Can't find what you need?**

1. Check [Troubleshooting](troubleshooting.md) first
2. Search existing GitHub issues
3. Ask on Freqtrade Discord
4. Create a GitHub issue with details

**When asking for help, include:**
- What you're trying to do
- What you've tried
- Error messages (full output)
- Configuration (sanitized)
- Environment (OS, Python version)

---

## Quick Start Reminder

```bash
# 1. Clone and setup
git clone <repo>
cd freqtrade-gmx-demo
git submodule update --init --recursive

# 2. Clone Freqtrade (use freqtrade-develop to avoid namespace conflicts)
git clone https://github.com/freqtrade/freqtrade.git freqtrade-develop

# 3. Create venv in main project directory
uv venv .venv
source .venv/bin/activate

# 4. Install Freqtrade and dependencies
uv pip install -r freqtrade-develop/requirements.txt
uv pip install -e freqtrade-develop/
uv pip install -e "deps/web3-ethereum-defi[data,ccxt]"

# 5. Download data
./freqtrade-gmx download-data --exchange gmx --config configs/pingpong_gmx.json --config configs/pingpong_gmx.secrets.json --timeframe 5m --timerange $(date -d "5 months ago" +%Y%m%d)-$(date -d yesterday +%Y%m%d)

# 6. Backtest
./freqtrade-gmx backtesting --strategy Pingpong --config configs/pingpong_gmx.json --config configs/pingpong_gmx.secrets.json --timerange $(date -d "5 months ago" +%Y%m%d)-$(date -d yesterday +%Y%m%d)
```

See [Getting Started](getting-started.md) for detailed instructions.
