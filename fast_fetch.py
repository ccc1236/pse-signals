"""Fast parallel fetcher — fetches all stocks for each date concurrently."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pandas as pd
import requests

from config import API_BASE, DATA_DIR, LOOKBACK_DAYS, STOCKS


def _fetch_one(symbol: str, date: str) -> dict | None:
    url = f"{API_BASE}/stocks/{symbol}.{date}.json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        stocks = data.get("stock") or data.get("stocks")
        if not stocks:
            return None
        s = stocks[0]
        return {"symbol": symbol, "date": date, "close": s["price"]["amount"], "volume": s["volume"]}
    except Exception:
        return None


def fast_fetch_all(symbols: list[str] = STOCKS, days: int = LOOKBACK_DAYS):
    """Fetch all stocks in parallel, date by date."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing cached data
    cached = {}
    for sym in symbols:
        path = os.path.join(DATA_DIR, f"{sym}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["date"])
            cached[sym] = set(df["date"].dt.strftime("%Y-%m-%d"))
        else:
            cached[sym] = set()

    # Build date list
    end = datetime.now()
    start = end - timedelta(days=days)
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # Collect all (symbol, date) pairs that need fetching
    tasks = []
    for date_str in dates:
        for sym in symbols:
            if date_str not in cached[sym]:
                tasks.append((sym, date_str))

    print(f"Need to fetch {len(tasks)} data points ({len(dates)} dates x {len(symbols)} stocks, minus cached)")
    if not tasks:
        print("Everything cached!")
        return

    # Fetch in parallel batches
    results = {sym: [] for sym in symbols}
    batch_size = 25  # One date's worth of stocks at a time
    done = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            futures = {executor.submit(_fetch_one, sym, dt): (sym, dt) for sym, dt in batch}
            for future in futures:
                result = future.result()
                if result:
                    results[result["symbol"]].append(result)
            done += len(batch)
            if done % 250 == 0 or done == len(tasks):
                print(f"  Progress: {done}/{len(tasks)} ({done * 100 // len(tasks)}%)")
            time.sleep(0.15)  # Small delay between batches

    # Merge with cached data and save
    for sym in symbols:
        path = os.path.join(DATA_DIR, f"{sym}.csv")
        rows = results[sym]

        if os.path.exists(path):
            existing = pd.read_csv(path, parse_dates=["date"])
            if rows:
                new_df = pd.DataFrame(rows)[["date", "close", "volume"]]
                new_df["date"] = pd.to_datetime(new_df["date"])
                df = pd.concat([existing, new_df], ignore_index=True)
            else:
                df = existing
        else:
            if not rows:
                continue
            df = pd.DataFrame(rows)[["date", "close", "volume"]]
            df["date"] = pd.to_datetime(df["date"])

        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        df.to_csv(path, index=False)
        print(f"  {sym}: {len(df)} rows saved")

    print("Done!")


if __name__ == "__main__":
    fast_fetch_all()
