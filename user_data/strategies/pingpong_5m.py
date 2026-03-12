"""A strategy to test all trading pairs on an exchange — 5-minute timeframe variant."""

import logging
from datetime import datetime, timedelta

from freqtrade.enums import RunMode
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame

logger = logging.getLogger(__name__)


class Pingpong5m(IStrategy):
    buy_params = {}
    sell_params = {}

    # 1. Strategy interface version
    INTERFACE_VERSION: int = 3

    # 2. Timeframe and minimal startup candles
    timeframe = "5m"
    startup_candle_count = 0

    # 3. ROI table and stoploss
    minimal_roi = {"5": -1}
    stoploss = -0.99

    # 4. Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = False

    # 5. Plot configuration
    plot_config = {
        "main_plot": {},
        "subplots": {},
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all necessary indicators."""
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Buy on every candle."""
        dataframe.loc[:, "enter_long"] = 1
        dataframe.loc[:, "buy"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals in dataframe — all exits handled by custom_exit."""
        dataframe.loc[:, "exit_long"] = 0
        dataframe.loc[:, "sell"] = 0
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
            [Trade.is_open.is_(True), Trade.pair == pair]
        ).first()
        if existing:
            logger.info(
                f"⛔ Skipping entry for {pair}: open trade exists (id={existing.id})."
            )
            return False

        current_time = datetime.now()
        logger.info(f"🎯 ENTRY SIGNAL: {pair} | Price: {rate:.4f} | Time: {current_time}")
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
        """
        Custom exit logic to sell exactly 5 minutes after entry (one 5m candle).
        This function is called for every open trade at every bot loop iteration.
        """
        time_diff = current_time - trade.open_date_utc
        time_diff_seconds = time_diff.total_seconds()

        profit_pct = current_profit * 100
        price_change = current_rate - trade.open_rate
        price_change_pct = (price_change / trade.open_rate) * 100

        if time_diff >= timedelta(minutes=5):
            logger.info(
                f"🚪 EXIT SIGNAL: {pair} | "
                f"Entry: {trade.open_rate:.4f} @ {trade.open_date_utc.strftime('%H:%M:%S')} | "
                f"Exit: {current_rate:.4f} @ {current_time.strftime('%H:%M:%S')} | "
                f"Duration: {int(time_diff_seconds)}s | "
                f"Price Change: {price_change:+.4f} ({price_change_pct:+.2f}%) | "
                f"Final P&L: {profit_pct:+.2f}%"
            )
            return "five_minute_exit"

        # Continue holding the position
        return None

    def lock_pair(
        self, pair: str, until: datetime, reason: str | None = None, side: str = "*"
    ) -> None:
        """Override to disable auto lock completely."""
        pass

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """Log bot loop start with open positions summary."""
        current_mode = self.config["runmode"]
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        if is_trading_mode:
            open_trades = Trade.get_open_trades()
            logger.info(
                f"🔄 BOT LOOP START: {current_time} | Open Trades: {len(open_trades)}"
            )
