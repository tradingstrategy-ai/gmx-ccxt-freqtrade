# IchiV2_LS_1h_Merged - Dual Long/Short Ichimoku Strategy (1h timeframe)
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
from freqtrade.strategy import informative, DecimalParameter, IntParameter
from freqtrade.strategy.strategy_helper import stoploss_from_absolute
import logging
import json
from freqtrade.optimize.space import SKDecimal 

class IchiV2_LS_Live(IStrategy):
    """
    IchiV2_LS_Live - for live config bots

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


    with fixed stoploss OR atr stoploss

                                                          EXIT REASON STATS                                                       
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│          sar_exit_long │   409 │         4.51 │         422.410 │       422.41 │  2 days, 2:21:00 │  234     0   175  57.2 │
│   tp_velocity_achieved │   111 │        13.31 │         357.842 │       357.84 │ 2 days, 11:51:00 │  103     0     8  92.8 │
│     tp_rsi_4h_oversold │    89 │        14.26 │         295.409 │       295.41 │ 6 days, 10:05:00 │   77     0    12  86.5 │
│ senkou_a_4h_exit_short │   198 │         2.62 │         145.497 │        145.5 │  4 days, 1:47:00 │  142     0    56  71.7 │
│             force_exit │     4 │         1.78 │           4.177 │         4.18 │ 7 days, 19:15:00 │    2     0     2  50.0 │
│  senkou_a_4h_exit_long │    56 │        -0.03 │          -0.146 │        -0.15 │         17:39:00 │   23     0    33  41.1 │
│     trailing_stop_loss │   114 │        -3.37 │         -84.801 │        -84.8 │  2 days, 1:22:00 │    0     0   114     0 │
│              stop_loss │   637 │         -4.0 │        -633.972 │      -633.97 │   1 day, 0:24:00 │    0     0   637     0 │
│                  TOTAL │  1618 │         1.35 │         506.416 │       506.42 │  2 days, 3:26:00 │  581     0  1037  35.9 │
└────────────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                               MIXED TAG STATS                                                               
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃            Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  long_entry │          sar_exit_long │    409 │         4.51 │         422.410 │       422.41 │  2 days, 2:21:00 │  234     0   175  57.2 │
│ short_entry │   tp_velocity_achieved │    111 │        13.31 │         357.842 │       357.84 │ 2 days, 11:51:00 │  103     0     8  92.8 │
│ short_entry │     tp_rsi_4h_oversold │     89 │        14.26 │         295.409 │       295.41 │ 6 days, 10:05:00 │   77     0    12  86.5 │
│ short_entry │ senkou_a_4h_exit_short │    198 │         2.62 │         145.497 │        145.5 │  4 days, 1:47:00 │  142     0    56  71.7 │
│ short_entry │             force_exit │      4 │         1.78 │           4.177 │         4.18 │ 7 days, 19:15:00 │    2     0     2  50.0 │
│  long_entry │  senkou_a_4h_exit_long │     56 │        -0.03 │          -0.146 │        -0.15 │         17:39:00 │   23     0    33  41.1 │
│ short_entry │     trailing_stop_loss │    114 │        -3.37 │         -84.801 │        -84.8 │  2 days, 1:22:00 │    0     0   114     0 │
│  long_entry │              stop_loss │    240 │        -4.51 │        -275.871 │      -275.87 │         12:07:00 │    0     0   240     0 │
│ short_entry │              stop_loss │    397 │        -3.69 │        -358.101 │       -358.1 │   1 day, 7:49:00 │    0     0   397     0 │
│       TOTAL │                        │   1618 │         1.35 │         506.416 │       506.42 │  2 days, 3:26:00 │  581     0  1037  35.9 │
└─────────────┴────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2024-01-01 00:00:00             │
│ Backtesting to                │ 2025-12-22 09:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 1618 / 2.24                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 606.416 USDT                    │
│ Absolute profit               │ 506.416 USDT                    │
│ Total profit %                │ 506.42%                         │
│ CAGR %                        │ 149.04%                         │
│ Sortino                       │ 5.65                            │
│ Sharpe                        │ 2.32                            │
│ Calmar                        │ 13.09                           │
│ SQN                           │ 4.60                            │
│ Profit factor                 │ 1.61                            │
│ Expectancy (Ratio)            │ 0.31 (0.39)                     │
│ Avg. daily profit             │ 0.702 USDT                      │
│ Avg. stake amount             │ 24.302 USDT                     │
│ Total trade volume            │ 78439.111 USDT                  │
│                               │                                 │
│ Long / Short trades           │ 705 / 913                       │
│ Long / Short profit %         │ 146.39% / 360.02%               │
│ Long / Short profit USDT      │ 146.393 / 360.024               │
│                               │                                 │
│ Best Pair                     │ MOODENG/USDT:USDT 77.61%        │
│ Worst Pair                    │ BNB/USDT:USDT -11.45%           │
│ Best trade                    │ MOODENG/USDT:USDT 196.35%       │
│ Worst trade                   │ ZEC/USDT:USDT -4.83%            │
│ Best day                      │ 61.65 USDT                      │
│ Worst day                     │ -16.576 USDT                    │
│ Days win/draw/lose            │ 206 / 174 / 341                 │
│ Min/Max/Avg. Duration Winners │ 0d 01:00 / 30d 23:00 / 3d 18:25 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 18d 10:00 / 1d 05:35 │
│ Max Consecutive Wins / Loss   │ 17 / 23                         │
│ Rejected Entry signals        │ 527                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 95.195 USDT                     │
│ Max balance                   │ 606.569 USDT                    │
│ Max % of account underwater   │ 13.88%                          │
│ Absolute drawdown             │ 59.485 USDT (11.39%)            │
│ Drawdown duration             │ 50 days 01:00:00                │
│ Profit at drawdown start      │ 422.406 USDT                    │
│ Profit at drawdown end        │ 362.921 USDT                    │
│ Drawdown start                │ 2025-08-17 16:00:00             │
│ Drawdown end                  │ 2025-10-06 17:00:00             │
│ Market change                 │ 19.91%                          │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2024-01-01 00:00:00 -> 2025-12-22 09:00:00 | Max open trades : 10
                                                              STRATEGY SUMMARY                                                              
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃       Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃            Drawdown ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ IchiV2_LS_Live │   1618 │         1.35 │         506.416 │       506.42 │ 2 days, 3:26:00 │  581     0  1037  35.9 │ 59.485 USDT  11.39% │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴─────────────────────┘


with ATR stoploss taking precedence over fixed stoploss
                                                  ENTER TAG STATS                                                   
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃ Entries ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ short_entry │     836 │         1.83 │         421.827 │       421.83 │ 3 days, 0:10:00 │  332     0   504  39.7 │
│  long_entry │     699 │          1.1 │         140.321 │       140.32 │ 1 day, 10:47:00 │  257     0   442  36.8 │
│       TOTAL │    1535 │          1.5 │         562.147 │       562.15 │ 2 days, 7:08:00 │  589     0   946  38.4 │
└─────────────┴─────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┘
                                                      EXIT REASON STATS                                                       
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│          sar_exit_long │   408 │         4.51 │         405.835 │       405.83 │  2 days, 2:14:00 │  234     0   174  57.4 │
│   tp_velocity_achieved │   115 │        13.29 │         373.450 │       373.45 │ 2 days, 19:14:00 │  106     0     9  92.2 │
│     tp_rsi_4h_oversold │    89 │        14.21 │         291.895 │        291.9 │ 6 days, 11:44:00 │   77     0    12  86.5 │
│ senkou_a_4h_exit_short │   210 │         2.36 │         144.700 │        144.7 │  4 days, 7:43:00 │  147     0    63  70.0 │
│             force_exit │     3 │         3.71 │           6.948 │         6.95 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  senkou_a_4h_exit_long │    54 │         -0.0 │           0.241 │         0.24 │         17:44:00 │   23     0    31  42.6 │
│     trailing_stop_loss │   112 │        -3.85 │         -89.739 │       -89.74 │  1 day, 21:00:00 │    0     0   112     0 │
│              stop_loss │   544 │        -4.42 │        -571.183 │      -571.18 │   1 day, 2:22:00 │    0     0   544     0 │
│                  TOTAL │  1535 │          1.5 │         562.147 │       562.15 │  2 days, 7:08:00 │  589     0   946  38.4 │
└────────────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                               MIXED TAG STATS                                                               
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃            Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  long_entry │          sar_exit_long │    408 │         4.51 │         405.835 │       405.83 │  2 days, 2:14:00 │  234     0   174  57.4 │
│ short_entry │   tp_velocity_achieved │    115 │        13.29 │         373.450 │       373.45 │ 2 days, 19:14:00 │  106     0     9  92.2 │
│ short_entry │     tp_rsi_4h_oversold │     89 │        14.21 │         291.895 │        291.9 │ 6 days, 11:44:00 │   77     0    12  86.5 │
│ short_entry │ senkou_a_4h_exit_short │    210 │         2.36 │         144.700 │        144.7 │  4 days, 7:43:00 │  147     0    63  70.0 │
│ short_entry │             force_exit │      3 │         3.71 │           6.948 │         6.95 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  long_entry │  senkou_a_4h_exit_long │     54 │         -0.0 │           0.241 │         0.24 │         17:44:00 │   23     0    31  42.6 │
│ short_entry │     trailing_stop_loss │    112 │        -3.85 │         -89.739 │       -89.74 │  1 day, 21:00:00 │    0     0   112     0 │
│  long_entry │              stop_loss │    237 │        -4.51 │        -265.755 │      -265.75 │         12:04:00 │    0     0   237     0 │
│ short_entry │              stop_loss │    307 │        -4.36 │        -305.428 │      -305.43 │  1 day, 13:25:00 │    0     0   307     0 │
│       TOTAL │                        │   1535 │          1.5 │         562.147 │       562.15 │  2 days, 7:08:00 │  589     0   946  38.4 │
└─────────────┴────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2024-01-01 00:00:00             │
│ Backtesting to                │ 2025-12-22 09:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 1535 / 2.13                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 662.147 USDT                    │
│ Absolute profit               │ 562.147 USDT                    │
│ Total profit %                │ 562.15%                         │
│ CAGR %                        │ 160.38%                         │
│ Sortino                       │ 6.74                            │
│ Sharpe                        │ 2.58                            │
│ Calmar                        │ 17.61                           │
│ SQN                           │ 5.22                            │
│ Profit factor                 │ 1.73                            │
│ Expectancy (Ratio)            │ 0.37 (0.45)                     │
│ Avg. daily profit             │ 0.78 USDT                       │
│ Avg. stake amount             │ 23.721 USDT                     │
│ Total trade volume            │ 72550.583 USDT                  │
│                               │                                 │
│ Long / Short trades           │ 699 / 836                       │
│ Long / Short profit %         │ 140.32% / 421.83%               │
│ Long / Short profit USDT      │ 140.321 / 421.827               │
│                               │                                 │
│ Best Pair                     │ MOODENG/USDT:USDT 72.68%        │
│ Worst Pair                    │ BNB/USDT:USDT -14.21%           │
│ Best trade                    │ MOODENG/USDT:USDT 196.35%       │
│ Worst trade                   │ ZEC/USDT:USDT -17.13%           │
│ Best day                      │ 59.789 USDT                     │
│ Worst day                     │ -15.851 USDT                    │
│ Days win/draw/lose            │ 206 / 186 / 329                 │
│ Min/Max/Avg. Duration Winners │ 0d 01:00 / 30d 23:00 / 3d 21:56 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 14d 13:00 / 1d 06:59 │
│ Max Consecutive Wins / Loss   │ 17 / 22                         │
│ Rejected Entry signals        │ 561                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 94.055 USDT                     │
│ Max balance                   │ 662.147 USDT                    │
│ Max % of account underwater   │ 10.78%                          │
│ Absolute drawdown             │ 45.243 USDT (9.11%)             │
│ Drawdown duration             │ 50 days 01:00:00                │
│ Profit at drawdown start      │ 396.793 USDT                    │
│ Profit at drawdown end        │ 351.551 USDT                    │
│ Drawdown start                │ 2025-08-17 16:00:00             │
│ Drawdown end                  │ 2025-10-06 17:00:00             │
│ Market change                 │ 19.39%                          │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2024-01-01 00:00:00 -> 2025-12-22 09:00:00 | Max open trades : 10
                                                             STRATEGY SUMMARY                                                              
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃       Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃           Drawdown ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ IchiV2_LS_Live │   1535 │         1.50 │         562.147 │       562.15 │ 2 days, 7:08:00 │  589     0   946  38.4 │ 45.243 USDT  9.11% │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴────────────────────┘
 
 with fixed stoploss taking precedence, new change

 Result for strategy IchiV2_LS_Live
                                                    BACKTESTING REPORT                                                     
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃               Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  MOODENG/USDT:USDT │     29 │        12.25 │          77.608 │        77.61 │   1 day, 3:33:00 │   12     0    17  41.4 │
│      SUI/USDT:USDT │     64 │         3.58 │          43.847 │        43.85 │  2 days, 0:28:00 │   31     0    33  48.4 │
│     HYPE/USDT:USDT │     34 │         2.94 │          43.358 │        43.36 │  2 days, 6:14:00 │   15     0    19  44.1 │
│     ZORA/USDT:USDT │     16 │         3.65 │          30.220 │        30.22 │  1 day, 13:30:00 │    6     0    10  37.5 │
│     CAKE/USDT:USDT │     41 │         2.47 │          28.232 │        28.23 │  2 days, 5:03:00 │   17     0    24  41.5 │
│      ARB/USDT:USDT │     38 │         2.75 │          26.904 │         26.9 │ 2 days, 12:28:00 │   17     0    21  44.7 │
│     DOGE/USDT:USDT │     49 │         1.97 │          26.635 │        26.64 │ 2 days, 13:00:00 │   24     0    25  49.0 │
│ FARTCOIN/USDT:USDT │     34 │         2.47 │          26.301 │         26.3 │         17:26:00 │   13     0    21  38.2 │
│      ENA/USDT:USDT │     49 │         1.06 │          25.548 │        25.55 │   1 day, 7:04:00 │   16     0    33  32.7 │
│     NEAR/USDT:USDT │     44 │         3.75 │          23.953 │        23.95 │  2 days, 5:37:00 │   24     0    20  54.5 │
│      CRV/USDT:USDT │     52 │         2.45 │          22.689 │        22.69 │  3 days, 4:55:00 │   18     0    34  34.6 │
│      ZEC/USDT:USDT │     34 │         1.63 │          20.385 │        20.38 │  1 day, 22:02:00 │   14     0    20  41.2 │
│    PENGU/USDT:USDT │     23 │         1.96 │          19.468 │        19.47 │  1 day, 13:57:00 │   10     0    13  43.5 │
│      MET/USDT:USDT │      2 │        17.66 │          17.816 │        17.82 │   1 day, 5:30:00 │    2     0     0   100 │
│     AAVE/USDT:USDT │     67 │        -0.16 │          16.168 │        16.17 │  1 day, 20:29:00 │   17     0    50  25.4 │
│      XLM/USDT:USDT │     53 │         1.53 │          15.744 │        15.74 │ 2 days, 12:32:00 │   21     0    32  39.6 │
│       OP/USDT:USDT │     44 │         0.34 │          14.819 │        14.82 │  1 day, 11:22:00 │   14     0    30  31.8 │
│      INJ/USDT:USDT │     49 │         0.85 │          14.625 │        14.63 │ 2 days, 17:04:00 │   13     0    36  26.5 │
│      TON/USDT:USDT │     49 │         0.72 │          14.438 │        14.44 │  2 days, 2:51:00 │   16     0    33  32.7 │
│     ONDO/USDT:USDT │     57 │         1.08 │          14.092 │        14.09 │  1 day, 20:19:00 │   19     0    38  33.3 │
│     AVAX/USDT:USDT │     20 │         2.59 │          13.753 │        13.75 │  2 days, 7:06:00 │    8     0    12  40.0 │
│      ADA/USDT:USDT │     42 │         1.05 │           8.536 │         8.54 │ 2 days, 23:30:00 │   14     0    28  33.3 │
│      BCH/USDT:USDT │     53 │         0.65 │           7.516 │         7.52 │ 2 days, 18:24:00 │   21     0    32  39.6 │
│     LINK/USDT:USDT │     44 │         1.62 │           6.665 │         6.66 │ 2 days, 10:20:00 │   21     0    23  47.7 │
│      ETH/USDT:USDT │     16 │         2.65 │           5.203 │          5.2 │  1 day, 19:22:00 │    7     0     9  43.8 │
│       0G/USDT:USDT │      2 │         3.44 │           4.060 │         4.06 │          3:30:00 │    1     0     1  50.0 │
│     WLFI/USDT:USDT │      5 │         0.79 │           1.598 │          1.6 │ 4 days, 16:36:00 │    1     0     4  20.0 │
│      DOT/USDT:USDT │     37 │         1.72 │           1.511 │         1.51 │ 2 days, 22:02:00 │   16     0    21  43.2 │
│      BTC/USDT:USDT │     49 │          0.8 │           0.810 │         0.81 │  3 days, 8:01:00 │   19     0    30  38.8 │
│      SOL/USDT:USDT │      0 │          0.0 │           0.000 │          0.0 │             0:00 │    0     0     0     0 │
│     STBL/USDT:USDT │      2 │         0.24 │          -0.264 │        -0.26 │          4:30:00 │    1     0     1  50.0 │
│    LINEA/USDT:USDT │      4 │        -0.18 │          -0.297 │         -0.3 │          3:30:00 │    1     0     3  25.0 │
│      UNI/USDT:USDT │     49 │        -0.58 │          -0.467 │        -0.47 │  2 days, 9:04:00 │   13     0    36  26.5 │
│      SEI/USDT:USDT │     53 │         1.68 │          -1.037 │        -1.04 │  1 day, 20:32:00 │   20     0    33  37.7 │
│      WLD/USDT:USDT │     37 │         0.39 │          -1.070 │        -1.07 │  1 day, 19:28:00 │   12     0    25  32.4 │
│     AVNT/USDT:USDT │      1 │         -4.5 │          -1.927 │        -1.93 │          2:00:00 │    0     0     1     0 │
│    TRUMP/USDT:USDT │     18 │         0.08 │          -2.095 │        -2.09 │   1 day, 5:33:00 │    7     0    11  38.9 │
│      APT/USDT:USDT │     52 │         0.24 │          -2.190 │        -2.19 │  2 days, 1:52:00 │   17     0    35  32.7 │
│     PUMP/USDT:USDT │     18 │        -0.24 │          -2.770 │        -2.77 │         22:47:00 │    5     0    13  27.8 │
│      LTC/USDT:USDT │     69 │        -0.22 │          -2.838 │        -2.84 │  2 days, 1:58:00 │   16     0    53  23.2 │
│    ASTER/USDT:USDT │      5 │        -1.47 │          -2.902 │         -2.9 │          7:00:00 │    1     0     4  20.0 │
│      TRX/USDT:USDT │     52 │        -0.23 │          -4.042 │        -4.04 │  1 day, 21:27:00 │   16     0    36  30.8 │
│     PYTH/USDT:USDT │     52 │         0.89 │          -4.341 │        -4.34 │  1 day, 16:27:00 │   15     0    37  28.8 │
│      XPL/USDT:USDT │      3 │        -4.46 │          -6.166 │        -6.17 │ 2 days, 12:40:00 │    0     0     3     0 │
│      XRP/USDT:USDT │     47 │        -0.59 │          -6.269 │        -6.27 │ 2 days, 19:20:00 │   13     0    34  27.7 │
│      SKY/USDT:USDT │      7 │        -2.29 │          -8.476 │        -8.48 │  1 day, 20:43:00 │    1     0     6  14.3 │
│      BNB/USDT:USDT │     54 │        -0.53 │         -11.449 │       -11.45 │  2 days, 2:29:00 │   17     0    37  31.5 │
│              TOTAL │   1619 │         1.36 │         513.901 │        513.9 │  2 days, 3:29:00 │  582     0  1037  35.9 │
└────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                LEFT OPEN TRADES REPORT                                                
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃           Pair ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  CRV/USDT:USDT │      1 │         9.26 │           5.298 │          5.3 │ 11 days, 8:00:00 │    1     0     0   100 │
│ ZORA/USDT:USDT │      1 │         4.22 │           2.488 │         2.49 │  1 day, 14:00:00 │    1     0     0   100 │
│  BTC/USDT:USDT │      1 │        -2.34 │          -1.224 │        -1.22 │ 4 days, 17:00:00 │    0     0     1     0 │
│          TOTAL │      3 │         3.71 │           6.562 │         6.56 │ 5 days, 21:00:00 │    2     0     1  66.7 │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                   ENTER TAG STATS                                                   
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃ Entries ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ short_entry │     914 │         1.57 │         367.508 │       367.51 │ 2 days, 16:24:00 │  325     0   589  35.6 │
│  long_entry │     705 │         1.08 │         146.393 │       146.39 │  1 day, 10:44:00 │  257     0   448  36.5 │
│       TOTAL │    1619 │         1.36 │         513.901 │        513.9 │  2 days, 3:29:00 │  582     0  1037  35.9 │
└─────────────┴─────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                      EXIT REASON STATS                                                       
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│          sar_exit_long │   409 │         4.51 │         422.410 │       422.41 │  2 days, 2:21:00 │  234     0   175  57.2 │
│   tp_velocity_achieved │   112 │        13.28 │         363.534 │       363.53 │ 2 days, 14:15:00 │  104     0     8  92.9 │
│     tp_rsi_4h_oversold │    89 │        14.26 │         295.409 │       295.41 │ 6 days, 10:05:00 │   77     0    12  86.5 │
│ senkou_a_4h_exit_short │   198 │         2.62 │         145.497 │        145.5 │  4 days, 1:47:00 │  142     0    56  71.7 │
│             force_exit │     3 │         3.71 │           6.562 │         6.56 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  senkou_a_4h_exit_long │    56 │        -0.03 │          -0.146 │        -0.15 │         17:39:00 │   23     0    33  41.1 │
│     trailing_stop_loss │   114 │        -3.37 │         -84.801 │        -84.8 │  2 days, 1:22:00 │    0     0   114     0 │
│              stop_loss │   638 │        -3.99 │        -634.565 │      -634.56 │   1 day, 0:35:00 │    0     0   638     0 │
│                  TOTAL │  1619 │         1.36 │         513.901 │        513.9 │  2 days, 3:29:00 │  582     0  1037  35.9 │
└────────────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                               MIXED TAG STATS                                                               
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃            Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  long_entry │          sar_exit_long │    409 │         4.51 │         422.410 │       422.41 │  2 days, 2:21:00 │  234     0   175  57.2 │
│ short_entry │   tp_velocity_achieved │    112 │        13.28 │         363.534 │       363.53 │ 2 days, 14:15:00 │  104     0     8  92.9 │
│ short_entry │     tp_rsi_4h_oversold │     89 │        14.26 │         295.409 │       295.41 │ 6 days, 10:05:00 │   77     0    12  86.5 │
│ short_entry │ senkou_a_4h_exit_short │    198 │         2.62 │         145.497 │        145.5 │  4 days, 1:47:00 │  142     0    56  71.7 │
│ short_entry │             force_exit │      3 │         3.71 │           6.562 │         6.56 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  long_entry │  senkou_a_4h_exit_long │     56 │        -0.03 │          -0.146 │        -0.15 │         17:39:00 │   23     0    33  41.1 │
│ short_entry │     trailing_stop_loss │    114 │        -3.37 │         -84.801 │        -84.8 │  2 days, 1:22:00 │    0     0   114     0 │
│  long_entry │              stop_loss │    240 │        -4.51 │        -275.871 │      -275.87 │         12:07:00 │    0     0   240     0 │
│ short_entry │              stop_loss │    398 │        -3.69 │        -358.694 │      -358.69 │   1 day, 8:05:00 │    0     0   398     0 │
│       TOTAL │                        │   1619 │         1.36 │         513.901 │        513.9 │  2 days, 3:29:00 │  582     0  1037  35.9 │
└─────────────┴────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2024-01-01 00:00:00             │
│ Backtesting to                │ 2025-12-22 09:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 1619 / 2.25                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 613.901 USDT                    │
│ Absolute profit               │ 513.901 USDT                    │
│ Total profit %                │ 513.90%                         │
│ CAGR %                        │ 150.59%                         │
│ Sortino                       │ 5.74                            │
│ Sharpe                        │ 2.35                            │
│ Calmar                        │ 13.23                           │
│ SQN                           │ 4.66                            │
│ Profit factor                 │ 1.62                            │
│ Expectancy (Ratio)            │ 0.32 (0.40)                     │
│ Avg. daily profit             │ 0.713 USDT                      │
│ Avg. stake amount             │ 24.325 USDT                     │
│ Total trade volume            │ 78553.074 USDT                  │
│                               │                                 │
│ Long / Short trades           │ 705 / 914                       │
│ Long / Short profit %         │ 146.39% / 367.51%               │
│ Long / Short profit USDT      │ 146.393 / 367.508               │
│                               │                                 │
│ Best Pair                     │ MOODENG/USDT:USDT 77.61%        │
│ Worst Pair                    │ BNB/USDT:USDT -11.45%           │
│ Best trade                    │ MOODENG/USDT:USDT 196.35%       │
│ Worst trade                   │ ZEC/USDT:USDT -4.83%            │
│ Best day                      │ 61.65 USDT                      │
│ Worst day                     │ -16.576 USDT                    │
│ Days win/draw/lose            │ 206 / 174 / 341                 │
│ Min/Max/Avg. Duration Winners │ 0d 01:00 / 30d 23:00 / 3d 18:48 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 18d 10:00 / 1d 05:25 │
│ Max Consecutive Wins / Loss   │ 17 / 23                         │
│ Rejected Entry signals        │ 527                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 95.195 USDT                     │
│ Max balance                   │ 613.901 USDT                    │
│ Max % of account underwater   │ 13.88%                          │
│ Absolute drawdown             │ 59.485 USDT (11.39%)            │
│ Drawdown duration             │ 50 days 01:00:00                │
│ Profit at drawdown start      │ 422.406 USDT                    │
│ Profit at drawdown end        │ 362.921 USDT                    │
│ Drawdown start                │ 2025-08-17 16:00:00             │
│ Drawdown end                  │ 2025-10-06 17:00:00             │
│ Market change                 │ 19.63%                          │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2024-01-01 00:00:00 -> 2025-12-22 09:00:00 | Max open trades : 10
                                                              STRATEGY SUMMARY                                                              
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃       Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃            Drawdown ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ IchiV2_LS_Live │   1619 │         1.36 │         513.901 │        513.9 │ 2 days, 3:29:00 │  582     0  1037  35.9 │ 59.485 USDT  11.39% │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴─────────────────────┘
 


 testing stoloss hyperopt. Before hyperopt as is with stoploss proiritization of 4.5%

 since 2020 so we have a long backtest

                                                     EXIT REASON STATS                                                       
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│          sar_exit_long │   887 │         3.69 │         765.654 │       765.65 │  2 days, 0:34:00 │  498     0   389  56.1 │
│   tp_velocity_achieved │   177 │         12.0 │         593.946 │       593.95 │  2 days, 8:59:00 │  162     0    15  91.5 │
│     tp_rsi_4h_oversold │   160 │        13.65 │         536.905 │        536.9 │ 6 days, 13:46:00 │  144     0    16  90.0 │
│ senkou_a_4h_exit_short │   402 │         2.14 │         252.681 │       252.68 │ 3 days, 23:27:00 │  282     0   120  70.1 │
│             force_exit │     3 │         3.71 │           9.549 │         9.55 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  senkou_a_4h_exit_long │    98 │        -0.16 │          -2.261 │        -2.26 │         18:04:00 │   40     0    58  40.8 │
│     trailing_stop_loss │   266 │        -3.25 │        -171.717 │      -171.72 │  1 day, 23:40:00 │    2     0   264   0.8 │
│              stop_loss │  1233 │         -4.0 │       -1186.455 │     -1186.46 │   1 day, 1:15:00 │    0     0  1233     0 │
│                  TOTAL │  3226 │         0.82 │         798.301 │        798.3 │  2 days, 2:27:00 │ 1130     0  2096  35.0 │
└────────────────────────┴───────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                                                               MIXED TAG STATS                                                               
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   Enter Tag ┃            Exit Reason ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃     Avg Duration ┃  Win  Draw  Loss  Win% ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│  long_entry │          sar_exit_long │    887 │         3.69 │         765.654 │       765.65 │  2 days, 0:34:00 │  498     0   389  56.1 │
│ short_entry │   tp_velocity_achieved │    177 │         12.0 │         593.946 │       593.95 │  2 days, 8:59:00 │  162     0    15  91.5 │
│ short_entry │     tp_rsi_4h_oversold │    160 │        13.65 │         536.905 │        536.9 │ 6 days, 13:46:00 │  144     0    16  90.0 │
│ short_entry │ senkou_a_4h_exit_short │    402 │         2.14 │         252.681 │       252.68 │ 3 days, 23:27:00 │  282     0   120  70.1 │
│ short_entry │             force_exit │      3 │         3.71 │           9.549 │         9.55 │ 5 days, 21:00:00 │    2     0     1  66.7 │
│  long_entry │  senkou_a_4h_exit_long │     98 │        -0.16 │          -2.261 │        -2.26 │         18:04:00 │   40     0    58  40.8 │
│ short_entry │     trailing_stop_loss │    266 │        -3.25 │        -171.717 │      -171.72 │  1 day, 23:40:00 │    2     0   264   0.8 │
│  long_entry │              stop_loss │    473 │        -4.58 │        -521.860 │      -521.86 │         13:41:00 │    0     0   473     0 │
│ short_entry │              stop_loss │    760 │        -3.63 │        -664.595 │       -664.6 │   1 day, 8:26:00 │    0     0   760     0 │
│       TOTAL │                        │   3226 │         0.82 │         798.301 │        798.3 │  2 days, 2:27:00 │ 1130     0  2096  35.0 │
└─────────────┴────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────────┴────────────────────────┘
                          SUMMARY METRICS                          
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                        ┃ Value                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from              │ 2020-10-21 20:00:00             │
│ Backtesting to                │ 2025-12-22 09:00:00             │
│ Trading Mode                  │ Isolated Futures                │
│ Max open trades               │ 10                              │
│                               │                                 │
│ Total/Daily Avg Trades        │ 3226 / 1.71                     │
│ Starting balance              │ 100 USDT                        │
│ Final balance                 │ 898.301 USDT                    │
│ Absolute profit               │ 798.301 USDT                    │
│ Total profit %                │ 798.30%                         │
│ CAGR %                        │ 52.90%                          │
│ Sortino                       │ 3.21                            │
│ Sharpe                        │ 1.51                            │
│ Calmar                        │ 4.57                            │
│ SQN                           │ 4.85                            │
│ Profit factor                 │ 1.51                            │
│ Expectancy (Ratio)            │ 0.25 (0.33)                     │
│ Avg. daily profit             │ 0.423 USDT                      │
│ Avg. stake amount             │ 23.371 USDT                     │
│ Total trade volume            │ 150496.364 USDT                 │
│                               │                                 │
│ Long / Short trades           │ 1458 / 1768                     │
│ Long / Short profit %         │ 241.53% / 556.77%               │
│ Long / Short profit USDT      │ 241.533 / 556.769               │
│                               │                                 │
│ Best Pair                     │ MOODENG/USDT:USDT 108.98%       │
│ Worst Pair                    │ BNB/USDT:USDT -13.66%           │
│ Best trade                    │ MOODENG/USDT:USDT 196.35%       │
│ Worst trade                   │ NEAR/USDT:USDT -26.36%          │
│ Best day                      │ 89.728 USDT                     │
│ Worst day                     │ -25.377 USDT                    │
│ Days win/draw/lose            │ 451 / 628 / 809                 │
│ Min/Max/Avg. Duration Winners │ 0d 00:00 / 30d 23:00 / 3d 15:24 │
│ Min/Max/Avg. Duration Losers  │ 0d 00:00 / 18d 10:00 / 1d 06:32 │
│ Max Consecutive Wins / Loss   │ 17 / 23                         │
│ Rejected Entry signals        │ 612                             │
│ Entry/Exit Timeouts           │ 0 / 0                           │
│                               │                                 │
│ Min balance                   │ 91.741 USDT                     │
│ Max balance                   │ 898.301 USDT                    │
│ Max % of account underwater   │ 22.30%                          │
│ Absolute drawdown             │ 88.712 USDT (11.58%)            │
│ Drawdown duration             │ 24 days 11:00:00                │
│ Profit at drawdown start      │ 666.306 USDT                    │
│ Profit at drawdown end        │ 577.594 USDT                    │
│ Drawdown start                │ 2025-10-17 16:00:00             │
│ Drawdown end                  │ 2025-11-11 03:00:00             │
│ Market change                 │ 362.53%                         │
└───────────────────────────────┴─────────────────────────────────┘

Backtested 2020-10-21 20:00:00 -> 2025-12-22 09:00:00 | Max open trades : 10
                                                              STRATEGY SUMMARY                                                              
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃       Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃    Avg Duration ┃  Win  Draw  Loss  Win% ┃            Drawdown ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ IchiV2_LS_Live │   3226 │         0.82 │         798.301 │        798.3 │ 2 days, 2:27:00 │ 1130     0  2096  35.0 │ 88.712 USDT  11.58% │
└────────────────┴────────┴──────────────┴─────────────────┴──────────────┴─────────────────┴────────────────────────┴─────────────────────┘

 
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
    startup_candle_count = 500
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
        ATR-based stop loss for SHORTS only.
        Returns the TIGHTER of ATR-based or base stoploss.
        """
        if not trade.is_short:
            return None

        entry_atr = trade.get_custom_data(key='entry_atr')

        if entry_atr is None:
            custom_info_pair = self.custom_info.get(pair)
            if custom_info_pair is not None:
                try:
                    entry_candle = custom_info_pair[custom_info_pair.index <= trade.open_date_utc]
                    if not entry_candle.empty:
                        entry_atr = entry_candle.iloc[-1]['atr']
                        if pd.isna(entry_atr):
                            return None
                    else:
                        return None
                except (KeyError, IndexError):
                    return None
            else:
                return None

        entry_rate = trade.open_rate
        atr_distance = self.atr_stop_multiplier.value * float(entry_atr)

        atr_stop_price = entry_rate + atr_distance
        fixed_stop_price = entry_rate * (1 + abs(self.stoploss))
        
        # Use the TIGHTER stop loss between atr and fixed stoploss
        final_stop_price = min(atr_stop_price, fixed_stop_price)
        
        # Convert absolute price to stoploss distance using Freqtrade utility
        return stoploss_from_absolute(
            stop_rate=final_stop_price,
            current_rate=current_rate,
            is_short=trade.is_short,
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
        custom_info_pair = self.custom_info.get(pair)
        if custom_info_pair is None:
            return None

        current_mode = self.config['runmode']
        is_trading_mode = current_mode in (RunMode.LIVE, RunMode.DRY_RUN)

        try:
            completed_candles = custom_info_pair.loc[custom_info_pair.index < current_time]
            if completed_candles.empty:
                return None

            last_row = completed_candles.iloc[-1]
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
        custom_info_pair = self.custom_info.get(pair)

        # Store ATR for shorts
        if trade is not None and side == 'short' and custom_info_pair is not None:
            try:
                entry_candles = custom_info_pair[custom_info_pair.index <= current_time]
                if not entry_candles.empty:
                    entry_row = entry_candles.iloc[-1]
                    entry_atr = entry_row.get('atr')
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

    def _add_ichimoku(self, df: DataFrame) -> None:
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