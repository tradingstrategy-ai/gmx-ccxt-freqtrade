"""
GMX Liquidity Filter - Filter pairs by GMX pool liquidity.

Live mode: fetches available liquidity directly from the GMX REST API
(arbitrum-api.gmxinfra.io/markets/info) via its own GMXAPI instance.
This is independent of the exchange's market data — same pattern as
HistoricalVolumePairList creating its own Binance instance.

Backtest mode: reads daily pool liquidity feather files from
datadir/futures_metrics/ directory and removes pairs whose pool liquidity is
below the configured minimum threshold.

Preserves incoming sort order from upstream handlers in both modes.

Usage in config (as a filter after HistoricalVolumePairList):
    "pairlists": [
        {"method": "StaticPairList"},
        {"method": "HistoricalVolumePairList", ...},
        {
            "method": "GMXLiquidityFilter",
            "min_pool_liquidity": 500000
        }
    ],
    "enable_dynamic_pairlist": true
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from freqtrade.exchange.exchange_types import Tickers
from freqtrade.plugins.pairlist.IPairList import IPairList, PairlistParameter, SupportsBacktesting
from cachetools import TTLCache


logger = logging.getLogger(__name__)


class GMXLiquidityFilter(IPairList):
    """
    Filter pairs by GMX pool liquidity.

    Live mode: fetches liquidity from GMX REST API directly (own GMXAPI instance).
    Backtest mode: reads pre-downloaded pool_liquidity feather files.
    """

    supports_backtesting = SupportsBacktesting.YES

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._min_pool_liquidity: float = self._pairlistconfig.get(
            "min_pool_liquidity", 500_000
        )

        # Live mode: cached liquidity + lazy GMXAPI instance
        self._pair_cache: TTLCache = TTLCache(maxsize=1, ttl=self.refresh_period)
        self._gmx_api = None

        # Backtest mode data (lazy-loaded)
        self._liq_data: pd.DataFrame | None = None

    @property
    def needstickers(self) -> bool:
        return False

    def short_desc(self) -> str:
        return f"{self.name} - min pool liquidity ${self._min_pool_liquidity:,.0f}"

    @staticmethod
    def description() -> str:
        return "Filter pairs by GMX pool liquidity threshold."

    @staticmethod
    def available_parameters() -> dict[str, PairlistParameter]:
        return {
            "min_pool_liquidity": {
                "type": "number",
                "default": 500000,
                "description": "Minimum pool liquidity",
                "help": "Minimum GMX pool liquidity in USD to keep a pair.",
            },
        }

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    def _is_live(self) -> bool:
        """True when running live/dry-run (no backtest time set)."""
        return getattr(self._pairlistmanager, '_current_time', None) is None

    # ------------------------------------------------------------------
    # Live mode: GMX REST API (own instance, independent of exchange)
    # ------------------------------------------------------------------

    def _get_gmx_api(self):
        """Lazy-initialise a GMXAPI instance for fetching market info."""
        if self._gmx_api is None:
            from eth_defi.gmx.api import GMXAPI

            self._gmx_api = GMXAPI(chain="arbitrum")
        return self._gmx_api

    def _get_live_liquidity(self) -> dict[str, float]:
        """Fetch pool liquidity from GMX REST API.

        Calls arbitrum-api.gmxinfra.io/markets/info directly (same pattern as
        HistoricalVolumePairList creating its own Binance instance).
        Aggregates liquidity across collateral variants per base token.
        Values are in USD (converted from 1e30 fixed-point).
        """
        cached = self._pair_cache.get("liquidity")
        if cached is not None:
            return cached

        try:
            api = self._get_gmx_api()
            data = api.get_markets_info()
        except Exception as e:
            logger.warning("GMXLiquidityFilter: REST API fetch failed: %s", e)
            return {}

        markets = data.get("markets", [])
        if not markets:
            return {}

        # Aggregate available liquidity across collateral variants per token.
        # Market name format: "SOL/USD [SOL-USDC]", "BTC/USD [WBTC.b-USDC]"
        # We extract the base token (SOL, BTC) and sum liquidity across variants.
        liquidity: dict[str, float] = {}
        for m in markets:
            if not m.get("isListed"):
                continue
            name = m.get("name", "")
            if "/" not in name:
                continue
            base = name.split("/")[0]
            gmx_pair = f"{base}/USDC:USDC"

            avail_long = int(m.get("availableLiquidityLong", 0)) / 1e30
            avail_short = int(m.get("availableLiquidityShort", 0)) / 1e30
            total = avail_long + avail_short

            # Aggregate across collateral variants (BTC has 3 markets)
            liquidity[gmx_pair] = liquidity.get(gmx_pair, 0) + total

        if liquidity:
            self._pair_cache["liquidity"] = liquidity.copy()

        logger.info(
            "GMXLiquidityFilter [live]: fetched liquidity for %d markets from "
            "GMX REST API (%d unique tokens). Source: %s",
            len(markets), len(liquidity),
            api.base_url if hasattr(api, "base_url") else "arbitrum-api.gmxinfra.io",
        )
        return liquidity

    def _filter_live(self, pairlist: list[str]) -> list[str]:
        """Filter pairlist using live GMX REST API data."""
        liquidity = self._get_live_liquidity()

        if not liquidity:
            logger.warning(
                "GMXLiquidityFilter: no liquidity data from REST API. "
                "Passing all %d pairs through UNFILTERED.",
                len(pairlist),
            )
            return pairlist

        liquid_pairs = {p for p, v in liquidity.items() if v >= self._min_pool_liquidity}
        result = [p for p in pairlist if p in liquid_pairs]
        removed = [p.split('/')[0] for p in pairlist if p not in liquid_pairs]
        no_data = [p.split('/')[0] for p in pairlist if p not in liquidity]

        logger.info(
            "GMXLiquidityFilter [live]: %d in -> %d out. "
            "Removed %d below $%s threshold: %s",
            len(pairlist), len(result), len(removed),
            f"{self._min_pool_liquidity:,.0f}", removed[:10],
        )
        if no_data:
            logger.info(
                "GMXLiquidityFilter [live]: %d pairs had no liquidity data "
                "(removed): %s",
                len(no_data), no_data[:10],
            )
        return result

    # ------------------------------------------------------------------
    # Backtest mode: feather files
    # ------------------------------------------------------------------

    @staticmethod
    def _file_token_to_pair(token: str) -> str:
        """Convert 'BTC' -> 'BTC/USDC:USDC'."""
        return f"{token}/USDC:USDC"

    def _load_liquidity_data(self) -> None:
        """Load pool liquidity feather files. Called once lazily."""
        if self._liq_data is not None:
            return

        datadir = Path(self._config.get("datadir", "user_data/data/gmx"))
        futures_dir = datadir / "futures_metrics"

        liq_series: dict[str, pd.Series] = {}

        for f in sorted(futures_dir.glob("*_USDC_USDC-1d-pool_liquidity.feather")):
            token = f.name.split("_USDC_USDC-1d-")[0]
            pair = self._file_token_to_pair(token)
            df = pd.read_feather(f)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            liq_series[pair] = df.set_index("date")["close"]

        self._liq_data = pd.DataFrame(liq_series)

        logger.info(
            "GMXLiquidityFilter: loaded %d liquidity series, date range %s to %s",
            len(liq_series),
            self._liq_data.index.min(), self._liq_data.index.max(),
        )

    def _filter_backtest(self, pairlist: list[str]) -> list[str]:
        """Backtest mode: look up historical liquidity from feather files."""
        self._load_liquidity_data()

        if self._liq_data is None or self._liq_data.empty:
            return pairlist

        current_time = getattr(self._pairlistmanager, '_current_time', None)
        if current_time is None:
            current_time = datetime.utcnow()

        target_date = pd.Timestamp(current_time).normalize().tz_localize(None)

        # Find the most recent date <= target_date in the liquidity data
        valid_dates = self._liq_data.index[self._liq_data.index <= target_date]
        if valid_dates.empty:
            # No liquidity data available yet, pass all pairs through
            return pairlist

        lookup_date = valid_dates[-1]
        liq_row = self._liq_data.loc[lookup_date].dropna()

        # Build set of pairs that pass the liquidity threshold
        liquid_pairs = set(liq_row[liq_row >= self._min_pool_liquidity].index)

        # Filter pairlist, preserving order. Pairs without liquidity data are removed.
        result = [p for p in pairlist if p in liquid_pairs]
        removed = [p.split('/')[0] for p in pairlist if p not in liquid_pairs]

        logger.info(
            "GMXLiquidityFilter [%s]: %d in -> %d out. Removed %d: %s",
            target_date.date(), len(pairlist), len(result), len(removed), removed[:10],
        )

        return result

    # ------------------------------------------------------------------
    # Pairlist interface
    # ------------------------------------------------------------------

    def filter_pairlist(self, pairlist: list[str], tickers: Tickers) -> list[str]:
        """
        Filter pairs by pool liquidity. Preserves incoming sort order.

        Live: reads liquidity from exchange market data.
        Backtest: looks up historical liquidity from feather files.
        """
        if self._is_live():
            return self._filter_live(pairlist)
        return self._filter_backtest(pairlist)
