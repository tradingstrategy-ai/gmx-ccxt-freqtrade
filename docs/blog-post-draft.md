# Announcing CCXT and FreqTrade Support for GMX: Bringing Algorithmic Trading to DeFi Perpetuals

_Funded by an Arbitrum DAO grant, Trading Strategy delivers a production-ready CCXT adapter for GMX — enabling quants and algo traders to run strategies on one of DeFi's deepest perpetual futures exchanges._

Trading Strategy has shipped [CCXT](https://tradingstrategy.ai/glossary/ccxt) and [FreqTrade](https://tradingstrategy.ai/glossary/freqtrade) integration for [GMX](https://tradingstrategy.ai/glossary/gmx), the leading [decentralised exchange](https://tradingstrategy.ai/glossary/decentralised-exchange) for [perpetual futures](https://tradingstrategy.ai/glossary/perpetual-future) on [Arbitrum](https://tradingstrategy.ai/glossary). This means [algorithmic traders](https://tradingstrategy.ai/glossary/algorithmic-trading) can now use the same [Python](https://tradingstrategy.ai/glossary/python)-based tools they already know from centralised exchanges — CCXT and FreqTrade — to trade [onchain](https://tradingstrategy.ai/glossary/onchain) perpetuals with deep [liquidity](https://tradingstrategy.ai/glossary/liquidity), [self-custodial](https://tradingstrategy.ai/glossary/self-custodial) execution, and full [DeFi](https://tradingstrategy.ai/glossary/defi) [composability](https://tradingstrategy.ai/glossary/composability).

[Get started with the tutorial and example strategies on GitHub.](https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade)

## Why this matters

Quantitative traders have long relied on CCXT as the standard interface for [centralised exchanges](https://tradingstrategy.ai/glossary/cex) like Binance, Coinbase, and Kraken. But when it comes to onchain [DEX](https://tradingstrategy.ai/glossary/dex) trading, the tooling gap has been significant: smart contract interaction, [gas fee](https://tradingstrategy.ai/glossary/gas-fee) management, [MEV](https://tradingstrategy.ai/glossary/mev) protection, and onchain data ingestion all require specialised knowledge that most [quants](https://tradingstrategy.ai/glossary/quant) shouldn't need to worry about.

This integration bridges that gap. By wrapping GMX's onchain trading behind a familiar CCXT interface, algo traders can focus on [strategy](https://tradingstrategy.ai/glossary/strategy) development — not blockchain plumbing.

## What is GMX?

[GMX](https://tradingstrategy.ai/glossary/gmx) is a decentralised spot and perpetual exchange that supports low price impact trades with up to 100x [leverage](https://tradingstrategy.ai/glossary/leverage). It routes orders against its own [AMM](https://tradingstrategy.ai/glossary/amm) liquidity pools (GM Pools) and uses Chainlink Data Stream [oracles](https://tradingstrategy.ai/glossary/oracle) for pricing, ensuring fair execution without traditional [order book](https://tradingstrategy.ai/glossary/order-book) manipulation risks.

GMX is live on Arbitrum, Avalanche, and Botanix, offering 90+ perpetual markets and 23 swap markets.

### Current GMX innovations

GMX has been shipping aggressively through 2025–2026:

- **Gasless transactions**: Traders sign wallet messages instead of paying gas directly. Transactions are broadcast via keeper networks like Gelato, creating a frictionless trading experience.
- **GMX Multichain**: Users can trade GMX's full range of perpetuals directly from Ethereum, Base, and BNB Chain, with trade settlement and execution in under 1 second across chains.
- **Express and One-Click trading**: Off-chain message signing and auto-signed local execution modes eliminate wallet popups entirely.
- **Capped price impact**: Net [price impact](https://tradingstrategy.ai/glossary/price-impact) is calculated and charged at position closure rather than opening, enabling virtually zero price impact for highly liquid markets like BTC and ETH.
- **TWAP orders**: [Time-weighted average price](https://tradingstrategy.ai/glossary/twap) orders for splitting large trades across time.

On the roadmap (v2.3):

- **Cross-collateral**: All positions share collateral — positive PnL from existing positions can be used as margin for others, boosting capital efficiency.
- **Market aggregation**: Similar perp markets unified under single groups (e.g., ETH/USD), reducing complexity and consolidating liquidity.

## What is Trading Strategy?

[Trading Strategy](https://tradingstrategy.ai) is the first protocol replacing investment managers with code. It enables both retail and institutional participants to create, deploy, and invest in [automated trading strategies](https://tradingstrategy.ai/glossary/automated-trading-strategy) across decentralised exchanges — covering 1M+ [trading pairs](https://tradingstrategy.ai/glossary/trading-pair) on Ethereum, Polygon, BNB Chain, Arbitrum, and Base — without requiring blockchain expertise.

Key innovations include user-investable [trading vaults](https://web3-ethereum-defi.tradingstrategy.ai/tutorials/lagoon-gmx) for copy trading on GMX where investors deposit and the strategy trades automatically with fully [non-custodial](https://tradingstrategy.ai/glossary/non-custodial) onchain settlement, [smart contract](https://tradingstrategy.ai/glossary/smart-contract) [composability](https://tradingstrategy.ai/glossary/composability) allowing strategies to compose with [lending](https://tradingstrategy.ai/glossary/lending-protocol), [liquidity provision](https://tradingstrategy.ai/glossary/liquidity-provider), and yield farming within a single [vault](https://tradingstrategy.ai/glossary/vault), production-grade [robustness](https://web3-ethereum-defi.tradingstrategy.ai/tutorials/mev-blocker) infrastructure with Arbitrum gas management, [MEV](https://tradingstrategy.ai/glossary/mev) blocking via centralised sequencer routing, and multi-provider [JSON-RPC](https://tradingstrategy.ai/glossary/json-rpc) fallback, [backtesting](https://tradingstrategy.ai/glossary/backtest) with real onchain [historical market data](https://tradingstrategy.ai/glossary/historical-market-data) from GMX's GraphQL API, and transparent performance through real-time dashboards, [equity curves](https://tradingstrategy.ai/glossary/equity-curve), and onchain-verifiable trade-by-trade reporting.

## How the CCXT adapter works

The `web3-ethereum-defi` Python package provides the GMX-specific CCXT adapter. It maps onchain operations to the standard CCXT interface through a monkey-patch approach — no modifications to FreqTrade or CCXT source code are needed.

The adapter:

- Adds `ccxt.gmx` and `ccxt.async_support.gmx` exchange classes
- Registers GMX in FreqTrade's `SUPPORTED_EXCHANGES`
- Translates CCXT calls into GMX [smart contract](https://tradingstrategy.ai/glossary/smart-contract) interactions
- Handles [OHLCV](https://tradingstrategy.ai/glossary/ohlcv) [candle](https://tradingstrategy.ai/glossary/candle) data retrieval from GMX's onchain data
- Manages Arbitrum gas estimation, [execution buffers](https://web3-ethereum-defi.tradingstrategy.ai/api/gmx/_autosummary_gmx/eth_defi.gmx.execution_buffer#module-eth_defi.gmx.execution_buffer), and keeper fee payments

This means you can take an existing FreqTrade strategy, point it at GMX, and start trading — with familiar commands like `freqtrade backtesting`, `freqtrade trade`, and `freqtrade download-data`.

## Test coverage and quality

Quality assurance is a core focus of this grant. The GMX CCXT adapter is backed by comprehensive testing across multiple layers:

<!-- TODO: Update these numbers from the GMX test summary spreadsheet
     https://docs.google.com/spreadsheets/d/1AXpcZvGakdX05omUojxFXdqEu3hIB63rBmwyrMXfbTU/edit?usp=sharing -->

| Layer                                         | Tests                                                                                                                                | Coverage                                                         |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| GMX low-level primitives (web3-ethereum-defi) | See [test summary spreadsheet](https://docs.google.com/spreadsheets/d/1AXpcZvGakdX05omUojxFXdqEu3hIB63rBmwyrMXfbTU/edit?usp=sharing) | Market data, contracts, orders, positions, events, gas utilities |
| CCXT adapter integration                      | Functional                                                                                                                           | Order lifecycle, market loading, OHLCV data, position management |
| FreqTrade end-to-end                          | CI backtest                                                                                                                          | Full strategy backtest in CI pipeline on every commit            |

The FreqTrade framework itself carries 1,400+ test functions across 131 test files covering exchange integrations, bot logic, [backtesting](https://tradingstrategy.ai/glossary/backtest), persistence, RPC, and strategy interfaces.

The CI pipeline runs a complete [backtest](https://tradingstrategy.ai/glossary/backtest) of the ADX [momentum](https://tradingstrategy.ai/glossary/momentum) strategy against real GMX [historical data](https://tradingstrategy.ai/glossary/historical-market-data) on every pull request, validating the full integration end-to-end.

## Example: ADX Momentum strategy backtest

The repository includes a ready-to-run [ADX](https://tradingstrategy.ai/glossary/average-directional-index-adx) momentum strategy trading BTC, ETH, SOL, and DOGE perpetuals on 1h [candles](https://tradingstrategy.ai/glossary/candle). Here's what a 5-month backtest looks like:

| Metric                                                       | Value  |
| ------------------------------------------------------------ | ------ |
| Total trades                                                 | 79     |
| Win rate                                                     | 54.4%  |
| Total profit                                                 | 11.56% |
| [CAGR](https://tradingstrategy.ai/glossary/cagr)             | 28.55% |
| [Sharpe](https://tradingstrategy.ai/glossary/sharpe) ratio   | 2.04   |
| [Sortino](https://tradingstrategy.ai/glossary/sortino) ratio | 4.32   |
| Max [drawdown](https://tradingstrategy.ai/glossary/drawdown) | 6.79%  |
| Market change                                                | -2.70% |

The strategy delivered positive returns even as the underlying market declined — a hallmark of a well-designed [momentum](https://tradingstrategy.ai/glossary/momentum) strategy with proper [risk management](https://tradingstrategy.ai/glossary/risk-adjusted-return).

## Getting started

1. **Clone the repository**: `git clone --recurse-submodules https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade.git`
2. **Install dependencies**: Follow the [installation guide](https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade#installation)
3. **Run a backtest**: Use the included ADX Momentum strategy against real GMX data
4. **Go live**: Fund an Arbitrum [wallet](https://tradingstrategy.ai/glossary/wallet) with USDC and ETH, configure your RPC providers, and start trading

No API keys needed — GMX's onchain data and execution are fully public and permissionless.

## What's next

This CCXT adapter for GMX is the first of several planned [perpetual future](https://tradingstrategy.ai/glossary/perpetual-future) DEX integrations under Trading Strategy's broader [algorithmic trading](https://tradingstrategy.ai/glossary/algorithmic-trading) protocol. We're working on:

- Expanding test coverage across all GMX operations
- Adding more example strategies beyond ADX Momentum
- Supporting additional perpetual DEXs through the same CCXT interface
- Deepening vault integrations for investor-facing strategy deployment

## Links

- [GitHub: gmx-ccxt-freqtrade tutorial](https://github.com/tradingstrategy-ai/gmx-ccxt-freqtrade)
- [GitHub: web3-ethereum-defi (GMX adapter source)](https://github.com/tradingstrategy-ai/web3-ethereum-defi)
- [Grant announcement](https://tradingstrategy.ai/blog/trading-strategy-receives-arbitrum-foundation-grant-to-bring-ccxt-support-to-gmx)
- [GMX test summary spreadsheet](https://docs.google.com/spreadsheets/d/1AXpcZvGakdX05omUojxFXdqEu3hIB63rBmwyrMXfbTU/edit?usp=sharing)
- [Trading Strategy](https://tradingstrategy.ai)
- [GMX](https://app.gmx.io)
- [Trading Strategy Glossary](https://tradingstrategy.ai/glossary)

## Join the community

Have questions or want to build your own strategy on GMX?

- [Join Discord](https://tradingstrategy.ai/community)
- [Follow on Twitter](https://twitter.com/TradingProtocol)
- [Follow on Telegram](https://t.me/trading_protocol)
- [Watch tutorials on YouTube](https://www.youtube.com/@tradingstrategyprotocol)
