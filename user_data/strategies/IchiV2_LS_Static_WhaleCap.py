"""
IchiV2_LS_Static_WhaleCap — IchiV2_LS_Static with percentage-based position caps.

Inherits all logic from IchiV2_LS_Static. Adds:
- OI cap: limits position to max_oi_share % of pair's total open interest
- Pool liquidity cap: limits position to max_pool_share % of pool liquidity
- Dust filter: skips trade if caps reduce stake below min_stake_ratio % of
  what strategy sizing wanted (scales with account size, no fixed thresholds)

All three caps are percentage-based and adaptive to market conditions.

Live mode: reads OI and pool liquidity from exchange market data (refreshed
by Freqtrade's reload_markets cycle).
Backtest mode: reads pre-downloaded feather files from datadir/futures_metrics/.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from freqtrade.enums import RunMode
from freqtrade.strategy import DecimalParameter
from user_data.strategies.IchiV2_LS_Static import IchiV2_LS_Static


logger = logging.getLogger(__name__)


class IchiV2_LS_Static_WhaleCap(IchiV2_LS_Static):
    """IchiV2_LS_Static with percentage-based position caps (OI + pool liquidity)."""

    # Max share of pair's total OI
    max_oi_share = DecimalParameter(
        0.005, 0.10, default=0.025, decimals=3, space='buy', optimize=False
    )
    # Max share of pool liquidity
    max_pool_share = DecimalParameter(
        0.01, 0.10, default=0.04, decimals=3, space='buy', optimize=False
    )
    # Skip trade if caps reduce stake below this fraction of proposed stake
    min_stake_ratio = DecimalParameter(
        0.01, 0.20, default=0.10, decimals=3, space='buy', optimize=False
    )
    # Skip trade if final stake is below this fraction of total balance (slot not worth it)
    min_position_pct = DecimalParameter(
        0.001, 0.05, default=0.01, decimals=3, space='buy', optimize=False
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._oi_data: pd.DataFrame | None = None
        self._pool_liq_data: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    def _is_live(self) -> bool:
        """True when running in live or dry-run mode (not backtesting)."""
        try:
            return self.dp and self.dp.runmode in (RunMode.LIVE, RunMode.DRY_RUN)
        except Exception:
            return False

    def _get_market_info(self, pair: str) -> dict:
        """Get market info dict from exchange (live data from load_markets)."""
        try:
            market = self.dp.market(pair)
            return market.get('info', {}) if market else {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # OI data
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
            "WhaleCap: loaded %d OI series, date range %s to %s",
            len(oi_series),
            self._oi_data.index.min(), self._oi_data.index.max(),
        )

    def _get_oi_for_pair(self, pair: str, current_time: datetime) -> float | None:
        """Get total OI for a pair. Live: exchange market info. Backtest: feather files."""
        if self._is_live():
            info = self._get_market_info(pair)
            oi_long = info.get('open_interest_long')
            oi_short = info.get('open_interest_short')
            if oi_long is not None and oi_short is not None:
                try:
                    return float(oi_long) + float(oi_short)
                except (ValueError, TypeError):
                    pass
            return None

        # Backtest: use feather files
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
    # Pool liquidity data
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
            "PoolCap: loaded %d liquidity series, date range %s to %s",
            len(liq_series),
            self._pool_liq_data.index.min(), self._pool_liq_data.index.max(),
        )

    def _get_pool_liquidity_for_pair(self, pair: str, current_time: datetime) -> float | None:
        """Get pool liquidity for a pair. Live: exchange data. Backtest: feather files."""
        if self._is_live():
            info = self._get_market_info(pair)
            # Primary: available liquidity from GMX REST API
            liq_long = info.get('available_liquidity_long')
            liq_short = info.get('available_liquidity_short')
            if liq_long is not None and liq_short is not None:
                try:
                    return float(liq_long) + float(liq_short)
                except (ValueError, TypeError):
                    pass
            # Fallback: pool amounts
            pool_long = info.get('pool_amount_long')
            pool_short = info.get('pool_amount_short')
            if pool_long is not None and pool_short is not None:
                try:
                    return float(pool_long) + float(pool_short)
                except (ValueError, TypeError):
                    pass
            return None

        # Backtest: use feather files
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
    # Position sizing — percentage-based caps
    # ------------------------------------------------------------------

    def custom_stake_amount(
        self,
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
        """Cap position size by OI and pool liquidity percentages."""
        pair = kwargs.get("pair", "")
        if not pair:
            return proposed_stake

        final_stake = proposed_stake

        # Step 1: Apply OI cap
        oi_value = self._get_oi_for_pair(pair, current_time)
        if oi_value is not None and oi_value > 0:
            max_stake_oi = (oi_value * self.max_oi_share.value) / (leverage if leverage > 0 else 1)
            final_stake = min(final_stake, max_stake_oi)

        # Step 2: Apply pool liquidity cap
        pool_liq = self._get_pool_liquidity_for_pair(pair, current_time)
        if pool_liq is not None and pool_liq > 0:
            max_stake_liq = pool_liq * self.max_pool_share.value
            final_stake = min(final_stake, max_stake_liq)

        # Step 3: Skip dust trades (percentage-based)
        oi_str = f"${oi_value:,.0f}" if oi_value else "N/A"
        liq_str = f"${pool_liq:,.0f}" if pool_liq else "N/A"

        if final_stake < proposed_stake * self.min_stake_ratio.value:
            logger.info(
                f"DUST SKIP | {pair} | proposed=${proposed_stake:,.0f} | "
                f"capped=${final_stake:,.0f} | ratio={final_stake/proposed_stake:.1%} "
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

        if final_stake < proposed_stake:
            logger.info(
                f"CAP | {pair} | proposed=${proposed_stake:,.0f} -> ${final_stake:,.0f} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )

        return final_stake
