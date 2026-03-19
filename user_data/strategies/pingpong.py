"""A strategy to test all trading pairs on an exchange.

Supports simultaneous long + short on the same pair via a module-level monkey-patch
of FreqtradeBot.enter_positions.  Freqtrade's default behaviour removes a pair from
the entry whitelist the moment *any* trade is open for it, which prevents opening
the opposite-side hedge.  The patch changes the rule to: only exclude a pair once
*both* long and short sides are open.
"""

import logging
from copy import deepcopy
from datetime import datetime, timedelta

from freqtrade.enums import RunMode, SignalDirection
from freqtrade.exceptions import DependencyException
from freqtrade.persistence import PairLocks, Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Monkey-patch FreqtradeBot.enter_positions
#
# Applied once at import time (before the bot starts).  Reverting is as simple
# as removing this block and restarting the bot.
# ---------------------------------------------------------------------------

def _patch_freqtradebot() -> None:
    try:
        import freqtrade.constants as _ft_constants
        from freqtrade.freqtradebot import FreqtradeBot

        _orig = FreqtradeBot.enter_positions

        def _hedging_enter_positions(self) -> int:
            """enter_positions patched to allow simultaneous long+short on same pair."""
            trades_created = 0
            whitelist = deepcopy(self.active_pair_whitelist)

            if not whitelist:
                self.log_once("Active pair whitelist is empty.", logging.getLogger("freqtrade.freqtradebot").info)
                return trades_created

            open_trades_list = Trade.get_open_trades()

            if self.strategy.can_short:
                # Only remove a pair when BOTH sides are already open.
                open_longs = {t.pair for t in open_trades_list if not t.is_short}
                open_shorts = {t.pair for t in open_trades_list if t.is_short}
                for pair in list(whitelist):
                    if pair in open_longs and pair in open_shorts:
                        whitelist.remove(pair)
                        logging.getLogger("freqtrade.freqtradebot").debug(
                            "Ignoring %s in pair whitelist (both sides open)", pair
                        )
            else:
                for trade in open_trades_list:
                    if trade.pair in whitelist:
                        whitelist.remove(trade.pair)
                        logging.getLogger("freqtrade.freqtradebot").debug(
                            "Ignoring %s in pair whitelist", trade.pair
                        )

            if not whitelist:
                self.log_once(
                    "No currency pair in active pair whitelist, but checking to exit open trades.",
                    logging.getLogger("freqtrade.freqtradebot").info,
                )
                return trades_created

            if PairLocks.is_global_lock(side="*"):
                lock = PairLocks.get_pair_longest_lock("*")
                _ft_log = logging.getLogger("freqtrade.freqtradebot")
                if lock:
                    self.log_once(
                        f"Global pairlock active until "
                        f"{lock.lock_end_time.strftime(_ft_constants.DATETIME_PRINT_FORMAT)}. "
                        f"Not creating new trades, reason: {lock.reason}.",
                        _ft_log.info,
                    )
                else:
                    self.log_once("Global pairlock active. Not creating new trades.", _ft_log.info)
                return trades_created

            for pair in whitelist:
                try:
                    with self._exit_lock:
                        trades_created += self.create_trade(pair)
                except DependencyException as exception:
                    logging.getLogger("freqtrade.freqtradebot").warning(
                        "Unable to create trade for %s: %s", pair, exception
                    )

            if not trades_created:
                logging.getLogger("freqtrade.freqtradebot").debug(
                    "Found no enter signals for whitelisted currencies. Trying again..."
                )

            return trades_created

        FreqtradeBot.enter_positions = _hedging_enter_positions
        logger.info("Pingpong: patched FreqtradeBot.enter_positions for simultaneous long/short")

    except Exception as e:
        logger.warning("Pingpong: could not patch FreqtradeBot.enter_positions: %s", e)


_patch_freqtradebot()


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class Pingpong(IStrategy):
    buy_params = {}
    sell_params = {}

    # 1. Strategy interface version
    INTERFACE_VERSION: int = 3

    # 2. Timeframe and minimal startup candles
    timeframe = "1m"
    startup_candle_count = 0

    # 3. ROI table and stoploss
    minimal_roi = {"1": -1}
    stoploss = -0.99

    # 4. Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = False

    # 5. Allow both long and short positions simultaneously
    can_short = True

    # 6. Plot configuration
    plot_config = {"main_plot": {}, "subplots": {}}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Signal always present so Freqtrade's dataframe validator passes.
        # Actual direction is decided in get_entry_signal() based on open trades.
        dataframe.loc[:, "enter_long"] = 1
        dataframe.loc[:, "enter_short"] = 0
        return dataframe

    def get_entry_signal(
        self,
        pair: str,
        timeframe: str,
        dataframe: DataFrame,
    ) -> tuple[SignalDirection | None, str | None]:
        # In backtest/plot use the dataframe signal normally.
        if self.dp.runmode.value in ("backtest", "plot", "hyperopt"):
            return super().get_entry_signal(pair, timeframe, dataframe)

        # In live/dry-run: decide direction based on what's already open for this pair.
        long_open = Trade.get_trades(
            [Trade.is_open.is_(True), Trade.pair == pair, Trade.is_short.is_(False)]
        ).first()
        short_open = Trade.get_trades(
            [Trade.is_open.is_(True), Trade.pair == pair, Trade.is_short.is_(True)]
        ).first()

        if long_open and short_open:
            return None, None  # Both sides already open
        elif long_open:
            return SignalDirection.SHORT, None  # Long exists — open the short hedge
        else:
            return SignalDirection.LONG, None  # Nothing open or only short — enter long

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals — all exits handled by custom_exit."""
        dataframe.loc[:, "exit_long"] = 0
        dataframe.loc[:, "exit_short"] = 0
        return dataframe

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
            [Trade.is_open.is_(True), Trade.pair == pair, Trade.is_short.is_(side == "short")]
        ).first()
        if existing:
            logger.info(
                "⛔ Skipping %s entry for %s: open %s trade exists (id=%s).",
                side, pair, side, existing.id,
            )
            return False

        logger.info("🎯 ENTRY SIGNAL: %s | Price: %.4f | Time: %s", pair, rate, datetime.now())
        return True

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        """Exit exactly 1 minute after entry."""
        time_diff = current_time - trade.open_date_utc
        if time_diff >= timedelta(minutes=1):
            price_change = current_rate - trade.open_rate
            price_change_pct = (price_change / trade.open_rate) * 100
            logger.info(
                "🚪 EXIT SIGNAL: %s | Entry: %.4f @ %s | Exit: %.4f @ %s | "
                "Duration: %ds | Price Change: %+.4f (%+.2f%%) | Final P&L: %+.2f%%",
                pair,
                trade.open_rate,
                trade.open_date_utc.strftime("%H:%M:%S"),
                current_rate,
                current_time.strftime("%H:%M:%S"),
                int(time_diff.total_seconds()),
                price_change,
                price_change_pct,
                current_profit * 100,
            )
            return "one_minute_exit"
        return None

    def lock_pair(
        self, pair: str, until: datetime, reason: str | None = None, side: str = "*"
    ) -> None:
        """Disabled — auto-locking would block the hedge entry."""
        pass

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        if self.config["runmode"] in (RunMode.LIVE, RunMode.DRY_RUN):
            open_trades = Trade.get_open_trades()
            logger.info(
                "🔄 BOT LOOP START: %s | Open Trades: %d", current_time, len(open_trades)
            )
