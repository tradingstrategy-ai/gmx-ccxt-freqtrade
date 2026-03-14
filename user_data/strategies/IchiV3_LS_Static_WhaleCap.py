"""
IchiV3_LS_Static_WhaleCap — IchiV3_LS_Static with percentage-based position caps.

Inherits all logic from IchiV3_LS_Static (including market cap sizing). Adds:
- OI cap: limits position to max_oi_share % of pair's total open interest
- Pool liquidity cap: limits position to max_pool_share % of pool liquidity
- Dust filter: skips trade if caps reduce stake below min_stake_ratio % of
  what strategy sizing wanted (scales with account size, no fixed thresholds)
- Protections: CooldownPeriod, StoplossGuard, LowProfitPairs, MaxDrawdown
- Hot pair cooldown: pauses pairs that have been too profitable recently

All caps and protections are percentage-based and adaptive to market conditions.

In live/dry_run mode, OI and pool liquidity are fetched from the GMX exchange
via CCXT (on-chain data). In backtest mode, static feather files are used.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from freqtrade.enums import RunMode
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter
from user_data.strategies.IchiV3_LS_Static import IchiV3_LS_Static


logger = logging.getLogger(__name__)


class IchiV3_LS_Static_WhaleCap(IchiV3_LS_Static):
    """IchiV3_LS_Static with percentage-based position caps (OI + pool liquidity)."""

    # Max share of pair's total OI
    max_oi_share = DecimalParameter(
        0.005, 0.10, default=0.025, decimals=3, space='buy', optimize=False
    )
    # Max share of pool liquidity
    max_pool_share = DecimalParameter(
        0.01, 0.10, default=0.02, decimals=3, space='buy', optimize=False
    )
    # Skip trade if caps reduce stake below this fraction of proposed stake
    min_stake_ratio = DecimalParameter(
        0.01, 0.20, default=0.10, decimals=3, space='buy', optimize=False
    )
    # Skip trade if final stake is below this fraction of total balance (slot not worth it)
    min_position_pct = DecimalParameter(
        0.001, 0.05, default=0.01, decimals=3, space='buy', optimize=False
    )

    # ------------------------------------------------------------------
    # Hot pair cooldown — pause pairs running too hot (mean-reversion)
    # ------------------------------------------------------------------
    hot_pair_lookback_candles = IntParameter(
        12, 96, default=48, space='protection', optimize=True,
    )
    hot_pair_profit_threshold = DecimalParameter(
        0.02, 0.15, default=0.06, decimals=2, space='protection', optimize=True,
    )
    hot_pair_cooldown_candles = IntParameter(
        6, 48, default=24, space='protection', optimize=True,
    )
    hot_pair_trade_limit = IntParameter(
        1, 5, default=2, space='protection', optimize=True,
    )

    # ------------------------------------------------------------------
    # Built-in protections
    # ------------------------------------------------------------------
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": True,
                "only_per_side": True,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 24,
                "required_profit": -0.02,
                "only_per_pair": True,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 4,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.15,
            },
        ]

    # Cache TTL for live OI/pool data (seconds)
    _LIVE_CACHE_TTL = 300  # 5 minutes

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Backtest data (feather files)
        self._oi_data: pd.DataFrame | None = None
        self._pool_liq_data: pd.DataFrame | None = None
        # Live data cache: {pair: (timestamp, value)}
        self._live_oi_cache: dict[str, tuple[float, float]] = {}
        self._live_pool_liq_cache: dict[str, tuple[float, float]] = {}

    @property
    def _is_trading_mode(self) -> bool:
        return self.config.get('runmode') in (RunMode.LIVE, RunMode.DRY_RUN)

    # ------------------------------------------------------------------
    # Live OI fetching (from GMX exchange via CCXT)
    # ------------------------------------------------------------------

    def _get_live_oi(self, pair: str) -> float | None:
        """Fetch current OI from GMX exchange, with TTL cache."""
        now = time.monotonic()
        cached = self._live_oi_cache.get(pair)
        if cached and (now - cached[0]) < self._LIVE_CACHE_TTL:
            return cached[1]

        try:
            ccxt_api = self.dp._exchange._api
            oi_data = ccxt_api.fetch_open_interest(pair)
            oi_value = oi_data.get("openInterestValue")
            if oi_value is not None:
                oi_value = float(oi_value)
                self._live_oi_cache[pair] = (now, oi_value)
                return oi_value
        except Exception as e:
            logger.warning(f"WhaleCap: failed to fetch live OI for {pair}: {e}")

        return cached[1] if cached else None

    def _get_live_pool_liquidity(self, pair: str) -> float | None:
        """Fetch pool liquidity from GMX market data, with TTL cache."""
        now = time.monotonic()
        cached = self._live_pool_liq_cache.get(pair)
        if cached and (now - cached[0]) < self._LIVE_CACHE_TTL:
            return cached[1]

        try:
            market = self.dp.market(pair)
            if market and "info" in market:
                info = market["info"]
                long_liq = float(info.get("available_liquidity_long", 0) or 0)
                short_liq = float(info.get("available_liquidity_short", 0) or 0)
                pool_liq = long_liq + short_liq
                if pool_liq > 0:
                    self._live_pool_liq_cache[pair] = (now, pool_liq)
                    return pool_liq
        except Exception as e:
            logger.warning(f"WhaleCap: failed to fetch live pool liquidity for {pair}: {e}")

        return cached[1] if cached else None

    # ------------------------------------------------------------------
    # Backtest OI data loading (feather files, lazy)
    # ------------------------------------------------------------------

    @staticmethod
    def _file_token_to_pair(token: str) -> str:
        """Convert 'BTC' -> 'BTC/USDC:USDC'."""
        return f"{token}/USDC:USDC"

    def _load_oi_data(self) -> None:
        """Load daily OI feather files from futures_metrics/."""
        if self._oi_data is not None:
            return

        datadir = Path(self.config.get("datadir", "user_data/data/gmx"))
        futures_dir = datadir / "futures_metrics"

        oi_series: dict[str, pd.Series] = {}

        for f in sorted(futures_dir.glob("*_USDC_USDC-1d-open_interest.feather")):
            token = f.name.split("_USDC_USDC-1d-")[0]
            pair = self._file_token_to_pair(token)
            df = pd.read_feather(f)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            oi_series[pair] = df.set_index("date")["close"]

        self._oi_data = pd.DataFrame(oi_series)

        logger.info(
            f"WhaleCap: loaded {len(oi_series)} OI series, "
            f"date range {self._oi_data.index.min()} to {self._oi_data.index.max()}"
        )

    def _get_backtest_oi(self, pair: str, current_time: datetime) -> float | None:
        """Look up most recent OI value for a pair as of current_time (backtest)."""
        self._load_oi_data()

        if self._oi_data is None or pair not in self._oi_data.columns:
            return None

        target_date = pd.Timestamp(current_time).normalize().tz_localize(None)
        pair_oi = self._oi_data[pair].dropna()
        valid = pair_oi[pair_oi.index <= target_date]

        if valid.empty:
            return None

        return float(valid.iloc[-1])

    # ------------------------------------------------------------------
    # Backtest pool liquidity data loading (feather files, lazy)
    # ------------------------------------------------------------------

    def _load_pool_liq_data(self) -> None:
        """Load daily pool liquidity feather files from futures_metrics/."""
        if self._pool_liq_data is not None:
            return

        datadir = Path(self.config.get("datadir", "user_data/data/gmx"))
        futures_dir = datadir / "futures_metrics"

        liq_series: dict[str, pd.Series] = {}

        for f in sorted(futures_dir.glob("*_USDC_USDC-1d-pool_liquidity.feather")):
            token = f.name.split("_USDC_USDC-1d-")[0]
            pair = self._file_token_to_pair(token)
            df = pd.read_feather(f)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            liq_series[pair] = df.set_index("date")["close"]

        self._pool_liq_data = pd.DataFrame(liq_series)

        logger.info(
            f"PoolCap: loaded {len(liq_series)} liquidity series, "
            f"date range {self._pool_liq_data.index.min()} to {self._pool_liq_data.index.max()}"
        )

    def _get_backtest_pool_liquidity(self, pair: str, current_time: datetime) -> float | None:
        """Look up most recent pool liquidity value for a pair as of current_time (backtest)."""
        self._load_pool_liq_data()

        if self._pool_liq_data is None or pair not in self._pool_liq_data.columns:
            return None

        target_date = pd.Timestamp(current_time).normalize().tz_localize(None)
        pair_liq = self._pool_liq_data[pair].dropna()
        valid = pair_liq[pair_liq.index <= target_date]

        if valid.empty:
            return None

        return float(valid.iloc[-1])

    # ------------------------------------------------------------------
    # Unified OI / pool liquidity accessors (auto-select live vs backtest)
    # ------------------------------------------------------------------

    def _get_oi_for_pair(self, pair: str, current_time: datetime) -> float | None:
        if self._is_trading_mode:
            return self._get_live_oi(pair)
        return self._get_backtest_oi(pair, current_time)

    def _get_pool_liquidity_for_pair(self, pair: str, current_time: datetime) -> float | None:
        if self._is_trading_mode:
            return self._get_live_pool_liquidity(pair)
        return self._get_backtest_pool_liquidity(pair, current_time)

    # ------------------------------------------------------------------
    # Position sizing — market cap sizing THEN percentage-based caps
    # ------------------------------------------------------------------

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """Apply market cap sizing, then cap by OI and pool liquidity."""
        # Step 1: Get market cap-sized stake from parent
        mcap_stake = super().custom_stake_amount(
            pair=pair,
            current_time=current_time,
            current_rate=current_rate,
            proposed_stake=proposed_stake,
            min_stake=min_stake,
            max_stake=max_stake,
            leverage=leverage,
            entry_tag=entry_tag,
            side=side,
            **kwargs,
        )

        if mcap_stake <= 0:
            return mcap_stake

        final_stake = mcap_stake

        # Step 2: Apply OI cap
        oi_value = self._get_oi_for_pair(pair, current_time)
        if oi_value is not None and oi_value > 0:
            max_stake_oi = (oi_value * self.max_oi_share.value) / (leverage if leverage > 0 else 1)
            final_stake = min(final_stake, max_stake_oi)

        # Step 3: Apply pool liquidity cap
        pool_liq = self._get_pool_liquidity_for_pair(pair, current_time)
        if pool_liq is not None and pool_liq > 0:
            max_stake_liq = pool_liq * self.max_pool_share.value
            final_stake = min(final_stake, max_stake_liq)

        # Step 4: Skip dust trades (percentage-based)
        oi_str = f"${oi_value:,.0f}" if oi_value else "N/A"
        liq_str = f"${pool_liq:,.0f}" if pool_liq else "N/A"

        if final_stake < mcap_stake * self.min_stake_ratio.value:
            logger.info(
                f"DUST SKIP | {pair} | mcap_stake=${mcap_stake:,.0f} | "
                f"capped=${final_stake:,.0f} | ratio={final_stake/mcap_stake:.1%} "
                f"< min={self.min_stake_ratio.value:.0%} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )
            return 0

        # Skip if position too small relative to portfolio (not worth a slot)
        total_balance = self.wallets.get_total('USDC') if self.wallets else proposed_stake * 10
        if final_stake < total_balance * self.min_position_pct.value:
            logger.info(
                f"SLOT SKIP | {pair} | stake=${final_stake:,.0f} | "
                f"balance=${total_balance:,.0f} | pct={final_stake/total_balance:.2%} "
                f"< min={self.min_position_pct.value:.1%} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )
            return 0

        if final_stake < mcap_stake:
            logger.info(
                f"CAP | {pair} | mcap_stake=${mcap_stake:,.0f} -> ${final_stake:,.0f} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )

        return final_stake

    # ------------------------------------------------------------------
    # Hot pair cooldown — reject entries on overperforming pairs
    # ------------------------------------------------------------------

    def confirm_trade_entry(
        self, pair: str, order_type: str, amount: float, rate: float,
        time_in_force: str, current_time: datetime, entry_tag: str | None,
        side: str, **kwargs,
    ) -> bool:
        # Run parent checks first (ATR storage, mcap logging)
        if not super().confirm_trade_entry(
            pair, order_type, amount, rate,
            time_in_force, current_time, entry_tag, side, **kwargs,
        ):
            return False

        # Hot pair cooldown: pause pairs that have been too profitable recently
        lookback_start = current_time - timedelta(
            hours=int(self.hot_pair_lookback_candles.value)
        )
        recent_trades = Trade.get_trades_proxy(
            pair=pair, is_open=False, close_date=lookback_start,
        )

        if len(recent_trades) >= int(self.hot_pair_trade_limit.value):
            cumulative_profit = sum(t.profit_ratio for t in recent_trades)
            if cumulative_profit >= float(self.hot_pair_profit_threshold.value):
                cooldown_until = current_time + timedelta(
                    hours=int(self.hot_pair_cooldown_candles.value)
                )
                lock_side = side if self.config.get('trading_mode') == 'futures' else '*'
                self.lock_pair(
                    pair=pair,
                    until=cooldown_until,
                    reason=(
                        f"Hot pair cooldown: {cumulative_profit:.1%} profit "
                        f"in {len(recent_trades)} trades"
                    ),
                    side=lock_side,
                )
                logger.info(
                    f"HOT PAIR LOCK | {pair} | {side} | "
                    f"profit={cumulative_profit:.1%} in {len(recent_trades)} trades | "
                    f"locked until {cooldown_until}"
                )
                return False

        return True
