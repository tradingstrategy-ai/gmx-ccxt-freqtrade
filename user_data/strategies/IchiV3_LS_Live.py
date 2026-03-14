# IchiV3_LS_1h_Merged - Dual Long/Short Ichimoku Strategy with Market Cap Sizing (1h timeframe)
# Author: Gui
# Version: 3.0
# Description: Combines cloud crossover (long) with senkou B retest (short) + dynamic position sizing

from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
pd.options.mode.chained_assignment = None
import technical.indicators as ftt
from datetime import datetime, timedelta
import numpy as np
from freqtrade.persistence import Trade
from freqtrade.enums import RunMode
from freqtrade.strategy import informative, DecimalParameter, IntParameter, BooleanParameter, CategoricalParameter
from freqtrade.strategy.strategy_helper import stoploss_from_absolute
from freqtrade.exchange import timeframe_to_prev_date
import logging
import json
import os
from freqtrade.util.coin_gecko import FtCoinGeckoApi
from freqtrade.optimize.hyperopt.hyperopt_interface import IHyperOpt
from freqtrade.optimize.space import Dimension, Integer


class IchiV3_LS_Live(IStrategy):
    """
    IchiV3_LS_Live - for LIVE config bots

    Dual long/short Ichimoku strategy on 1h timeframe WITH dynamic market cap position sizing.

    LONG SIDE (checked on 4h boundaries):
    - 4h close crosses above senkou_a_4h
    - Cloud is green (senkou_a_4h > senkou_b_4h)
    - Parabolic SAR is below close (sar_4h < close_4h)

    Long Exits:
    - 1h close crosses below sar_4h (SAR cross exit, checked every hour)
    - Failsafe stoploss at -0.2 (rare/backup, SAR normally handles exits)
    - No ATR-based stop (custom_stoploss returns None for longs)

    SHORT SIDE (checked on every 1h candle):
    - Cloud is bearish (senkou_a < senkou_b)
    - Price re-tested senkou_b (high >= senkou_b) within lookback window
    - Current price breaks down below senkou_b

    Short Exits:
    - RSI 4h is oversold (< 25)
    - OR velocity exhaustion (< -10%)
    - ATR-based stop loss (3.5x ATR below entry, value locked at entry)
    - No SAR exit for shorts

    ──────────────────────────────────────────────────────────────
    MARKET CAP SIZING (live bot):
      - Blue chip (≥ $50B): 4.8x base stake
      - Large cap (≥ $15B): 3.8x base stake
      - Mid cap (≥ $1.5B): 2.9x base stake
      - Degen (< $1.5B): 1.9x base stake
      - Per-pair max: 52% of available balance.

    Sizing is applied automatically per-pair for safety and exposure balancing on live bots.

                                                   ENTER TAG STATS                                                   
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃ Entries ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ short_entry │    1433 │         0.95 │        1385.368 │      1385.37 │ 2 days, 20:25:00 │  532     0   901  37.1 │
│  long_entry │    1088 │         0.94 │         449.146 │       449.15 │  1 day, 17:23:00 │  445     0   643  40.9 │
│       TOTAL │    2521 │         0.94 │        1834.514 │      1834.51 │  2 days, 8:45:00 │  977     0  1544  38.8 │
└─────────────┴─────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                      EXIT REASON STATS                                                       
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│     tp_rsi_4h_oversold │   142 │        13.11 │        1653.705 │       1653.7 │  6 days, 7:22:00 │  126     0    16  88.7 │
│   tp_velocity_achieved │   167 │        11.72 │        1620.985 │      1620.98 │ 2 days, 10:28:00 │  150     0    17  89.8 │
│ senkou_a_4h_exit_short │   365 │         1.96 │         640.790 │       640.79 │  4 days, 3:21:00 │  252     0   113  69.0 │
│          sar_exit_long │  1005 │         1.23 │         628.202 │        628.2 │  1 day, 19:12:00 │  413     0   592  41.1 │
│             force_exit │     4 │         7.48 │          94.027 │        94.03 │ 5 days, 19:15:00 │    4     0     0   100 │
│  senkou_a_4h_exit_long │    74 │         -0.5 │         -32.974 │       -32.97 │         19:06:00 │   32     0    42  43.2 │
│     trailing_stop_loss │   242 │        -4.17 │        -840.929 │      -840.93 │  2 days, 0:44:00 │    0     0   242     0 │
│              stop_loss │   522 │        -4.56 │       -1929.291 │     -1929.29 │  1 day, 11:10:00 │    0     0   522     0 │
│                  TOTAL │  2521 │         0.94 │        1834.514 │      1834.51 │  2 days, 8:45:00 │  977     0  1544  38.8 │
└────────────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                               MIXED TAG STATS                                                               
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃            Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ short_entry │     tp_rsi_4h_oversold │    142 │        13.11 │        1653.705 │       1653.7 │  6 days, 7:22:00 │  126     0    16  88.7 │
│ short_entry │   tp_velocity_achieved │    167 │        11.72 │        1620.985 │      1620.98 │ 2 days, 10:28:00 │  150     0    17  89.8 │
│ short_entry │ senkou_a_4h_exit_short │    365 │         1.96 │         640.790 │       640.79 │  4 days, 3:21:00 │  252     0   113  69.0 │
│  long_entry │          sar_exit_long │   1005 │         1.23 │         628.202 │        628.2 │  1 day, 19:12:00 │  413     0   592  41.1 │
│ short_entry │             force_exit │      4 │         7.48 │          94.027 │        94.03 │ 5 days, 19:15:00 │    4     0     0   100 │
│  long_entry │  senkou_a_4h_exit_long │     74 │         -0.5 │         -32.974 │       -32.97 │         19:06:00 │   32     0    42  43.2 │
│  long_entry │              stop_loss │      9 │       -20.02 │        -146.082 │      -146.08 │         21:07:00 │    0     0     9     0 │
│ short_entry │     trailing_stop_loss │    242 │        -4.17 │        -840.929 │      -840.93 │  2 days, 0:44:00 │    0     0   242     0 │
│ short_entry │              stop_loss │    513 │        -4.29 │       -1783.209 │     -1783.21 │  1 day, 11:25:00 │    0     0   513     0 │
│       TOTAL │                        │   2521 │         0.94 │        1834.514 │      1834.51 │  2 days, 8:45:00 │  977     0  1544  38.8 │
└─────────────┴────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2020-10-21 20:00:00             │
│ Backtesting to                │ 2025-12-15 09:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 2521 / 1.34                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 1934.514 USDT                   │
│ Absolute profit               │ 1834.514 USDT                   │
│ Total profit %                │ 1834.51%                        │
│ CAGR %                        │ 77.74%                          │
│ Sortino                       │ 2.07                            │
│ Sharpe                        │ 1.19                            │
│ Calmar                        │ 3.72                            │
│ SQN                           │ 3.11                            │
│ Profit factor                 │ 1.35                            │
│ Expectancy (Ratio)            │ 0.73 (0.22)                     │
│ Avg. daily profit             │ 0.976 USDT                      │
│ Avg. stake amount             │ 91.949 USDT                     │
│ Total trade volume            │ 462757.679 USDT                 │
│                               │                                 │
│ Long / Short trades           │ 1088 / 1433                     │
│ Long / Short profit %         │ 449.15% / 1385.37%              │
│ Long / Short profit USDT      │ 449.146 / 1385.368              │
│                               │                                 │
│ Best Pair                     │ SUI/USDT:USDT 354.51%           │
│ Worst Pair                    │ BNB/USDT:USDT -130.38%          │
│ Best trade                    │ DOGE/USDT:USDT 177.80%          │
│ Worst trade                   │ BNB/USDT:USDT -20.39%           │
│ Best day                      │ 217.496 USDT                    │
│ Worst day                     │ -74.83 USDT                     │
│ Days win/draw/lose            │ 474 / 714 / 693                 │
│ Min/Max/Avg. Duration Winners │ 0d 00:00 / 28d 10:00 / 3d 18:13 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 17d 03:00 / 1d 11:34 │
│ Max Consecutive Wins / Loss   │ 12 / 22                         │
│ Rejected Entry signals        │ 34                              │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 81.638 USDT                     │
│ Max balance                   │ 1934.514 USDT                   │
│ Max % of account underwater   │ 38.02%                          │
│ Absolute drawdown             │ 363.927 USDT (20.89%)           │
│ Drawdown duration             │ 54 days 05:00:00                │
│ Profit at drawdown start      │ 1641.963 USDT                   │
│ Profit at drawdown end        │ 1278.036 USDT                   │
│ Drawdown start                │ 2025-08-17 16:00:00             │
│ Drawdown end                  │ 2025-10-10 21:00:00             │
│ Market change                 │ 381.35%                         │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2020-10-21 20:00:00 -> 2025-12-15 09:00:00 | Max open trades : 10
                                                             STRATEGY SUMMARY                                                              
┏━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃     Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃             Drawdown ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ IchiV3_LS_1h │   2521 │         0.94 │        1834.514 │      1834.51 │ 2 days, 8:45:00 │  977     0  1544  38.8 │ 363.927 USDT  20.89% │
└──────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴──────────────────────┘
    """

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        # Initialize CoinGecko client for market cap data
        _coingecko_config = config.get("coingecko", {})
        self._coingecko = FtCoinGeckoApi(
            api_key=_coingecko_config.get("api_key", ""),
            is_demo=_coingecko_config.get("is_demo", True),
        )

        # File-based cache instead of TTLCache
        self._cache_file = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "market_cap_cache.json"))
        self._marketcap_cache = self._load_cache()
        self._pairs_analyzed_count = 0

    def _load_cache(self) -> dict:
        """Load market cap cache from file."""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is still valid (24h)
                    cache_time = datetime.fromisoformat(data.get('timestamp', '1970-01-01'))
                    if datetime.now() - cache_time < timedelta(hours=72):
                        self.logger.info(f"Loaded market cap cache with {len(data.get('marketcap', {}))} coins")
                        return data
                    else:
                        self.logger.info("Market cap cache expired, will refresh")
        except Exception as e:
            self.logger.warning(f"Failed to load cache: {e}")

        return {"marketcap": None, "timestamp": None}

    def _save_cache(self, marketcap_data: dict):
        """Save market cap cache to file."""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            cache_data = {
                "marketcap": marketcap_data,
                "timestamp": datetime.now().isoformat()
            }
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f)
            self.logger.info(f"Saved market cap cache with {len(marketcap_data)} coins")
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")

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
    USE_CUSTOM_STAKE = True  # Enable market cap-based position sizing

    # Hyperoptable parameters
    buy_params = {
        # Market Cap Tier Thresholds (in billions USD)
        'mcap_blue_chip_threshold': 50.0,    # >= $50B
        'mcap_large_cap_threshold': 15.0,    # >= $15B
        'mcap_mid_cap_threshold': 1.5,       # >= $1.5B

        # Market Cap Multipliers
        'mcap_blue_chip_multiplier': 4.8,    # Blue chip multiplier
        'mcap_large_cap_multiplier': 3.8,    # Large cap multiplier
        'mcap_mid_cap_multiplier': 2.9,      # Mid cap multiplier
        'mcap_degen_multiplier': 1.9,        # Degen/unknown multiplier

        # Position sizing parameters
        'per_pair_cap_pct': 0.52,            # Max % of available capital per pair

        # Short entry (RetestSenkou)
        'retest_lookback_window': 24,    # Max candles to look for retest (24h)
        'rsi_tp_threshold': 25,           # RSI oversold threshold for shorts
        'velocity_tp_threshold': -0.1,    # Velocity threshold for shorts
        'price_velocity_window': 10,     # Velocity calculation window
    }

    # Market Cap Tier Threshold Optimization
    mcap_blue_chip_threshold = DecimalParameter(20.0, 100.0, default=50.0, decimals=1, space='buy', optimize=True)
    mcap_large_cap_threshold = DecimalParameter(8.0, 40.0, default=15.0, decimals=1, space='buy', optimize=True)
    mcap_mid_cap_threshold = DecimalParameter(0.5, 20.0, default=1.5, decimals=1, space='buy', optimize=True)

    # Market Cap Multiplier Optimization
    mcap_blue_chip_multiplier = DecimalParameter(1.0, 8.0, default=4.8, decimals=1, space='buy', optimize=True)
    mcap_large_cap_multiplier = DecimalParameter(1.0, 7.0, default=3.8, decimals=1, space='buy', optimize=True)
    mcap_mid_cap_multiplier = DecimalParameter(1.0, 6.0, default=2.9, decimals=1, space='buy', optimize=True)
    mcap_degen_multiplier = DecimalParameter(0.5, 5.0, default=1.9, decimals=1, space='buy', optimize=True)

    # Position sizing parameter optimization
    per_pair_cap_pct = DecimalParameter(0.05, 1.0, default=0.52, decimals=2, space='buy', optimize=True)

    # Short entry parameters
    retest_lookback_window = IntParameter(4, 96, default=24, space='buy', optimize=False)

    # Short exit parameters
    rsi_tp_threshold = IntParameter(15, 35, default=25, space='sell', optimize=False)
    velocity_tp_threshold = DecimalParameter(-0.20, -0.05, default=-0.098, decimals=3, space='sell', optimize=False)
    use_rsi_exit = IntParameter(0, 1, default=1, space='sell', optimize=False)

    # ATR stop loss for shorts
    atr_stop_multiplier = DecimalParameter(1.5, 4.0, default=3.1, decimals=1, space='sell', optimize=False)
    short_hard_stoploss = DecimalParameter(0.03, 0.20, default=0.071, decimals=3, space='sell', optimize=False)

    # Price velocity window
    price_velocity_window = IntParameter(2, 12, default=10, space='buy', optimize=False)

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
    stoploss = -0.2
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

    def _get_market_cap_value(self, pair: str) -> float | None:
        """
        Get actual market cap VALUE in USD for a pair.

        :param pair: Trading pair (e.g., "BTC/USDC:USDC")
        :return: Market cap in USD or None if not found
        """
        marketcap_data = self._marketcap_cache.get("marketcap")

        if marketcap_data is None:
            try:
                # Fetch top 250 coins by market cap from CoinGecko
                data = self._coingecko.get_coins_markets(
                    vs_currency="usd",
                    order="market_cap_desc",
                    per_page="250",
                    page="1",
                    sparkline="false",
                )

                if data and len(data) > 0:
                    # Store as dict: symbol -> market_cap_value
                    marketcap_data = {
                        row["symbol"].upper(): row.get("market_cap", 0)
                        for row in data
                    }

                    # Save to persistent cache
                    self._save_cache(marketcap_data)
                    self._marketcap_cache["marketcap"] = marketcap_data
                    self.logger.info(f"Fetched and cached market cap data for {len(marketcap_data)} coins")
                else:
                    self.logger.warning("CoinGecko returned empty data")
                    return None

            except Exception as e:
                self.logger.warning(f"Failed to fetch market cap data: {e}")
                return None

        # Extract base symbol from pair (e.g., "BTC/USDC:USDC" -> "BTC")
        base_symbol = pair.split('/')[0].upper()

        # Handle special cases like kPEPE -> PEPE
        if base_symbol.startswith('K') and len(base_symbol) > 1:
            alt_symbol = base_symbol[1:]  # Try without 'k' prefix
            if alt_symbol in marketcap_data:
                return marketcap_data[alt_symbol]

        return marketcap_data.get(base_symbol)

    def _get_market_cap_bucket(self, market_cap: float | None) -> str:
        """
        Determine market cap bucket based on actual market cap value using configurable thresholds.

        Buckets (configurable via buy_params):
        - blue_chip: >= mcap_blue_chip_threshold
        - large_cap: >= mcap_large_cap_threshold and < mcap_blue_chip_threshold
        - mid_cap: >= mcap_mid_cap_threshold and < mcap_large_cap_threshold
        - degen: < mcap_mid_cap_threshold (also used for unknown coins)

        :param market_cap: Market cap in USD
        :return: Bucket name
        """
        if market_cap is None or market_cap == 0:
            return "degen"  # Treat unknown as degen

        # Convert to billions for easier comparison
        mcap_billions = market_cap / 1_000_000_000

        blue_chip_threshold = self.buy_params.get('mcap_blue_chip_threshold', 50.0)
        large_cap_threshold = self.buy_params.get('mcap_large_cap_threshold', 15.0)
        mid_cap_threshold = self.buy_params.get('mcap_mid_cap_threshold', 1.5)

        # Check thresholds in descending order (guarantees non-overlapping buckets)
        if mcap_billions >= blue_chip_threshold:
            return "blue_chip"
        elif mcap_billions >= large_cap_threshold:
            return "large_cap"
        elif mcap_billions >= mid_cap_threshold:
            return "mid_cap"
        else:
            return "degen"

    def _get_market_cap_multiplier(self, market_cap: float | None) -> float:
        """
        Get position size multiplier based on market cap bucket using configurable parameters.

        :param market_cap: Market cap in USD
        :return: Position size multiplier
        """
        bucket = self._get_market_cap_bucket(market_cap)

        multipliers = {
            'blue_chip': self.buy_params.get('mcap_blue_chip_multiplier', 4.8),
            'large_cap': self.buy_params.get('mcap_large_cap_multiplier', 3.8),
            'mid_cap': self.buy_params.get('mcap_mid_cap_multiplier', 2.9),
            'degen': self.buy_params.get('mcap_degen_multiplier', 1.9),
        }

        return multipliers.get(bucket, multipliers['degen'])

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.

        :param pair: Pair that's currently analyzed
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param proposed_leverage: A leverage proposed by the bot.
        :param max_leverage: Max leverage allowed on this pair
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: "long" or "short" - indicating the direction of the proposed trade
        :return: A leverage amount, which is between 1.0 and max_leverage.
        """
        return 1.0

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
        Market cap VALUE-based position sizing (configurable via buy_params):
        - Uses a fixed base stake from total balance (total_balance / max_open_trades)
        - Applies market cap multiplier based on actual market cap VALUE
        - Respects per-pair concentration cap and available balance
        - Works for both longs and shorts

        :param pair: Pair that's currently analyzed
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param proposed_stake: A stake amount proposed by the bot.
        :param min_stake: Minimal stake size allowed by exchange.
        :param max_stake: Balance available for trading.
        :param leverage: Leverage selected for this trade.
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: 'long' or 'short' - indicating the direction of the proposed trade
        :return: A stake size, which is between min_stake and max_stake.
        """
        if not self.USE_CUSTOM_STAKE:
            return proposed_stake

        per_pair_cap_pct = self.buy_params.get('per_pair_cap_pct', 0.52)

        # Get fixed base stake from total balance (not remaining)
        try:
            wallets = kwargs.get('wallets')
            if wallets:
                total_balance = wallets.get_total_stake_amount()
                max_open_trades = self.config.get('max_open_trades', 10)
                base_stake = total_balance / max_open_trades
            else:
                base_stake = proposed_stake
                total_balance = None
        except Exception as e:
            self.logger.warning(f"{pair}: Wallet access failed, using proposed_stake: {e}")
            base_stake = proposed_stake
            total_balance = None

        # Calculate desired stake with market cap multiplier
        market_cap = self._get_market_cap_value(pair)
        mcap_multiplier = self._get_market_cap_multiplier(market_cap)
        desired_stake = base_stake * mcap_multiplier

        # Apply caps: per-pair concentration, available balance, min stake
        if total_balance:
            desired_stake = min(desired_stake, per_pair_cap_pct * total_balance)

        desired_stake = min(desired_stake, max_stake)

        # Check if there's sufficient balance available
        if max_stake <= 0:
            self.logger.info(f"{pair}: Insufficient balance available (max_stake={max_stake:.2f}), skipping trade")
            return 0.0

        if min_stake and desired_stake < min_stake:
            if max_stake >= min_stake:
                desired_stake = min_stake
            else:
                self.logger.info(f"{pair}: Available balance ({max_stake:.2f}) < minimum stake ({min_stake:.2f}), skipping trade")
                return 0.0

        if not isinstance(desired_stake, (int, float)) or desired_stake <= 0 or np.isnan(desired_stake):
            desired_stake = min(max(proposed_stake, min_stake or 0), max_stake)

        return float(desired_stake)

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
            # Use dedicated short hard stop (independent of the wide base stoploss used for longs)
            base_stop_price = entry_rate * (1 + self.short_hard_stoploss.value)

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
        """Store ATR at entry time for shorts and log detailed entry information with market cap sizing."""
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
            market_cap = self._get_market_cap_value(pair)
            bucket = self._get_market_cap_bucket(market_cap)
            multiplier = self._get_market_cap_multiplier(market_cap)

            self.logger.info(f"ENTRY | {pair} | {side} | amount={amount} | rate={rate} | mcap_bucket={bucket} | multiplier={multiplier} | time={current_time}")

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


class HyperOpt(IHyperOpt):
    def max_open_trades_space(self) -> list[Dimension]:
        """
        Define the max_open_trades optimization space.
        Default is -1 to 10, where -1 means unlimited.
        """
        return [
            Integer(10, 30, name="max_open_trades"),
        ]