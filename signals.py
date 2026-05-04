"""Signal scanner: check current state of all stocks for entry/exit signals."""

import os
from datetime import datetime

import pandas as pd

import config
from config import (
    MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_SHORT, EMA_LONG,
    RSI_PERIOD, RSI_ENTRY_MIN, RSI_ENTRY_MAX, RSI_EXIT_MAX, STOCKS,
)
from indicators import add_indicators


def scan_signals(symbols: list[str] = None, filtered_only: bool = True) -> list[dict]:
    """Scan stocks for current entry/exit signals.
    If filtered_only=True, only scans stocks that passed backtest criteria."""
    if symbols is None:
        if filtered_only:
            from backtest import get_filtered_stocks
            symbols = get_filtered_stocks()
            if not symbols:
                symbols = STOCKS  # Fallback if no backtest data
        else:
            symbols = STOCKS
    signals = []

    for sym in symbols:
        path = os.path.join(config.DATA_DIR, f"{sym}.csv")
        if not os.path.exists(path):
            continue

        df = pd.read_csv(path, parse_dates=["date"])
        if len(df) < 30:
            continue

        df = add_indicators(df, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                            EMA_SHORT, EMA_LONG, RSI_PERIOD)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(curr["macd"]) or pd.isna(curr["rsi"]):
            continue

        # Entry signal
        macd_cross = prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]
        ema_aligned = curr["ema_short"] > curr["ema_long"]
        rsi_ok = RSI_ENTRY_MIN < curr["rsi"] < RSI_ENTRY_MAX

        if macd_cross and ema_aligned and rsi_ok:
            signals.append({
                "symbol": sym,
                "signal": "BUY",
                "date": str(curr["date"].date()),
                "close": curr["close"],
                "rsi": round(curr["rsi"], 1),
                "macd": round(curr["macd"], 4),
                "macd_signal": round(curr["macd_signal"], 4),
                "reason": "MACD crossover + EMA9>EMA21 + RSI>40",
            })

        # Exit / warning signals
        if curr["rsi"] > RSI_EXIT_MAX:
            signals.append({
                "symbol": sym,
                "signal": "SELL",
                "date": str(curr["date"].date()),
                "close": curr["close"],
                "rsi": round(curr["rsi"], 1),
                "reason": f"RSI overbought ({curr['rsi']:.1f})",
            })

        # Bearish MACD cross
        macd_cross_down = prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]
        if macd_cross_down:
            signals.append({
                "symbol": sym,
                "signal": "WARN",
                "date": str(curr["date"].date()),
                "close": curr["close"],
                "rsi": round(curr["rsi"], 1),
                "reason": "Bearish MACD crossover",
            })

    return signals


def format_signals(signals: list[dict]) -> str:
    """Format signals into a readable alert message."""
    if not signals:
        return "No signals detected today."

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"PSE Signal Alert - {now}", "=" * 50]

    buys = [s for s in signals if s["signal"] == "BUY"]
    sells = [s for s in signals if s["signal"] == "SELL"]
    warns = [s for s in signals if s["signal"] == "WARN"]

    if buys:
        lines.append("\n** BUY SIGNALS **")
        for s in buys:
            lines.append(f"  {s['symbol']} @ PHP {s['close']:.2f} | RSI: {s['rsi']} | {s['reason']}")

    if sells:
        lines.append("\n** SELL SIGNALS **")
        for s in sells:
            lines.append(f"  {s['symbol']} @ PHP {s['close']:.2f} | RSI: {s['rsi']} | {s['reason']}")

    if warns:
        lines.append("\n** WARNINGS **")
        for s in warns:
            lines.append(f"  {s['symbol']} @ PHP {s['close']:.2f} | RSI: {s['rsi']} | {s['reason']}")

    lines.append(f"\nTotal: {len(buys)} buy, {len(sells)} sell, {len(warns)} warn")
    return "\n".join(lines)


if __name__ == "__main__":
    signals = scan_signals()
    print(format_signals(signals))
