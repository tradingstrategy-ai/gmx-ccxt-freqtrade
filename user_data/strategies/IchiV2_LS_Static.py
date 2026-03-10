# IchiV2_LS_Static - Dual Long/Short Ichimoku Strategy (1h timeframe)
# Author: Gui
# Version: 2.0
# Description: Combines cloud crossover (long) with senkou B retest breakdown (short)

from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
pd.options.mode.chained_assignment = None
import technical.indicators as ftt
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime
from freqtrade.persistence import Trade
from freqtrade.enums import RunMode
from freqtrade.strategy import informative, DecimalParameter, IntParameter, BooleanParameter, CategoricalParameter
from freqtrade.strategy.strategy_helper import stoploss_from_absolute
from freqtrade.exchange import timeframe_to_prev_date
import logging
import json
from freqtrade.optimize.space import SKDecimal 

class IchiV2_LS_Static(IStrategy):
    """
    IchiV2_LS_Static - for static config bots

    Dual long/short Ichimoku strategy on 1h timeframe.

    Long entries (checked at 4h boundary):
    - 4h close crosses above senkou_a_4h
    - Cloud is green (senkou_a_4h > senkou_b_4h)
    - SAR is below close (sar_4h < close_4h)

    Long exits:
    - 1h close crosses below sar_4h (exit on SAR cross)
    - Base stoploss at -0.2 as fallback
    - No ATR stop

    Short entries (checked on any 1h candle):
    - Cloud is bearish (senkou_a < senkou_b)
    - Price retested senkou_b (high >= senkou_b) within lookback window
    - Current price breaks down below senkou_b

    Short exits:
    - RSI 4h oversold (< 25)
    - OR price velocity exhaustion (< -10%)
    - ATR-based stop loss (3.5x ATR from entry, locked at entry)
    - No SAR exit for shorts

    Standard Freqtrade position sizing (no market cap scaling).

                                            MIXED TAG STATS                                         
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃           ┃           ┃        ┃            ┃       Tot ┃            ┃           ┃            ┃
┃           ┃      Exit ┃        ┃ Avg Profit ┃    Profit ┃ Tot Profit ┃       Avg ┃  Win  Draw ┃
┃ Enter Tag ┃    Reason ┃ Trades ┃          % ┃      USDT ┃          % ┃  Duration ┃ Loss  Win% ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ short_en… │ tp_veloc… │    184 │      11.93 │   702.255 │     702.25 │   2 days, │  168     0 │
│           │           │        │            │           │            │  11:11:00 │   16  91.3 │
│ long_ent… │ sar_exit… │   1121 │       2.38 │   606.182 │     606.18 │    1 day, │  515     0 │
│           │           │        │            │           │            │  21:13:00 │  606  45.9 │
│ short_en… │ tp_rsi_4… │    159 │      13.38 │   596.850 │     596.85 │   6 days, │  143     0 │
│           │           │        │            │           │            │  15:31:00 │   16  89.9 │
│ short_en… │ senkou_a… │    431 │        2.0 │   288.346 │     288.35 │   4 days, │  299     0 │
│           │           │        │            │           │            │   3:47:00 │  132  69.4 │
│ short_en… │ force_ex… │      3 │       5.33 │    15.784 │      15.78 │   5 days, │    3     0 │
│           │           │        │            │           │            │  19:20:00 │    0   100 │
│ long_ent… │ senkou_a… │    103 │      -0.25 │   -10.824 │     -10.82 │  19:07:00 │   42     0 │
│           │           │        │            │           │            │           │   61  40.8 │
│ short_en… │ trailing… │    257 │      -3.61 │  -220.982 │    -220.98 │    1 day, │    2     0 │
│           │           │        │            │           │            │  23:23:00 │  255   0.8 │
│ long_ent… │ stop_loss │    186 │      -7.23 │  -328.957 │    -328.96 │  16:19:00 │    0     0 │
│           │           │        │            │           │            │           │  186     0 │
│ short_en… │ stop_loss │    651 │      -4.13 │  -709.723 │    -709.72 │    1 day, │    0     0 │
│           │           │        │            │           │            │  12:31:00 │  651     0 │
│     TOTAL │           │   3095 │       0.93 │   938.931 │     938.93 │   2 days, │ 1172     0 │
│           │           │        │            │           │            │   7:21:00 │ 1923  37.9 │
└───────────┴───────────┴────────┴────────────┴───────────┴────────────┴───────────┴────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2020-10-21 20:00:00             │
│ Backtesting to                │ 2025-12-24 00:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 3095 / 1.64                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 1038.931 USDT                   │
│ Absolute profit               │ 938.931 USDT                    │
│ Total profit %                │ 938.93%                         │
│ CAGR %                        │ 57.19%                          │
│ Sortino                       │ 3.25                            │
│ Sharpe                        │ 1.59                            │
│ Calmar                        │ 5.32                            │
│ SQN                           │ 4.99                            │
│ Profit factor                 │ 1.51                            │
│ Expectancy (Ratio)            │ 0.30 (0.32)                     │
│ Avg. daily profit             │ 0.497 USDT                      │
│ Avg. stake amount             │ 26.458 USDT                     │
│ Total trade volume            │ 163397.423 USDT                 │
│                               │                                 │
│ Long / Short trades           │ 1410 / 1685                     │
│ Long / Short profit %         │ 266.40% / 672.53%               │
│ Long / Short profit USDT      │ 266.400 / 672.530               │
│                               │                                 │
│ Best Pair                     │ MOODENG/USDT:USDT 118.52%       │
│ Worst Pair                    │ BNB/USDT:USDT -15.69%           │
│ Best trade                    │ MOODENG/USDT:USDT 196.35%       │
│ Worst trade                   │ NEAR/USDT:USDT -26.36%          │
│ Best day                      │ 100.93 USDT                     │
│ Worst day                     │ -28.59 USDT                     │
│ Days win/draw/lose            │ 469 / 658 / 763                 │
│ Min/Max/Avg. Duration Winners │ 0d 00:00 / 30d 23:00 / 3d 17:15 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 17d 09:00 / 1d 10:42 │
│ Max Consecutive Wins / Loss   │ 17 / 24                         │
│ Rejected Entry signals        │ 694                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 91.397 USDT                     │
│ Max balance                   │ 1038.931 USDT                   │
│ Max % of account underwater   │ 19.66%                          │
│ Absolute drawdown             │ 89.8 USDT (10.74%)              │
│ Drawdown duration             │ 50 days 01:00:00                │
│ Profit at drawdown start      │ 736.105 USDT                    │
│ Profit at drawdown end        │ 646.306 USDT                    │
│ Drawdown start                │ 2025-08-17 16:00:00             │
│ Drawdown end                  │ 2025-10-06 17:00:00             │
│ Market change                 │ 353.16%                         │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2020-10-21 20:00:00 -> 2025-12-24 00:00:00 | Max open trades : 10
                                        STRATEGY SUMMARY                                         
┏━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃           ┃        ┃            ┃       Tot ┃            ┃           ┃            ┃           ┃
┃           ┃        ┃ Avg Profit ┃    Profit ┃ Tot Profit ┃       Avg ┃  Win  Draw ┃           ┃
┃  Strategy ┃ Trades ┃          % ┃      USDT ┃          % ┃  Duration ┃ Loss  Win% ┃  Drawdown ┃
┡━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ IchiV2_L… │   3095 │       0.93 │   938.931 │     938.93 │   2 days, │ 1172     0 │ 89.8 USDT │
│           │        │            │           │            │   7:21:00 │ 1923  37.9 │    10.74% │
└───────────┴────────┴────────────┴───────────┴────────────┴───────────┴────────────┴───────────┘
➜ 


    """

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self._pairs_analyzed_count = 0

    def _log_jsonl(self, signal_type: str, pair: str = None, 
                   conditions: dict = None, indicators: dict = None,
                   trade_data: dict = None, **extra_kwargs):
        """
        Universal JSONL logger for strategy analysis.
        
        :param signal_type: Type of signal/analysis (e.g., 'long_entry_check', 'short_exit_check')
        :param pair: Trading pair
        :param conditions: Dict of conditions being evaluated {name: bool}
        :param indicators: Dict of indicator values {name: float}
        :param trade_data: Dict of trade-specific data (trade_id, profit, etc.)
        :param extra_kwargs: Any additional key-value pairs to log
        """
        import numpy as np
        
        def convert_to_serializable(obj, max_decimals=4):
            """Convert numpy/pandas types to native Python types with decimal precision limit."""
            if isinstance(obj, (np.integer, np.floating)):
                return round(float(obj), max_decimals)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, float):
                return round(obj, max_decimals)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v, max_decimals) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item, max_decimals) for item in obj]
            elif pd.isna(obj):
                return None
            return obj
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "signal_type": signal_type,
        }
        
        # Add pair if provided
        if pair:
            log_entry["pair"] = pair
        
        # Add conditions if provided
        if conditions:
            log_entry["conditions"] = convert_to_serializable(conditions)
            # Add condition summary
            log_entry["conditions_passed"] = sum(1 for v in conditions.values() if v)
            log_entry["conditions_total"] = len(conditions)
            log_entry["all_conditions_met"] = all(conditions.values())
        
        # Add indicators if provided
        if indicators:
            log_entry["indicators"] = convert_to_serializable(indicators)
        
        # Add trade data if provided
        if trade_data:
            log_entry["trade"] = convert_to_serializable(trade_data)
        
        # Add any extra kwargs
        log_entry.update(convert_to_serializable(extra_kwargs))
        
        # Log as single-line JSON (no prefix for easy parsing)
        self.logger.info(json.dumps(log_entry))

    def _calculate_atr_stop_price(self, current_price: float, atr: float, is_short: bool) -> dict:
        """
        Calculate ATR-based stop loss price and related metrics.
        
        :param current_price: Current market price
        :param atr: Current ATR value
        :param is_short: True if short position, False if long
        :return: Dict with stop price and distance info
        """
        atr_multiplier = self.atr_stop_multiplier.value
        atr_distance = atr_multiplier * atr
        
        if is_short:
            # Short: stop is ABOVE entry (price + distance)
            stop_price = current_price + atr_distance
            stop_pct = (atr_distance / current_price) * 100
        else:
            # Long: stop is BELOW entry (price - distance)
            stop_price = current_price - atr_distance
            stop_pct = (atr_distance / current_price) * 100
        
        return {
            'atr_stop_price': stop_price,
            'atr_stop_distance': atr_distance,
            'atr_stop_pct': stop_pct,
            'atr_multiplier': atr_multiplier,
        }

    INTERFACE_VERSION = 3
    can_short = True  # Set to False to test long-only performance

    # Hyperoptable parameters
    buy_params = {
        # Short entry (RetestSenkou)
        'retest_lookback_window': 24,    # Max candles to look for retest (24h)
        'rsi_tp_threshold': 25,           # RSI oversold threshold for shorts
        'velocity_tp_threshold': -0.1,    # Velocity threshold for shorts
        'price_velocity_window': 10,      # Velocity calculation window
    }

    # Short entry parameters
    retest_lookback_window = IntParameter(4, 96, default=24, space='buy', optimize=False)

    # Short exit parameters
    rsi_tp_threshold = IntParameter(15, 35, default=25, space='sell', optimize=False)
    use_rsi_exit = IntParameter(0, 1, default=1, space='sell', optimize=False)

    # ATR stop loss for shorts
    atr_stop_multiplier = DecimalParameter(1.5, 4.0, default=3.5, decimals=1, space='sell', optimize=False)
    atr_timeperiod = IntParameter(2, 20, default=14, space='sell', optimize=False)

    # Price velocity window
    velocity_tp_threshold = DecimalParameter(-0.13, -0.06, default=-0.1, decimals=2, space='sell', optimize=True)
    price_velocity_window = IntParameter(4, 20, default=20, space='sell', optimize=False)

    # D8: Daily cloud regime filter (exp 018)
    daily_cloud_regime_enabled = BooleanParameter(default=True, space='buy', optimize=False)
    long_daily_cloud_filter = CategoricalParameter(
        ["all", "green_cloud"], default="green_cloud", space="buy", optimize=False)
    short_daily_cloud_filter = CategoricalParameter(
        ["all", "green_cloud"], default="all", space="sell", optimize=False)

    # D8: Short ATR trailing (exp 015/018)
    short_atr_trailing_enabled = BooleanParameter(default=True, space='sell', optimize=False)
    short_atr_trailing_multiplier = DecimalParameter(4.0, 8.0, default=6.1, decimals=1, space='sell', optimize=False)
    short_atr_trailing_activation = DecimalParameter(0.0, 0.10, default=0.03, decimals=3, space='sell', optimize=False)

    sell_params = {}
    custom_info = {}

    # ROI table - minimal
    minimal_roi = {
        "0": 10.0  # Disabled
    }

    # Stop loss
    # -0.2 for longs (only SAR exit matters)
    # Shorts use ATR-based custom stoploss
    stoploss = -0.129
    use_custom_stoploss = True  # Only applies to shorts (returns None for longs)

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
            # 4h Bollinger Bands
            # 'bb_upper_4h': {'color': 'lightblue'},
            # 'bb_middle_4h': {'color': 'lightgray'},
            # 'bb_lower_4h': {'color': 'lightblue'},
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

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, after_fill: bool,
                       **kwargs) -> float | None:
        """
        Dynamic stoploss comparing base stoploss vs strategy-specific stops.

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

                # Calculate base stoploss price (below entry)
                entry_rate = trade.open_rate
                base_stop_price = entry_rate * (1 + self.stoploss)  # self.stoploss is negative

                # For longs: Choose the HIGHER stop price (closer to current price = more conservative)
                # SAR trails up as price goes up, so it may be higher than base stoploss
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

            # For shorts: ATR stop is ABOVE entry price
            atr_stop_price = entry_rate + atr_distance
            base_stop_price = entry_rate * (1 + abs(self.stoploss))

            # Static stop: choose the LOWER (more conservative for shorts)
            static_stop = min(atr_stop_price, base_stop_price)

            # Optional short ATR trailing (D8)
            if self.short_atr_trailing_enabled.value:
                price_profit = (entry_rate - current_rate) / entry_rate
                trailing_already_active = trade.get_custom_data('short_trailing_active') is not None
                activated = trailing_already_active or (price_profit >= self.short_atr_trailing_activation.value)

                if activated:
                    if not trailing_already_active:
                        trade.set_custom_data('short_trailing_active', True)

                    trailing_distance = self.short_atr_trailing_multiplier.value * float(entry_atr)
                    trailing_stop_price = current_rate + trailing_distance

                    # Only use trailing if stop is below entry (protecting actual profit)
                    if trailing_stop_price < entry_rate:
                        final_stop_price = min(trailing_stop_price, static_stop)
                        return stoploss_from_absolute(
                            stop_rate=final_stop_price,
                            current_rate=current_rate,
                            is_short=True,
                            leverage=trade.leverage
                        )

            return stoploss_from_absolute(
                stop_rate=static_stop,
                current_rate=current_rate,
                is_short=True,
                leverage=trade.leverage
            )

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> str | bool | None:
        """
        Exit logic - COMPLETELY SEPARATE for longs vs shorts:

        LONGS (from IchiV3_LS_1h):
        - SAR exit: 1h close crosses below sar_4h → exit immediately
        - This is the PRIMARY and ONLY exit for longs (base stoploss is just fallback)

        SHORTS (from IchiV2_Short_RetestSenkou):
        - RSI 4h oversold (< 25)
        - OR velocity exhaustion (< -10%)
        - ATR-based stop loss (via custom_stoploss)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None

        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        try:
            last_row = dataframe.iloc[-1]
            last_close = last_row['close']
            last_sar = last_row.get('sar_4h')

            # LONG EXIT: SAR
            if not trade.is_short:
                # Cloud flip check (to prevent concurrent trades between long and short)
                cloud_flip = last_row['senkou_a_4h'] < last_row['senkou_b_4h']
                if cloud_flip:
                    if is_trading_mode:
                        self._log_jsonl(
                            signal_type="long_exit_check",
                            pair=pair,
                            conditions={'cloud_flip_bearish': cloud_flip},
                            indicators={
                                'close': float(last_close),
                                'sar_4h': float(last_sar) if not pd.isna(last_sar) else None,
                                'senkou_a_4h': float(last_row['senkou_a_4h']),
                                'senkou_b_4h': float(last_row['senkou_b_4h']),
                            },
                            trade_data={
                                'trade_id': trade.id,
                                'current_profit': current_profit,
                                'current_profit_pct': current_profit * 100,
                            },
                            exit_triggered=True,
                            exit_reason='senkou_a_4h_exit_long'
                        )
                    return 'senkou_a_4h_exit_long'
                # SAR cross down
                sar_cross_down = not pd.isna(last_sar) and last_close <= last_sar
                
                if is_trading_mode:
                    self._log_jsonl(
                        signal_type="long_exit_check",
                        pair=pair,
                        conditions={'sar_cross_down': sar_cross_down},
                        indicators={
                            'close': float(last_close),
                            'sar_4h': float(last_sar) if not pd.isna(last_sar) else None,
                        },
                        trade_data={
                            'trade_id': trade.id,
                            'current_profit': current_profit,
                            'current_profit_pct': current_profit * 100,
                        },
                        exit_triggered=sar_cross_down,
                        exit_reason='sar_exit_long' if sar_cross_down else None
                    )
                
                if sar_cross_down:
                    return 'sar_exit_long'

            # SHORT EXIT: RSI + Velocity
            if trade.is_short:
                last_rsi_4h = last_row.get('rsi_4h')
                last_velocity = last_row.get('price_velocity')

                # Cloud flip check (to prevent concurrent trades between long and short)
                cloud_flip = last_row['senkou_a_4h'] > last_row['senkou_b_4h']
                if cloud_flip:
                    if is_trading_mode:
                        self._log_jsonl(
                            signal_type="short_exit_check",
                            pair=pair,
                            conditions={'cloud_flip_bullish': cloud_flip},
                            indicators={
                                'close': float(last_close),
                                'senkou_a_4h': float(last_row['senkou_a_4h']),
                                'senkou_b_4h': float(last_row['senkou_b_4h']),
                                'rsi_4h': float(last_rsi_4h) if not pd.isna(last_rsi_4h) else None,
                                'price_velocity': float(last_velocity) if not pd.isna(last_velocity) else None,
                                'atr': float(last_row.get('atr', 0)),
                            },
                            trade_data={
                                'trade_id': trade.id,
                                'current_profit': current_profit,
                                'current_profit_pct': current_profit * 100,
                            },
                            exit_triggered=True,
                            exit_reason='senkou_a_4h_exit_short'
                        )
                    return 'senkou_a_4h_exit_short'

                # Check exit conditions
                rsi_oversold = False
                velocity_exhausted = False
                
                if self.use_rsi_exit.value == 1:
                    rsi_oversold = not pd.isna(last_rsi_4h) and last_rsi_4h < self.rsi_tp_threshold.value
                
                velocity_exhausted = not pd.isna(last_velocity) and last_velocity < self.velocity_tp_threshold.value

                if is_trading_mode:
                    self._log_jsonl(
                        signal_type="short_exit_check",
                        pair=pair,
                        conditions={
                            'rsi_oversold': rsi_oversold,
                            'velocity_exhausted': velocity_exhausted,
                        },
                        indicators={
                            'close': float(last_close),
                            'rsi_4h': float(last_rsi_4h) if not pd.isna(last_rsi_4h) else None,
                            'price_velocity': float(last_velocity) if not pd.isna(last_velocity) else None,
                            'atr': float(last_row.get('atr', 0)),
                            'rsi_threshold': self.rsi_tp_threshold.value,
                            'velocity_threshold': self.velocity_tp_threshold.value,
                        },
                        trade_data={
                            'trade_id': trade.id,
                            'current_profit': current_profit,
                            'current_profit_pct': current_profit * 100,
                        },
                        exit_triggered=rsi_oversold or velocity_exhausted,
                        exit_reason='tp_rsi_4h_oversold' if rsi_oversold else ('tp_velocity_achieved' if velocity_exhausted else None)
                    )
                
                if rsi_oversold:
                    return 'tp_rsi_4h_oversold'
                
                if velocity_exhausted:
                    return 'tp_velocity_achieved'

        except (KeyError, IndexError) as e:
            self.logger.warning(f"Error in custom_exit for {pair}: {e}")

        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str | None,
                           side: str, **kwargs) -> bool:
        """Store ATR at entry time for shorts and log detailed entry information."""
        trade = kwargs.get('trade')

        # Store ATR for shorts
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

        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        if is_trading_mode:
            self.logger.info(f"ENTRY | {pair} | {side} | amount={amount} | rate={rate} | time={current_time}")

        return True

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                          rate: float, time_in_force: str, exit_reason: str,
                          current_time: datetime, **kwargs) -> bool:
        """Log detailed trade exit information."""
        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        if is_trading_mode:
            profit_ratio = trade.calc_profit_ratio(rate)
            duration = current_time - trade.open_date_utc
            side = 'short' if trade.is_short else 'long'

            self.logger.info(f"EXIT | {pair} | {side} | reason={exit_reason} | profit={profit_ratio:.2%} | duration={duration} | time={current_time}")

        return True

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        Called at the start of each trading cycle.
        Logs balance and open positions summary.
        """
        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        if is_trading_mode:
            self.logger.info(f"🔄 NEW TRADING CYCLE: {current_time}")
            self._log_portfolio_summary(current_time, **kwargs)

        # Reset counter for new cycle
        self._pairs_analyzed_count = 0

    def _log_portfolio_summary(self, cycle_time: datetime, **kwargs) -> None:
        """
        Log portfolio summary with balance and open positions details in JSONL format.
        """
        open_trades = Trade.get_open_trades()

        # Get balance information
        balance_info = {}
        stake_currency = self.config.get('stake_currency', 'USDC')
        wallets = kwargs.get('wallets') or self.wallets

        if wallets:
            try:
                balance_info = {
                    'total_balance': float(wallets.get_total(stake_currency)),
                    'total_stake_amount': float(wallets.get_total_stake_amount()),
                    'free_balance': float(wallets.get_free(stake_currency)),
                    'used_balance': float(wallets.get_used(stake_currency)),
                    'stake_currency': stake_currency,
                }
            except Exception as e:
                self.logger.warning(f"Failed to fetch balance info: {e}")
                balance_info = {'error': str(e)}

        # Collect position details
        positions = []
        total_unrealized_pnl = 0
        winning = 0
        losing = 0

        for trade in open_trades:
            # Get current rate from dataprovider
            try:
                dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
                if not dataframe.empty:
                    current_rate = dataframe.iloc[-1]['close']
                else:
                    current_rate = trade.open_rate
            except Exception:
                current_rate = trade.open_rate

            profit_ratio = trade.calc_profit_ratio(current_rate)
            profit_pct = profit_ratio * 100
            entry_date = trade.open_date_utc
            duration = cycle_time - entry_date
            duration_seconds = duration.total_seconds()

            total_unrealized_pnl += profit_ratio
            if profit_ratio > 0:
                winning += 1
            else:
                losing += 1

            side_label = "short" if trade.is_short else "long"

            positions.append({
                'trade_id': trade.id,
                'pair': trade.pair,
                'side': side_label,
                'entry_rate': float(trade.open_rate),
                'current_rate': float(current_rate),
                'entry_time': entry_date.isoformat(),
                'profit_pct': float(profit_pct),
                'profit_ratio': float(profit_ratio),
                'duration_seconds': int(duration_seconds),
                'duration_str': str(duration),
                'is_winning': profit_ratio > 0,
            })

        # Log portfolio summary as JSONL
        self._log_jsonl(
            signal_type="portfolio_summary",
            cycle_time=cycle_time.isoformat(),
            balance=balance_info,
            positions_count=len(open_trades),
            positions=positions,
            summary={
                'winning_positions': winning,
                'losing_positions': losing,
                'total_unrealized_pnl_pct': float(total_unrealized_pnl * 100),
                'total_unrealized_pnl_ratio': float(total_unrealized_pnl),
            }
        )

    def _add_ichimoku(self, df: DataFrame) -> None:
        ichi = ftt.ichimoku(df, **self.ICHI_PARAMS)
        df['senkou_a'] = ichi['senkou_span_a']
        df['senkou_b'] = ichi['senkou_span_b']
        df['chikou_span'] = ichi['chikou_span']
        df['tenkan_sen'] = ichi['tenkan_sen']
        df['kijun_sen'] = ichi['kijun_sen']
        df['cloud_green'] = ichi['cloud_green']
        df['cloud_red'] = ichi['cloud_red']

    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Daily Ichimoku cloud for regime filtering (exp 018)."""
        self._add_ichimoku(dataframe)
        return dataframe

    @informative('4h')
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate 4h Ichimoku, SAR, and RSI."""
        self._add_ichimoku(dataframe)
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)

        # #  Bollinger Bands for analysis (using qtpylib)
        # bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=3.0)
        # dataframe['bb_upper'] = bollinger['upper']
        # dataframe['bb_middle'] = bollinger['mid']
        # dataframe['bb_lower'] = bollinger['lower']
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

        # Daily cloud regime filter (D8)
        if self.daily_cloud_regime_enabled.value:
            has_daily_cloud = dataframe['senkou_a_1d'].notna() & dataframe['senkou_b_1d'].notna()
            daily_cloud_green = (dataframe['senkou_a_1d'] > dataframe['senkou_b_1d']) & has_daily_cloud

            long_dc = self.long_daily_cloud_filter.value
            if long_dc == 'green_cloud':
                dataframe['daily_cloud_allows_long'] = daily_cloud_green | ~has_daily_cloud
            else:
                dataframe['daily_cloud_allows_long'] = True

            short_dc = self.short_daily_cloud_filter.value
            if short_dc == 'green_cloud':
                dataframe['daily_cloud_allows_short'] = daily_cloud_green | ~has_daily_cloud
            else:
                dataframe['daily_cloud_allows_short'] = True
        else:
            dataframe['daily_cloud_allows_long'] = True
            dataframe['daily_cloud_allows_short'] = True

        # Store for custom functions
        self.custom_info[metadata['pair']] = dataframe[[
            'date', 'close', 'sar_4h', 'rsi_4h', 'price_velocity', 'atr',
            'senkou_a_4h', 'senkou_b_4h'
            #  'bb_upper_4h'
        ]].copy().set_index('date')

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Dual entry system:
        1. LONG: Ichimoku cloud crossover at 4h boundaries
        2. SHORT: Senkou B retest breakdown
        """
        pair = metadata.get('pair', 'unknown')
        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        # Initialize
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['buy'] = 0
        dataframe['enter_tag'] = ''

        # === LONG ENTRY (IchiV3_LS_1h logic) ===
        # Only at 4h boundaries
        at_4h_boundary = dataframe['is_4h_boundary']
        effective_close = dataframe['close_4h']

        # Long: prev 4h close was below senkou_a, current 4h close is above
        prev_close_4h = effective_close.shift(4)
        prev_senkou_a = dataframe['senkou_a_4h'].shift(4)

        prev_below_cloud = prev_close_4h < prev_senkou_a
        curr_above_cloud = effective_close > dataframe['senkou_a_4h']
        cloud_green = dataframe['senkou_a_4h'] > dataframe['senkou_b_4h']
        sar_below_close = dataframe['sar_4h'] < effective_close

        long_entry = at_4h_boundary & prev_below_cloud & curr_above_cloud & cloud_green & sar_below_close
        long_entry = long_entry & dataframe['daily_cloud_allows_long']

        # === SHORT ENTRY (RetestSenkou logic) ===
        window = self.retest_lookback_window.value

        # Retest detection
        dataframe['retested_senkou_b'] = dataframe['high'] >= dataframe['senkou_b_4h']
        dataframe['had_senkou_b_retest'] = dataframe['retested_senkou_b'].rolling(
            window=window, min_periods=1
        ).max().astype(bool)

        # Breakdown detection
        dataframe['cross_down_senkou_b'] = (
            (dataframe['close'].shift(1) >= dataframe['senkou_b_4h'].shift(1)) &
            (dataframe['close'] < dataframe['senkou_b_4h'])
        )

        # Short entry: cloud bearish + retest + breakdown
        short_entry = (
            dataframe['cloud_bearish'] &
            dataframe['had_senkou_b_retest'] &
            dataframe['cross_down_senkou_b']
        )
        short_entry = short_entry & dataframe['daily_cloud_allows_short']

        # Apply signals
        dataframe.loc[long_entry, 'enter_long'] = 1
        dataframe.loc[long_entry, 'enter_tag'] = 'long_entry'
        dataframe.loc[short_entry, 'enter_short'] = 1
        dataframe.loc[short_entry, 'enter_tag'] = 'short_entry'
        dataframe.loc[long_entry | short_entry, 'buy'] = 1

        # Signal logging (only in trading mode)
        if is_trading_mode and len(dataframe) > 0:
            latest = dataframe.iloc[-1]

            # LONG signal analysis
            if latest['is_4h_boundary']:
                long_conditions = {
                    'prev_below_cloud': bool(prev_below_cloud.iloc[-1]) if len(prev_below_cloud) > 0 else False,
                    'curr_above_cloud': bool(curr_above_cloud.iloc[-1]) if len(curr_above_cloud) > 0 else False,
                    'cloud_green': bool(cloud_green.iloc[-1]) if len(cloud_green) > 0 else False,
                    'sar_below_close': bool(sar_below_close.iloc[-1]) if len(sar_below_close) > 0 else False,
                }
                
                long_signal = latest['enter_long'] == 1
                
                # Calculate ATR stop for longs (informational - longs use SAR exit)
                atr_stop_info = self._calculate_atr_stop_price(
                    current_price=float(latest['close']),
                    atr=float(latest.get('atr', 0)),
                    is_short=False
                )
                
                # Standardized JSONL logging
                self._log_jsonl(
                    signal_type="long_entry_check",
                    pair=pair,
                    conditions=long_conditions,
                    indicators={
                        'close': float(latest['close']),
                        'close_4h': float(latest['close_4h']),
                        'senkou_a_4h': float(latest['senkou_a_4h']),
                        'senkou_b_4h': float(latest['senkou_b_4h']),
                        'sar_4h': float(latest['sar_4h']),
                        'rsi_4h': float(latest.get('rsi_4h', 0)),
                        'atr': float(latest.get('atr', 0)),
                        'atr_stop_price': atr_stop_info['atr_stop_price'],
                        'atr_stop_distance': atr_stop_info['atr_stop_distance'],
                        'atr_stop_pct': atr_stop_info['atr_stop_pct'],
                    },
                    signal_triggered=long_signal,
                    is_4h_boundary=True,
                    action='ENTER_LONG' if long_signal else 'REJECTED',
                    note='longs_use_sar_exit_not_atr'
                )

            # SHORT signal analysis
            short_conditions = {
                'cloud_bearish': bool(latest['cloud_bearish']),
                'had_retest': bool(latest['had_senkou_b_retest']),
                'cross_down': bool(latest['cross_down_senkou_b']),
            }
            
            short_signal = latest['enter_short'] == 1
            
            # Only log if at least one condition is met or signal triggered (reduce noise)
            should_log_short = short_signal or latest['cloud_bearish'] or latest['had_senkou_b_retest'] or latest['cross_down_senkou_b']
            
            if should_log_short:
                # Calculate ATR stop for shorts (this is the actual stop used)
                atr_stop_info = self._calculate_atr_stop_price(
                    current_price=float(latest['close']),
                    atr=float(latest.get('atr', 0)),
                    is_short=True
                )
                
                # Standardized JSONL logging
                self._log_jsonl(
                    signal_type="short_entry_check",
                    pair=pair,
                    conditions=short_conditions,
                    indicators={
                        'close': float(latest['close']),
                        'senkou_a_4h': float(latest['senkou_a_4h']),
                        'senkou_b_4h': float(latest['senkou_b_4h']),
                        'rsi_4h': float(latest.get('rsi_4h', 0)),
                        'price_velocity': float(latest.get('price_velocity', 0)),
                        'atr': float(latest.get('atr', 0)),
                        'atr_stop_price': atr_stop_info['atr_stop_price'],
                        'atr_stop_distance': atr_stop_info['atr_stop_distance'],
                        'atr_stop_pct': atr_stop_info['atr_stop_pct'],
                    },
                    signal_triggered=short_signal,
                    action='ENTER_SHORT' if short_signal else 'REJECTED',
                    note='shorts_use_atr_stop'
                )

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signals disabled - using custom_exit."""
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''
        dataframe['sell'] = 0
        return dataframe



    class HyperOpt:
            """
            Custom hyperopt space definitions
            """
            @staticmethod
            def stoploss_space() -> list:
                """
                Define custom stoploss bounds for hyperopt.
                This limits stoploss optimization to your specified range.
                """
                return [
                    SKDecimal(-0.1, -0.02, decimals=3, name='stoploss')
                ]