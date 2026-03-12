# IchiV2_LS_Optimised - Dual Long/Short Ichimoku Strategy (Hyperopt-Optimised)
# Based on: IchiV2_LS_Backtest.py
# Description: Uses hyperopt-optimised parameters from 100-epoch SharpeHyperOptLossDaily run
#              on 28 chainlink token pairs (all available data).

from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
pd.options.mode.chained_assignment = None
import technical.indicators as ftt
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime
from freqtrade.persistence import Trade
from freqtrade.strategy import informative, DecimalParameter, IntParameter
from freqtrade.strategy.strategy_helper import stoploss_from_absolute
from freqtrade.exchange import timeframe_to_prev_date
import logging


class IchiV2_LS_Optimised(IStrategy):
    """
    IchiV2_LS_Optimised - hyperopt-optimised version of IchiV2_LS_Backtest.

    Dual long/short Ichimoku strategy on 1h timeframe.
    Parameters optimised via SharpeHyperOptLossDaily on 28 chainlink pairs.

    Optimised results (100 epochs, 28 chainlink pairs, all available data):
    - 2522 trades, 679W/0D/1843L (26.9% win rate)
    - Avg profit 0.80%, total profit 496.45%
    - Avg duration 2 days 2:57
    - Objective: -1.65660

    Key optimisation findings:
    - Wider lookback window (65 vs 24) for short entries
    - Much tighter ATR stop (1.5x vs 3.5x) for shorts
    - Shorter ATR period (13 vs 14) for more responsive stops
    - Faster velocity detection (10 vs 20 candle window)
    - Stricter RSI threshold (20 vs 25) for short exits

    Long entries (checked at 4h boundary):
    - 4h close crosses above senkou_a_4h
    - Cloud is green (senkou_a_4h > senkou_b_4h)
    - SAR is below close (sar_4h < close_4h)

    Long exits:
    - 1h close crosses below sar_4h (exit on SAR cross)
    - Cloud flip to bearish
    - Base stoploss at -0.129 as fallback

    Short entries (checked on any 1h candle):
    - Cloud is bearish (senkou_a < senkou_b)
    - Price retested senkou_b (high >= senkou_b) within 65-candle lookback
    - Current price breaks down below senkou_b

    Short exits:
    - RSI 4h oversold (< 20)
    - OR price velocity exhaustion (< -11%)
    - Cloud flip to bullish
    - ATR-based stop loss (1.5x ATR from entry, locked at entry)
    """

    INTERFACE_VERSION = 3
    can_short = True

    # Hyperopt-optimised parameters
    buy_params = {
        'retest_lookback_window': 65,
    }

    sell_params = {
        'atr_stop_multiplier': 1.5,
        'atr_timeperiod': 13,
        'price_velocity_window': 10,
        'rsi_tp_threshold': 20,
        'use_rsi_exit': 1,
        'velocity_tp_threshold': -0.11,
    }

    # Short entry parameters
    retest_lookback_window = IntParameter(4, 96, default=65, space='buy', optimize=False)

    # Short exit parameters
    rsi_tp_threshold = IntParameter(15, 35, default=20, space='sell', optimize=False)
    use_rsi_exit = IntParameter(0, 1, default=1, space='sell', optimize=False)

    # ATR stop loss for shorts
    atr_stop_multiplier = DecimalParameter(1.5, 4.0, default=1.5, decimals=1, space='sell', optimize=False)
    atr_timeperiod = IntParameter(2, 20, default=13, space='sell', optimize=False)

    # Price velocity window
    velocity_tp_threshold = DecimalParameter(-0.13, -0.06, default=-0.11, decimals=2, space='sell', optimize=False)
    price_velocity_window = IntParameter(4, 20, default=10, space='sell', optimize=False)

    custom_info = {}

    # ROI table - minimal
    minimal_roi = {
        "0": 10.0  # Disabled
    }

    # Stop loss
    stoploss = -0.129
    use_custom_stoploss = True

    # Timeframe
    timeframe = '1h'
    startup_candle_count = 121
    process_only_new_candles = True

    # Trailing stop - DISABLED
    trailing_stop = False
    trailing_stop_positive = None
    trailing_stop_positive_offset = None
    trailing_only_offset_is_reached = False

    # Exit settings
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    ICHI_PARAMS = dict(
        conversion_line_period=20,
        base_line_periods=60,
        laggin_span=120,
        displacement=1,
    )

    plot_config = {
        'main_plot': {
            'sar_4h': {'color': 'purple', 'marker': '.', 'linestyle': 'none'},
            'senkou_a_4h': {'color': 'lightgreen', 'linestyle': '--'},
            'senkou_b_4h': {'color': 'lightcoral', 'linestyle': '--'},
        },
        'subplots': {
            'RSI 4h': {
                'rsi_4h': {'color': 'purple'},
            },
            'Price Velocity': {
                'price_velocity': {'color': 'magenta'},
            },
        },
    }

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, after_fill: bool,
                       **kwargs) -> float | None:
        """
        Dynamic stoploss comparing base stoploss vs strategy-specific stops.

        :param pair: Trading pair.
        :param trade: Current trade object.
        :param current_time: Current datetime.
        :param current_rate: Current market rate.
        :param current_profit: Current profit ratio.
        :param after_fill: Whether this is called after a fill.
        :return: Stoploss value or None.

        LONGS: Compare base stoploss vs SAR level, choose the TIGHTER (higher) stop.
        SHORTS: Compare base stoploss vs ATR stop, choose the TIGHTER (lower) stop.
        """
        if not trade.is_short:
            # === LONG POSITIONS: Compare base stoploss vs SAR ===
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe.empty:
                return None

            try:
                last_candle = dataframe.iloc[-1]
                sar_level = last_candle.get('sar_4h')

                if pd.isna(sar_level):
                    return None

                entry_rate = trade.open_rate
                base_stop_price = entry_rate * (1 + self.stoploss)

                final_stop_price = max(base_stop_price, sar_level)

                return stoploss_from_absolute(
                    stop_rate=final_stop_price,
                    current_rate=current_rate,
                    is_short=False,
                    leverage=trade.leverage
                )

            except (KeyError, IndexError) as e:
                self.logger.warning(f"Error calculating SAR stoploss for {pair}: {e}")
                return None

        else:
            # === SHORT POSITIONS: Compare base stoploss vs ATR stop ===
            entry_atr = trade.get_custom_data(key='entry_atr')

            if entry_atr is None:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if not dataframe.empty:
                    try:
                        trade_candle_time = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
                        entry_candles = dataframe[dataframe['date'] <= trade_candle_time]
                        if not entry_candles.empty:
                            entry_atr = entry_candles.iloc[-1]['atr']
                            if not pd.isna(entry_atr):
                                trade.set_custom_data(key='entry_atr', value=float(entry_atr))
                    except (KeyError, IndexError) as e:
                        self.logger.warning(f"Failed to store entry ATR for {pair}: {e}")

            if entry_atr is None:
                return None

            entry_rate = trade.open_rate
            atr_distance = self.atr_stop_multiplier.value * float(entry_atr)

            atr_stop_price = entry_rate + atr_distance
            base_stop_price = entry_rate * (1 + abs(self.stoploss))

            final_stop_price = min(atr_stop_price, base_stop_price)

            return stoploss_from_absolute(
                stop_rate=final_stop_price,
                current_rate=current_rate,
                is_short=True,
                leverage=trade.leverage
            )

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> str | bool | None:
        """
        Exit logic - separate for longs vs shorts.

        :param pair: Trading pair.
        :param trade: Current trade object.
        :param current_time: Current datetime.
        :param current_rate: Current market rate.
        :param current_profit: Current profit ratio.
        :return: Exit reason string, or None.

        LONGS: SAR exit (1h close crosses below sar_4h), cloud flip to bearish.
        SHORTS: RSI 4h oversold, velocity exhaustion, cloud flip to bullish.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None

        try:
            last_row = dataframe.iloc[-1]
            last_close = last_row['close']
            last_sar = last_row.get('sar_4h')

            # LONG EXIT
            if not trade.is_short:
                # Cloud flip check
                cloud_flip = last_row['senkou_a_4h'] < last_row['senkou_b_4h']
                if cloud_flip:
                    return 'senkou_a_4h_exit_long'

                # SAR cross down
                sar_cross_down = not pd.isna(last_sar) and last_close <= last_sar
                if sar_cross_down:
                    return 'sar_exit_long'

            # SHORT EXIT
            if trade.is_short:
                # Cloud flip check
                cloud_flip = last_row['senkou_a_4h'] > last_row['senkou_b_4h']
                if cloud_flip:
                    return 'senkou_a_4h_exit_short'

                # RSI oversold
                last_rsi_4h = last_row.get('rsi_4h')
                rsi_oversold = False
                if self.use_rsi_exit.value == 1:
                    rsi_oversold = not pd.isna(last_rsi_4h) and last_rsi_4h < self.rsi_tp_threshold.value

                if rsi_oversold:
                    return 'tp_rsi_4h_oversold'

                # Velocity exhaustion
                last_velocity = last_row.get('price_velocity')
                velocity_exhausted = not pd.isna(last_velocity) and last_velocity < self.velocity_tp_threshold.value
                if velocity_exhausted:
                    return 'tp_velocity_achieved'

        except (KeyError, IndexError) as e:
            self.logger.warning(f"Error in custom_exit for {pair}: {e}")

        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str | None,
                           side: str, **kwargs) -> bool:
        """
        Store ATR at entry time for shorts.

        :param pair: Trading pair.
        :param order_type: Order type.
        :param amount: Trade amount.
        :param rate: Entry rate.
        :param time_in_force: Time in force.
        :param current_time: Current datetime.
        :param entry_tag: Entry tag.
        :param side: Trade side ('long' or 'short').
        :return: True to confirm entry.
        """
        trade = kwargs.get('trade')

        if trade is not None and side == 'short':
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not dataframe.empty:
                try:
                    entry_candle = dataframe.iloc[-1]
                    entry_atr = entry_candle.get('atr')
                    if not pd.isna(entry_atr):
                        trade.set_custom_data(key='entry_atr', value=float(entry_atr))
                except (KeyError, IndexError) as e:
                    self.logger.warning(f"Failed to store entry ATR for {pair}: {e}")

        return True

    def _add_ichimoku(self, df: DataFrame) -> None:
        """
        Add Ichimoku indicator columns to the dataframe.

        :param df: Input dataframe with OHLC data.
        """
        ichi = ftt.ichimoku(df, **self.ICHI_PARAMS)
        df['senkou_a'] = ichi['senkou_span_a']
        df['senkou_b'] = ichi['senkou_span_b']
        df['chikou_span'] = ichi['chikou_span']
        df['tenkan_sen'] = ichi['tenkan_sen']
        df['kijun_sen'] = ichi['kijun_sen']
        df['cloud_green'] = ichi['cloud_green']
        df['cloud_red'] = ichi['cloud_red']

    @informative('4h')
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate 4h Ichimoku, SAR, and RSI."""
        self._add_ichimoku(dataframe)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate 1h indicators."""
        # Mark 4h boundaries for long entries
        dataframe['is_4h_boundary'] = dataframe['date'].dt.hour % 4 == 0

        # Cloud status for short entries
        dataframe['cloud_bearish'] = dataframe['senkou_a_4h'] < dataframe['senkou_b_4h']

        # Price velocity for short exits
        dataframe['price_velocity'] = (
            (dataframe['close'] - dataframe['close'].shift(self.price_velocity_window.value)) /
            dataframe['close'].shift(self.price_velocity_window.value)
        )

        # ATR for short stop loss
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # Store for custom functions
        self.custom_info[metadata['pair']] = dataframe[[
            'date', 'close', 'sar_4h', 'rsi_4h', 'price_velocity', 'atr',
            'senkou_a_4h', 'senkou_b_4h'
        ]].copy().set_index('date')

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Dual entry system:
        1. LONG: Ichimoku cloud crossover at 4h boundaries
        2. SHORT: Senkou B retest breakdown
        """
        # Initialize
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['buy'] = 0
        dataframe['enter_tag'] = ''

        # === LONG ENTRY ===
        at_4h_boundary = dataframe['is_4h_boundary']
        effective_close = dataframe['close_4h']

        prev_close_4h = effective_close.shift(4)
        prev_senkou_a = dataframe['senkou_a_4h'].shift(4)

        prev_below_cloud = prev_close_4h < prev_senkou_a
        curr_above_cloud = effective_close > dataframe['senkou_a_4h']
        cloud_green = dataframe['senkou_a_4h'] > dataframe['senkou_b_4h']
        sar_below_close = dataframe['sar_4h'] < effective_close

        long_entry = at_4h_boundary & prev_below_cloud & curr_above_cloud & cloud_green & sar_below_close

        # === SHORT ENTRY ===
        window = self.retest_lookback_window.value

        dataframe['retested_senkou_b'] = dataframe['high'] >= dataframe['senkou_b_4h']
        dataframe['had_senkou_b_retest'] = dataframe['retested_senkou_b'].rolling(
            window=window, min_periods=1
        ).max().astype(bool)

        dataframe['cross_down_senkou_b'] = (
            (dataframe['close'].shift(1) >= dataframe['senkou_b_4h'].shift(1)) &
            (dataframe['close'] < dataframe['senkou_b_4h'])
        )

        short_entry = (
            dataframe['cloud_bearish'] &
            dataframe['had_senkou_b_retest'] &
            dataframe['cross_down_senkou_b']
        )

        # Apply signals
        dataframe.loc[long_entry, 'enter_long'] = 1
        dataframe.loc[long_entry, 'enter_tag'] = 'long_entry'
        dataframe.loc[short_entry, 'enter_short'] = 1
        dataframe.loc[short_entry, 'enter_tag'] = 'short_entry'
        dataframe.loc[long_entry | short_entry, 'buy'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signals disabled - using custom_exit."""
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''
        dataframe['sell'] = 0
        return dataframe
