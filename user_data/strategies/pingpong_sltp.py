"""Pingpong strategy variation to test freqtrade stop-loss / take-profit cancel orders on GMX.

Test goal: verify that when a trade exits via take-profit (or time fallback),
freqtrade's cancel_order() call to GMX/CCXT correctly cancels the pending
unfilled stop-loss exchange order.

Also tests the SL *move* flow (cancel-old + place-new), triggered by custom_stoploss:

Flow:
  1. Enter long via market order on every candle (one trade per pair).
  2. freqtrade places an initial stop-loss order on GMX exchange at stoploss=-0.05
     (stoploss_on_exchange=true must be set in the config).
  3. After SL_MOVE_AFTER_SECS seconds custom_stoploss tightens the SL to SL_TIGHT.
     freqtrade detects the change, cancels the old SL order on GMX (cancel tested here)
     and places a new tighter SL order (create tested here).
  4. custom_exit() polls each bot loop:
       - TP hit (profit >= +1%)   → return "take_profit_1pct"
       - Time fallback (>= 60 min) → return "time_exit_60min"
  5. On any custom_exit trigger, freqtrade places a market exit order AND
     calls exchange.cancel_order(stoploss_order_id) — cancel tested again here.
  6. If SL fires first, GMX fills the stop order and freqtrade detects the fill.
"""

import logging
from datetime import datetime, timedelta

from freqtrade.enums import RunMode
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame

logger = logging.getLogger(__name__)


class PingpongSLTP(IStrategy):
    """Pingpong SL/TP variant for testing cancel-order and SL-move flows on GMX."""

    buy_params = {}
    sell_params = {}

    INTERFACE_VERSION: int = 3

    can_short: bool = False

    timeframe = "5m"
    startup_candle_count = 0

    # Initial wide stop-loss — freqtrade places this as an exchange order on GMX
    # immediately after trade open (stoploss_on_exchange: true must be set in config).
    stoploss = -0.05

    # After SL_MOVE_AFTER_SECS, custom_stoploss tightens the SL to SL_TIGHT.
    # freqtrade detects the change and does: cancel old SL order → place new SL order.
    # Set SL_MOVE_AFTER_SECS = 0 to disable the SL-move test.
    SL_MOVE_AFTER_SECS: int = 90
    SL_TIGHT: float = -0.02  # tighter stop used after the move

    use_custom_stoploss = True

    # ROI disabled — exits managed entirely by custom_exit and the exchange SL
    minimal_roi = {"0": 100}

    trailing_stop = False

    plot_config = {
        "main_plot": {},
        "subplots": {},
    }

    # ------------------------------------------------------------------ #
    # Indicators                                                           #
    # ------------------------------------------------------------------ #

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No indicators required."""
        return dataframe

    # ------------------------------------------------------------------ #
    # Entry / exit signal population                                       #
    # ------------------------------------------------------------------ #

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter long on every candle."""
        dataframe.loc[:, "enter_long"] = 1
        dataframe.loc[:, "buy"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No dataframe exit signals — all exits handled by custom_exit."""
        dataframe.loc[:, "exit_long"] = 0
        dataframe.loc[:, "sell"] = 0
        return dataframe

    # ------------------------------------------------------------------ #
    # Trade entry confirmation                                             #
    # ------------------------------------------------------------------ #

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        side: str,
        **kwargs,
    ) -> bool:
        if self.dp.runmode.value in ("backtest", "plot"):
            return True

        existing = Trade.get_trades(
            [Trade.is_open.is_(True), Trade.pair == pair]
        ).first()
        if existing:
            logger.info(
                f"⛔ Skipping entry for {pair}: open trade exists (id={existing.id})."
            )
            return False

        current_time = datetime.now()
        logger.info(
            f"🎯 ENTRY SIGNAL (long): {pair} | Price: {rate:.4f} | Time: {current_time} | "
            f"SL will be placed on exchange at ~{rate * (1 + self.stoploss):.4f} "
            f"({abs(self.stoploss) * 100:.0f}% below entry)"
        )
        return True

    # ------------------------------------------------------------------ #
    # Custom stop-loss — move SL to test cancel + re-place flow          #
    # ------------------------------------------------------------------ #

    def custom_stoploss(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        Tighten the stop-loss after SL_MOVE_AFTER_SECS to trigger freqtrade's
        cancel-old-SL → place-new-SL flow on GMX.

        :returns:
          - ``SL_TIGHT`` (e.g. -0.02) once the timer fires → freqtrade cancels the
            initial exchange SL order and places a new tighter one.
          - ``stoploss`` (-0.05) before the timer → no change, freqtrade keeps
            the initial exchange SL unchanged.
        """
        if self.SL_MOVE_AFTER_SECS == 0:
            return self.stoploss

        elapsed = (current_time - trade.open_date_utc).total_seconds()

        if elapsed >= self.SL_MOVE_AFTER_SECS:
            if current_profit > self.SL_TIGHT:
                # Only move if current price is above the new tight SL level —
                # otherwise the new SL would be immediately triggered.
                logger.info(
                    "SL MOVE triggered for %s: %.0fs elapsed, tightening from %.0f%% to %.0f%% | "
                    "freqtrade will cancel old SL order and place new one on GMX",
                    pair,
                    elapsed,
                    self.stoploss * 100,
                    self.SL_TIGHT * 100,
                )
                return self.SL_TIGHT

        return self.stoploss

    # ------------------------------------------------------------------ #
    # Custom exit — take-profit and time fallback                         #
    # ------------------------------------------------------------------ #

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        """
        :returns:
          - ``"take_profit_1pct"``  when profit >= +1 %  → freqtrade exits + cancels SL order
          - ``"time_exit_60min"``   when trade is >= 60 min old (12 × 5m candle fallback)
          - ``None``                to keep holding
        """
        profit_pct = current_profit * 100
        time_elapsed = current_time - trade.open_date_utc
        elapsed_secs = time_elapsed.total_seconds()

        # Warn when within 1% of the 5% stop-loss
        if -0.04 <= current_profit < 0.0:
            logger.warning(
                f"⚠️  APPROACHING SL: {pair} | Profit: {profit_pct:+.3f}% | "
                f"SL at {self.stoploss * 100:.1f}% | Elapsed: {int(elapsed_secs)}s"
            )
        else:
            logger.info(
                f"📊 HOLDING: {pair} | Entry: {trade.open_rate:.4f} | "
                f"Current: {current_rate:.4f} | Profit: {profit_pct:+.3f}% | "
                f"Elapsed: {int(elapsed_secs)}s"
            )

        # --- Take-profit check ---
        if current_profit >= 0.01:
            logger.info(
                f"✅ TAKE PROFIT HIT: {pair} | "
                f"Entry: {trade.open_rate:.4f} | Exit: {current_rate:.4f} | "
                f"Profit: {profit_pct:+.3f}% | Elapsed: {int(elapsed_secs)}s | "
                f"freqtrade will now cancel pending SL exchange order."
            )
            return "take_profit_1pct"

        # --- Time fallback check (60 minutes — 4 × 15m candles) ---
        if time_elapsed >= timedelta(minutes=60):
            logger.info(
                f"⏰ TIME EXIT (60 min): {pair} | "
                f"Entry: {trade.open_rate:.4f} | Exit: {current_rate:.4f} | "
                f"Profit: {profit_pct:+.3f}% | Elapsed: {int(elapsed_secs)}s | "
                f"freqtrade will now cancel pending SL exchange order."
            )
            return "time_exit_60min"

        return None

    # ------------------------------------------------------------------ #
    # Pair locking                                                         #
    # ------------------------------------------------------------------ #

    def lock_pair(
        self, pair: str, until: datetime, reason: str | None = None, side: str = "*"
    ) -> None:
        """Disable auto pair locking."""
        pass

    # ------------------------------------------------------------------ #
    # Bot loop logging                                                     #
    # ------------------------------------------------------------------ #

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """Log open positions summary each bot loop."""
        current_mode = self.config["runmode"]
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        if is_trading_mode:
            open_trades = Trade.get_open_trades()
            logger.info(
                f"🔄 BOT LOOP: {current_time} | Open Trades: {len(open_trades)}"
            )
            for t in open_trades:
                logger.info(
                    f"   └─ {t.pair} | Entry: {t.open_rate:.4f} | "
                    f"Open since: {t.open_date_utc} | "
                    f"Has SL on exchange: {t.has_open_sl_orders}"
                )
