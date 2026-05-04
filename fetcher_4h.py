"""Fetch 4H candle data from TradingView for PSE stocks."""

import os
import time

import pandas as pd
from tvDatafeed import TvDatafeed, Interval

from config import STOCKS_FALLBACK, get_stocks

DATA_DIR_4H = os.path.join("data", "4h")


def fetch_4h(symbol: str, n_bars: int = 5000, tv: TvDatafeed = None) -> pd.DataFrame:
    """Fetch 4H OHLCV data for a single PSE stock from TradingView."""
    if tv is None:
        tv = TvDatafeed()
    try:
        df = tv.get_hist(symbol=symbol, exchange="PSE",
                         interval=Interval.in_4_hour, n_bars=n_bars)
        if df is None or len(df) == 0:
            print(f"  {symbol}: no data returned")
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={"datetime": "date"})
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  {symbol}: error - {e}")
        return pd.DataFrame()


def fetch_all_4h(symbols: list[str] = None, n_bars: int = 5000):
    """Fetch 4H data for all stocks and save to CSV."""
    if symbols is None:
        symbols = get_stocks()

    os.makedirs(DATA_DIR_4H, exist_ok=True)
    tv = TvDatafeed()

    success = 0
    for i, sym in enumerate(symbols):
        print(f"  [{i+1}/{len(symbols)}] {sym}...", end=" ")
        df = fetch_4h(sym, n_bars=n_bars, tv=tv)
        if len(df) > 0:
            path = os.path.join(DATA_DIR_4H, f"{sym}.csv")
            df.to_csv(path, index=False)
            print(f"{len(df)} bars")
            success += 1
        # Small delay to avoid rate limiting
        if i < len(symbols) - 1:
            time.sleep(1)

    print(f"\nDone: {success}/{len(symbols)} stocks fetched")


if __name__ == "__main__":
    fetch_all_4h()
