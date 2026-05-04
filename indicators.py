"""Technical indicators: MACD, RSI, EMA."""

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def add_indicators(df: pd.DataFrame, fast=12, slow=26, signal_period=9,
                   ema_short=9, ema_long=21, rsi_period=14) -> pd.DataFrame:
    """Add all indicators to a DataFrame with 'close' column."""
    df = df.copy()
    df["ema_short"] = ema(df["close"], ema_short)
    df["ema_long"] = ema(df["close"], ema_long)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(df["close"], fast, slow, signal_period)
    df["rsi"] = rsi(df["close"], rsi_period)
    return df
