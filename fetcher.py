"""Fetch historical daily close+volume for PSE stocks from Phisix API."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import requests

from config import API_BASE, DATA_DIR, LOOKBACK_DAYS, STOCKS

SESSION = requests.Session()


def fetch_stock_day(symbol: str, date: str) -> dict | None:
    """Fetch single stock data for a given date (YYYY-MM-DD)."""
    url = f"{API_BASE}/stocks/{symbol}.{date}.json"
    try:
        resp = SESSION.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        stocks = data.get("stock") or data.get("stocks")
        if not stocks:
            return None
        stock = stocks[0]
        return {
            "date": date,
            "close": stock["price"]["amount"],
            "volume": stock["volume"],
        }
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError):
        return None


def _get_weekdays(days: int) -> list[str]:
    """Generate list of weekday date strings for the lookback period."""
    end = datetime.now()
    start = end - timedelta(days=days)
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def fetch_stock_history(symbol: str, days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """Fetch historical data for a stock, skipping weekends."""
    cache_path = os.path.join(DATA_DIR, f"{symbol}.csv")

    existing_dates = set()
    rows = []
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["date"])
        existing_dates = set(df["date"].dt.strftime("%Y-%m-%d"))
        rows = df.to_dict("records")

    all_dates = _get_weekdays(days)
    to_fetch = [d for d in all_dates if d not in existing_dates]

    new_fetches = 0
    for date_str in to_fetch:
        result = fetch_stock_day(symbol, date_str)
        if result:
            rows.append(result)
            new_fetches += 1
        time.sleep(0.1)

    if not rows:
        return pd.DataFrame(columns=["date", "close", "volume"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(cache_path, index=False)

    if new_fetches:
        print(f"  {symbol}: fetched {new_fetches} new days, total {len(df)} rows")
    else:
        print(f"  {symbol}: {len(df)} rows (cached)")

    return df


def fetch_all(symbols: list[str] = STOCKS, days: int = LOOKBACK_DAYS) -> dict[str, pd.DataFrame]:
    """Fetch history for all stocks. Returns dict of symbol -> DataFrame."""
    print(f"Fetching {len(symbols)} stocks, {days} days lookback...")
    result = {}
    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym}")
        result[sym] = fetch_stock_history(sym, days)
    print("Done!")
    return result


if __name__ == "__main__":
    data = fetch_all()
    for sym, df in data.items():
        if len(df) > 0:
            print(f"{sym}: {len(df)} days, {df['date'].min().date()} to {df['date'].max().date()}")
