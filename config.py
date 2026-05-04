"""Configuration for PSE Signal Alert System."""

import os

# Fallback top 25 PSE stocks (used when API is unreachable)
STOCKS_FALLBACK = [
    "ICT", "BDO", "BPI", "MBT", "URC", "PLUS", "SM", "AC", "JFC", "ALI",
    "SMPH", "MWC", "MYNLD", "MER", "GTCAP", "TEL", "GLO", "SECB", "PGOLD",
    "RLC", "MEG", "AGI", "WLCON", "DMC", "LTG",
]

# Set to True to auto-rank stocks by turnover from the API each day
DYNAMIC_RANKING = True
TOP_N_STOCKS = 25

# Phisix API
API_BASE = "http://phisix-api3.appspot.com"


def get_stocks() -> list[str]:
    """Get the active stock list — dynamic or fallback."""
    if DYNAMIC_RANKING:
        try:
            from ranking import get_dynamic_stocks
            symbols = get_dynamic_stocks(top_n=TOP_N_STOCKS)
            if symbols:
                return symbols
        except Exception:
            pass
    return STOCKS_FALLBACK


# For backward compat — modules that import STOCKS directly get the fallback
STOCKS = STOCKS_FALLBACK

# Strategy parameters (same as crypto bot, will tune via backtest)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
EMA_SHORT = 9
EMA_LONG = 21
RSI_PERIOD = 14
RSI_ENTRY_MIN = 40
RSI_ENTRY_MAX = 60
RSI_EXIT_MAX = 75
STOP_LOSS_PCT = 6.0   # % below entry (tuned via grid search)
TAKE_PROFIT_PCT = 12.0  # % above entry (tuned via grid search)

# Data
TIMEFRAME = "1d"  # "1d" or "4h"
DATA_DIR = "data"  # overridden by set_timeframe()
DATA_DIR_1D = "data"
DATA_DIR_4H = os.path.join("data", "4h")
LOOKBACK_DAYS = 730  # 2 years of history for backtest


def set_timeframe(tf: str):
    """Switch timeframe — updates DATA_DIR and filter criteria."""
    global TIMEFRAME, DATA_DIR, MIN_TRADES
    tf = tf.lower()
    if tf in ("4h", "4H"):
        TIMEFRAME = "4h"
        DATA_DIR = DATA_DIR_4H
        MIN_TRADES = 5
    else:
        TIMEFRAME = "1d"
        DATA_DIR = DATA_DIR_1D
        MIN_TRADES = 5

# Stock filtering criteria (from backtest)
MIN_TRADES = 5
MIN_WIN_RATE = 50.0  # %
MIN_TOTAL_RETURN = 0.0  # %
