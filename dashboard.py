"""Dashboard server for PSE Signal Alert System."""

import json
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pandas as pd

from config import (
    DATA_DIR, MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_SHORT, EMA_LONG,
    RSI_PERIOD, RSI_ENTRY_MIN, RSI_EXIT_MAX, DYNAMIC_RANKING,
    MIN_TRADES, MIN_WIN_RATE, MIN_TOTAL_RETURN, get_stocks,
)
from indicators import add_indicators
from backtest import run_backtest, get_filtered_stocks
from signals import scan_signals
from ranking import fetch_current_stocks


def get_dashboard_data() -> dict:
    """Build all data needed for the dashboard."""
    # Get active stock list (dynamic or fallback)
    active_stocks = get_stocks()

    # Run backtest to get stats and filtered list
    summary = run_backtest(symbols=active_stocks)
    watchlist = get_filtered_stocks(summary) if len(summary) > 0 else []

    # Get signals for all active stocks
    all_signals = scan_signals(symbols=active_stocks, filtered_only=False)

    # Get current market data from API for names
    current_market = fetch_current_stocks()
    name_map = {s["symbol"]: s["name"] for s in current_market}

    # Build per-stock details with indicators
    stock_details = []
    for sym in active_stocks:
        path = os.path.join(DATA_DIR, f"{sym}.csv")
        if not os.path.exists(path):
            continue

        df = pd.read_csv(path, parse_dates=["date"])
        if len(df) < 2:
            continue

        df = add_indicators(df, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                            EMA_SHORT, EMA_LONG, RSI_PERIOD)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        daily_change = (curr["close"] - prev["close"]) / prev["close"] * 100

        # 7-day change (5 trading days)
        weekly_change = None
        if len(df) >= 6:
            week_ago = df.iloc[-6]
            weekly_change = round((curr["close"] - week_ago["close"]) / week_ago["close"] * 100, 2)

        # Get backtest row for this stock
        bt_row = None
        if len(summary) > 0 and sym in summary["symbol"].values:
            bt_row = summary[summary["symbol"] == sym].iloc[0]

        # Determine signal for this stock
        signal = None
        for s in all_signals:
            if s["symbol"] == sym:
                signal = s
                break

        # RSI zone classification
        rsi_val = round(curr["rsi"], 1) if pd.notna(curr["rsi"]) else None
        rsi_zone = "neutral"
        if rsi_val is not None:
            if rsi_val < 30:
                rsi_zone = "oversold"
            elif rsi_val < 40:
                rsi_zone = "near_oversold"
            elif rsi_val > 75:
                rsi_zone = "overbought"
            elif rsi_val > 65:
                rsi_zone = "near_overbought"

        detail = {
            "symbol": sym,
            "name": name_map.get(sym, sym),
            "close": round(curr["close"], 2),
            "prev_close": round(prev["close"], 2),
            "daily_change": round(daily_change, 2),
            "weekly_change": weekly_change,
            "date": str(curr["date"].date()),
            "rsi": rsi_val,
            "rsi_zone": rsi_zone,
            "macd": round(curr["macd"], 4) if pd.notna(curr["macd"]) else None,
            "macd_signal_line": round(curr["macd_signal"], 4) if pd.notna(curr["macd_signal"]) else None,
            "macd_hist": round(curr["macd_hist"], 4) if pd.notna(curr["macd_hist"]) else None,
            "ema_short": round(curr["ema_short"], 2) if pd.notna(curr["ema_short"]) else None,
            "ema_long": round(curr["ema_long"], 2) if pd.notna(curr["ema_long"]) else None,
            "ema_aligned": bool(curr["ema_short"] > curr["ema_long"]) if pd.notna(curr["ema_short"]) else False,
            "macd_bullish": bool(curr["macd"] > curr["macd_signal"]) if pd.notna(curr["macd"]) else False,
            "in_watchlist": sym in watchlist,
            "signal": signal,
            # Backtest stats
            "bt_trades": int(bt_row["trades"]) if bt_row is not None else 0,
            "bt_win_rate": float(bt_row["win_rate"]) if bt_row is not None else 0,
            "bt_total_return": float(bt_row["total_return"]) if bt_row is not None else 0,
            "bt_avg_return": float(bt_row["avg_return"]) if bt_row is not None else 0,
        }
        stock_details.append(detail)

    # Market overview
    up = sum(1 for s in stock_details if s["daily_change"] > 0)
    down = sum(1 for s in stock_details if s["daily_change"] < 0)
    flat = len(stock_details) - up - down
    oversold = [s["symbol"] for s in stock_details if s["rsi_zone"] == "oversold"]
    overbought = [s["symbol"] for s in stock_details if s["rsi_zone"] == "overbought"]

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_date": stock_details[0]["date"] if stock_details else "N/A",
        "dynamic_ranking": DYNAMIC_RANKING,
        "market_overview": {
            "up": up, "down": down, "flat": flat, "total": len(stock_details),
            "oversold": oversold, "overbought": overbought,
        },
        "watchlist": watchlist,
        "all_signals": all_signals,
        "stocks": stock_details,
        "filter_criteria": {
            "min_trades": MIN_TRADES,
            "min_win_rate": MIN_WIN_RATE,
            "min_total_return": MIN_TOTAL_RETURN,
        },
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            data = get_dashboard_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        elif self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open(os.path.join(os.path.dirname(__file__), "dashboard.html"), "rb") as f:
                self.wfile.write(f.read())
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def main():
    port = 8050
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()
