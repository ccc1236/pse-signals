"""Dynamic stock ranking — picks top N PSE stocks by 7-day average turnover."""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

from config import API_BASE, DATA_DIR


def fetch_current_stocks() -> list[dict]:
    """Fetch all stocks from /stocks.json with current price and volume."""
    url = f"{API_BASE}/stocks.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        stocks = data.get("stock") or data.get("stocks") or []
        result = []
        for s in stocks:
            result.append({
                "symbol": s["symbol"],
                "name": s["name"],
                "price": s["price"]["amount"],
                "volume": s["volume"],
                "pct_change": s.get("percent_change", 0),
            })
        return result
    except Exception as e:
        print(f"Error fetching /stocks.json: {e}")
        return []


def compute_turnover_ranking(top_n: int = 25, lookback_days: int = 7) -> list[str]:
    """Rank all PSE stocks by average daily turnover over the last N trading days.

    Turnover = price * volume (proxy — Phisix doesn't give actual turnover).
    Returns list of top N symbols sorted by turnover descending.
    """
    # Get current list of all stocks
    current = fetch_current_stocks()
    if not current:
        return []

    all_symbols = [s["symbol"] for s in current]

    # Compute average turnover from cached CSV data (if available)
    rankings = []
    for sym in all_symbols:
        path = os.path.join(DATA_DIR, f"{sym}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["date"])
            # Take the last N trading days
            df = df.sort_values("date").tail(lookback_days)
            if len(df) > 0:
                df["turnover"] = df["close"] * df["volume"]
                avg_turnover = df["turnover"].mean()
                rankings.append({"symbol": sym, "avg_turnover": avg_turnover})
                continue

        # Fallback: use current day's data from API
        for s in current:
            if s["symbol"] == sym:
                turnover = s["price"] * s["volume"]
                rankings.append({"symbol": sym, "avg_turnover": turnover})
                break

    # Sort by turnover descending
    rankings.sort(key=lambda x: x["avg_turnover"], reverse=True)
    return [r["symbol"] for r in rankings[:top_n]]


def get_dynamic_stocks(top_n: int = 25) -> list[str]:
    """Get the current top N stocks by turnover.

    Uses cached ranking if fresh (< 1 day old), otherwise recomputes.
    """
    cache_path = os.path.join(DATA_DIR, "ranking_cache.json")

    # Check cache
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            cache = json.load(f)
        cached_date = cache.get("date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if cached_date == today and len(cache.get("symbols", [])) > 0:
            return cache["symbols"]

    # Recompute
    symbols = compute_turnover_ranking(top_n=top_n)
    if symbols:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "symbols": symbols}, f)
        print(f"Ranking updated: top {len(symbols)} stocks by turnover")

    return symbols


if __name__ == "__main__":
    print("Fetching current stocks from Phisix API...")
    stocks = fetch_current_stocks()
    print(f"Total listed stocks: {len(stocks)}")

    print(f"\nComputing top 25 by turnover...")
    top25 = compute_turnover_ranking(top_n=25)
    print(f"Top 25: {', '.join(top25)}")
