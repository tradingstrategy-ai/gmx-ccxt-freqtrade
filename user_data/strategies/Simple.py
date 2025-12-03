import logging
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

logger = logging.getLogger(__name__)


class Simple(IStrategy):
    INTERFACE_VERSION = 3

    minimal_roi = {"0": 100}  # 10000% - never exit via ROI
    stoploss = -0.10
    timeframe = '1m'
    can_short = False
    process_only_new_candles = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Entry condition: RSI < 50 and RSI is not NaN
        conditions = (
            (dataframe['rsi'] < 50) &
            (dataframe['rsi'].notnull())
        )

        dataframe.loc[conditions, 'enter_long'] = 1

        # Debug: log how many entry signals we have
        entry_count = dataframe['enter_long'].sum()
        logger.info(f"Generated {entry_count} entry signals out of {len(dataframe)} candles")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] > 50),
            'exit_long'
        ] = 1

        return dataframe