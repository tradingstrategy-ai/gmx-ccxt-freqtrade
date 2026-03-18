"""
IchiV3_LS_Static_HighPar — High-parallelism variant with fixed-fraction base stake.

Inherits from IchiV3_LS_Static_WhaleCap. Overrides custom_stake_amount to use a
fixed percentage of total balance as base_stake instead of total_balance/max_open_trades.

This allows many concurrent positions (30-50) where:
- base_stake = total_balance × base_stake_pct (e.g., 7% = $7K on $100K)
- Mcap multipliers scale the intent (blue chips get more, degens get less)
- OI cap and pool liquidity cap reduce positions on small markets
- max_stake (free balance) prevents over-allocation when capital runs out
- Dust and slot filters skip positions not worth taking
"""

import logging
from datetime import datetime

import numpy as np

from freqtrade.strategy import DecimalParameter
from user_data.strategies.IchiV3_LS_Static_WhaleCap import IchiV3_LS_Static_WhaleCap


logger = logging.getLogger(__name__)


class IchiV3_LS_Static_HighPar(IchiV3_LS_Static_WhaleCap):
    """High-parallelism variant: fixed-fraction base stake, many concurrent positions."""

    # Base stake as % of total balance (replaces total_balance / max_open_trades)
    base_stake_pct = DecimalParameter(
        0.02, 0.20, default=0.07, decimals=2, space='buy', optimize=False
    )

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
        """
        Fixed-fraction base stake with OI/pool caps.

        Does NOT call super() — reimplements the full sizing pipeline with
        base_stake = total_balance × base_stake_pct instead of total/max_open_trades.
        Reuses parent helper methods for OI, pool liquidity, and mcap lookups.
        """
        if not self.USE_CUSTOM_STAKE:
            return proposed_stake

        # Step 1: base_stake from fixed fraction of total balance
        wallets = kwargs.get('wallets') or self.wallets
        if wallets:
            total_balance = wallets.get_total_stake_amount()
        else:
            total_balance = proposed_stake * 10

        base_stake = total_balance * float(self.base_stake_pct.value)

        # Step 2: Apply mcap multiplier
        market_cap = self._get_market_cap_value_at(pair, current_time)
        mcap_multiplier = self._get_market_cap_multiplier(market_cap)
        desired_stake = base_stake * mcap_multiplier

        # Step 3: Per-pair concentration cap
        per_pair_cap_pct = self.buy_params.get('per_pair_cap_pct', 0.20)
        desired_stake = min(desired_stake, per_pair_cap_pct * total_balance)

        # Step 4: OI cap
        oi_value = self._get_oi_for_pair(pair, current_time)
        if oi_value is not None and oi_value > 0:
            max_stake_oi = (oi_value * self.max_oi_share.value) / (leverage if leverage > 0 else 1)
            desired_stake = min(desired_stake, max_stake_oi)

        # Step 5: Pool liquidity cap
        pool_liq = self._get_pool_liquidity_for_pair(pair, current_time)
        if pool_liq is not None and pool_liq > 0:
            max_stake_liq = pool_liq * self.max_pool_share.value
            desired_stake = min(desired_stake, max_stake_liq)

        # Step 6: Dust filter — skip if caps squeezed below min_stake_ratio of intent
        mcap_stake = base_stake * mcap_multiplier
        oi_str = f"${oi_value:,.0f}" if oi_value else "N/A"
        liq_str = f"${pool_liq:,.0f}" if pool_liq else "N/A"

        if desired_stake < mcap_stake * self.min_stake_ratio.value:
            logger.info(
                f"DUST SKIP | {pair} | intent=${mcap_stake:,.0f} | "
                f"capped=${desired_stake:,.0f} | ratio={desired_stake/mcap_stake:.1%} "
                f"< min={self.min_stake_ratio.value:.0%} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )
            return 0

        # Step 7: Slot filter — skip if position not worth a trading slot
        if desired_stake < total_balance * self.min_position_pct.value:
            logger.info(
                f"SLOT SKIP | {pair} | stake=${desired_stake:,.0f} | "
                f"balance=${total_balance:,.0f} | pct={desired_stake/total_balance:.2%} "
                f"< min={self.min_position_pct.value:.1%} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )
            return 0

        # Step 8: Cap by available free capital
        # max_stake = min(exchange_max, wallets.get_available_stake_amount())
        desired_stake = min(desired_stake, max_stake)

        if max_stake <= 0:
            return 0

        if min_stake and desired_stake < min_stake:
            return 0

        if not isinstance(desired_stake, (int, float)) or desired_stake <= 0 or np.isnan(desired_stake):
            return 0

        if desired_stake < mcap_stake:
            logger.info(
                f"CAP | {pair} | intent=${mcap_stake:,.0f} -> ${desired_stake:,.0f} | "
                f"OI={oi_str} | pool_liq={liq_str}"
            )

        return float(desired_stake)
