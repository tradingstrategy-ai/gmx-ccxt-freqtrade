"""
Historical Volume PairList - Cross-venue volume sorting with live and backtest modes.

Live mode: Fetches current tickers from Binance futures for quoteVolume ranking.
Backtest mode: Reads historical daily candle feather files from another venue
(e.g. Binance) and sorts pairs by rolling quoteVolume.

Designed for venues like GMX where on-chain volume is zero but we want to rank
pairs by real market activity on a reference exchange.

Usage in config (as a filter after StaticPairList):
    "pairlists": [
        {"method": "StaticPairList"},
        {
            "method": "HistoricalVolumePairList",
            "data_source_dir": "user_data/data/binance",
            "number_assets": 75,
            "lookback_days": 7,
            "min_value": 100000,
            "pair_suffix": "_USDT_USDT"
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


class HistoricalVolumePairList(IPairList):
    """
    Sort pairs by volume from an external venue.

    Live mode: fetches current 24h tickers from Binance futures via CCXT.
    Backtest mode: reads pre-downloaded feather files for historical volume.
    """

    supports_backtesting = SupportsBacktesting.YES

    # Binance uses "1000X" naming for small-denomination tokens.
    # Map these to the actual token symbols used on GMX.
    SOURCE_TO_GMX_TOKEN = {
        "1000BONK": "BONK",
        "1000PEPE": "PEPE",
        "1000FLOKI": "FLOKI",
        "1000SHIB": "SHIB",
        "1000SATS": "SATS",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._data_source_dir: str = self._pairlistconfig.get("data_source_dir", "")
        if not self._data_source_dir:
            raise ValueError(
                "HistoricalVolumePairList requires 'data_source_dir' in config "
                "(e.g. 'user_data/data/binance')"
            )

        self._number_assets: int = self._pairlistconfig.get("number_assets", 75)
        self._lookback_days: int = self._pairlistconfig.get("lookback_days", 7)
        self._min_value: float = self._pairlistconfig.get("min_value", 0)
        self._pair_suffix: str = self._pairlistconfig.get("pair_suffix", "_USDT_USDT")

        # Live mode: cached ranking + lazy Binance CCXT instance
        self._pair_cache: TTLCache = TTLCache(maxsize=1, ttl=self.refresh_period)
        self._binance = None

        # Backtest mode: lazy-loaded feather data
        self._volume_data: pd.DataFrame | None = None
        self._daily_rankings: dict[str, list[str]] | None = None

    @property
    def needstickers(self) -> bool:
        return False

    def short_desc(self) -> str:
        return (
            f"{self.name} - Top {self._number_assets} by volume "
            f"(lookback={self._lookback_days}d, min={self._min_value}, "
            f"source={self._data_source_dir})"
        )

    @staticmethod
    def description() -> str:
        return "Sort pairs by volume from external venue (live tickers or historical files)."

    @staticmethod
    def available_parameters() -> dict[str, PairlistParameter]:
        return {
            "data_source_dir": {
                "type": "string",
                "default": "",
                "description": "Data source directory",
                "help": "Path to the external venue data directory (e.g. user_data/data/binance).",
            },
            "number_assets": {
                "type": "number",
                "default": 75,
                "description": "Number of assets",
                "help": "Maximum number of pairs to return, sorted by volume.",
            },
            "lookback_days": {
                "type": "number",
                "default": 7,
                "description": "Lookback days",
                "help": "Number of days for rolling average volume calculation (backtest only).",
            },
            "min_value": {
                "type": "number",
                "default": 0,
                "description": "Minimum quoteVolume",
                "help": "Minimum quoteVolume (rolling avg in backtest, 24h in live) to include.",
            },
            "pair_suffix": {
                "type": "string",
                "default": "_USDT_USDT",
                "description": "Source file pair suffix",
                "help": "File naming suffix for the source venue (e.g. '_USDT_USDT' for Binance).",
            },
        }

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    def _is_live(self) -> bool:
        """True when running live/dry-run (no backtest time set)."""
        return getattr(self._pairlistmanager, '_current_time', None) is None

    # ------------------------------------------------------------------
    # Live mode: Binance tickers
    # ------------------------------------------------------------------

    def _get_binance(self):
        """Lazy-initialise a Binance futures CCXT instance (public, no key)."""
        if self._binance is None:
            import ccxt

            self._binance = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'},
            })
        return self._binance

    def _fetch_live_ranking(self, pairlist: list[str]) -> list[str]:
        """Fetch live 24h quoteVolume from Binance futures, rank and filter."""
        # Trace: log what pairs we received from upstream (StaticPairList)
        btc_in = 'BTC/USDC:USDC' in pairlist
        eth_in = 'ETH/USDC:USDC' in pairlist
        logger.info(
            "HistoricalVolumePairList: received %d pairs from upstream. "
            "BTC/USDC:USDC present: %s, ETH/USDC:USDC present: %s",
            len(pairlist), btc_in, eth_in,
        )

        cached = self._pair_cache.get("pairlist")
        if cached is not None:
            pairset = set(pairlist)
            result = [p for p in cached if p in pairset]
            logger.info(
                "HistoricalVolumePairList [live/cached]: %d in -> %d out. Top 5: %s",
                len(pairlist), len(result),
                [p.split('/')[0] for p in result[:5]],
            )
            return result

        logger.info(
            "HistoricalVolumePairList [live]: fetching Binance futures tickers "
            "(source: public API, no credentials)..."
        )

        try:
            binance = self._get_binance()
            tickers = binance.fetch_tickers()
        except Exception as e:
            logger.warning(
                "HistoricalVolumePairList: Binance fetch FAILED: %s. "
                "FALLING BACK to unfiltered pairlist (%d pairs).", e, len(pairlist),
            )
            return pairlist  # Pass through on failure

        logger.info(
            "HistoricalVolumePairList [live]: fetched %d Binance tickers successfully.",
            len(tickers),
        )

        # Build volume map: Binance perpetual futures → GMX pair.
        # IMPORTANT: only match perpetuals (symbol ends with ":USDT"), NOT
        # quarterly/delivery contracts like "BTC/USDT:USDT-260327" which have
        # much lower volume and would overwrite the perpetual entry.
        volumes: dict[str, float] = {}
        for symbol, ticker in tickers.items():
            if not symbol.endswith('/USDT:USDT'):
                continue
            quote_vol = ticker.get('quoteVolume') or 0
            if quote_vol < self._min_value:
                continue
            base = symbol.split('/')[0]
            base = self.SOURCE_TO_GMX_TOKEN.get(base, base)
            gmx_pair = f"{base}/USDC:USDC"
            volumes[gmx_pair] = quote_vol

        # Trace BTC/ETH specifically
        btc_vol = volumes.get('BTC/USDC:USDC')
        eth_vol = volumes.get('ETH/USDC:USDC')
        logger.info(
            "HistoricalVolumePairList [live]: BTC/USDC:USDC in volumes: %s (vol=$%s), "
            "ETH/USDC:USDC in volumes: %s (vol=$%s)",
            btc_vol is not None, f"{btc_vol:,.0f}" if btc_vol else "N/A",
            eth_vol is not None, f"{eth_vol:,.0f}" if eth_vol else "N/A",
        )

        ranked = sorted(volumes, key=lambda p: volumes[p], reverse=True)
        ranked = ranked[:self._number_assets]

        self._pair_cache["pairlist"] = ranked.copy()

        pairset = set(pairlist)
        result = [p for p in ranked if p in pairset]
        not_on_gmx = [p.split('/')[0] for p in ranked if p not in pairset]

        logger.info(
            "HistoricalVolumePairList [live]: %d Binance pairs above min_value -> "
            "top %d ranked -> %d matched GMX whitelist.",
            len(volumes), len(ranked), len(result),
        )
        # Log every matched pair with its volume so we can verify the full ranking
        for i, p in enumerate(result, 1):
            token = p.split('/')[0]
            vol = volumes.get(p, 0)
            logger.info(
                "  VolRank #%d: %s  24h_vol=$%s",
                i, token, f"{vol:,.0f}",
            )
        if not_on_gmx:
            logger.info(
                "HistoricalVolumePairList [live]: %d ranked pairs NOT in GMX whitelist "
                "(excluded): %s",
                len(not_on_gmx), not_on_gmx[:10],
            )
        return result

    # ------------------------------------------------------------------
    # Backtest mode: feather files
    # ------------------------------------------------------------------

    @staticmethod
    def _source_token_to_gmx_pair(token: str) -> str:
        """Convert source venue token to GMX pair format.

        e.g. 'BTC' -> 'BTC/USDC:USDC', '1000BONK' -> 'BONK/USDC:USDC'
        """
        mapped = HistoricalVolumePairList.SOURCE_TO_GMX_TOKEN.get(token, token)
        return f"{mapped}/USDC:USDC"

    def _load_volume_data(self) -> None:
        """Load daily candle feather files and compute quoteVolume. Called once lazily."""
        if self._volume_data is not None:
            return

        data_dir = Path(self._data_source_dir) / "futures"
        glob_pattern = f"*{self._pair_suffix}-1d-futures.feather"
        split_token = f"{self._pair_suffix}-1d-"

        volume_series: dict[str, pd.Series] = {}

        for f in sorted(data_dir.glob(glob_pattern)):
            token = f.name.split(split_token)[0]
            gmx_pair = self._source_token_to_gmx_pair(token)

            df = pd.read_feather(f)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            # quoteVolume = volume (base) * close price
            df["quoteVolume"] = df["volume"] * df["close"]
            volume_series[gmx_pair] = df.set_index("date")["quoteVolume"]

        self._volume_data = pd.DataFrame(volume_series)

        logger.info(
            "HistoricalVolumePairList: loaded %d volume series from %s, "
            "date range %s to %s",
            len(volume_series), data_dir,
            self._volume_data.index.min(), self._volume_data.index.max(),
        )

    def _build_daily_rankings(self) -> None:
        """Pre-compute daily sorted pair lists. Called once, results cached."""
        if self._daily_rankings is not None:
            return

        self._load_volume_data()

        rolling_vol = self._volume_data.rolling(
            window=self._lookback_days, min_periods=1
        ).mean()

        self._daily_rankings = {}

        for date in rolling_vol.index:
            day_str = str(date.date())
            vol_row = rolling_vol.loc[date].dropna()

            # Filter by minimum quoteVolume
            if self._min_value > 0:
                vol_row = vol_row[vol_row >= self._min_value]

            # Sort descending, take top N
            sorted_pairs = list(
                vol_row.sort_values(ascending=False).head(self._number_assets).index
            )
            self._daily_rankings[day_str] = sorted_pairs

        logger.info(
            "HistoricalVolumePairList: built rankings for %d days, "
            "top_n=%d, lookback=%d, min_value=%s",
            len(self._daily_rankings), self._number_assets,
            self._lookback_days, self._min_value,
        )

    def _filter_backtest(self, pairlist: list[str]) -> list[str]:
        """Backtest mode: look up pre-computed daily rankings by date."""
        self._build_daily_rankings()

        current_time = getattr(self._pairlistmanager, '_current_time', None)
        if current_time is None:
            current_time = datetime.utcnow()

        day_str = str(current_time.date())

        # Find the closest available date
        ranked_pairs = self._daily_rankings.get(day_str)
        if ranked_pairs is None:
            available_dates = sorted(self._daily_rankings.keys())
            earlier = [d for d in available_dates if d <= day_str]
            if earlier:
                ranked_pairs = self._daily_rankings[earlier[-1]]
            else:
                return pairlist

        # Intersection: keep only pairs in the incoming pairlist, in volume sort order
        pairset = set(pairlist)
        result = [p for p in ranked_pairs if p in pairset]

        logger.info(
            "HistoricalVolumePairList [%s]: %d in -> %d out. Top 5: %s",
            day_str, len(pairlist), len(result),
            [p.split('/')[0] for p in result[:5]],
        )

        return result

    # ------------------------------------------------------------------
    # Pairlist interface
    # ------------------------------------------------------------------

    def filter_pairlist(self, pairlist: list[str], tickers: Tickers) -> list[str]:
        """
        Sort and filter pairlist by volume.

        Live: fetches 24h tickers from Binance futures.
        Backtest: looks up historical rolling volume from feather files.
        """
        if self._is_live():
            return self._fetch_live_ranking(pairlist)
        return self._filter_backtest(pairlist)
