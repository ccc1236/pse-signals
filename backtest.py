"""Backtester for MACD+RSI+EMA strategy on PSE stocks."""

import os

import pandas as pd

import config
from config import (
    DATA_DIR, MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_SHORT, EMA_LONG,
    RSI_PERIOD, RSI_ENTRY_MIN, RSI_EXIT_MAX, STOCKS,
)
from indicators import add_indicators


def backtest_stock(df: pd.DataFrame, sl_pct: float = None,
                   tp_pct: float = None) -> dict:
    """Backtest MACD+RSI+EMA strategy on a single stock.

    Entry: MACD crosses above signal AND EMA9 > EMA21 AND RSI > 40
    Exit: RSI > 75 OR stop-loss hit OR take-profit hit

    Returns dict with trades list and summary stats.
    """
    if sl_pct is None:
        sl_pct = config.STOP_LOSS_PCT
    if tp_pct is None:
        tp_pct = config.TAKE_PROFIT_PCT
    if len(df) < 30:
        return {"trades": [], "total_return": 0, "win_rate": 0, "num_trades": 0}

    df = add_indicators(df, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                        EMA_SHORT, EMA_LONG, RSI_PERIOD)

    trades = []
    in_position = False
    entry_price = 0
    entry_date = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if pd.isna(row["macd"]) or pd.isna(row["rsi"]):
            continue

        if not in_position:
            # Entry: MACD crossover + EMA alignment + RSI filter
            macd_cross = prev["macd"] <= prev["macd_signal"] and row["macd"] > row["macd_signal"]
            ema_aligned = row["ema_short"] > row["ema_long"]
            rsi_ok = row["rsi"] > RSI_ENTRY_MIN

            if macd_cross and ema_aligned and rsi_ok:
                in_position = True
                entry_price = row["close"]
                entry_date = row["date"]
        else:
            # Exit checks
            pnl_pct = (row["close"] - entry_price) / entry_price * 100
            reason = None

            if pnl_pct <= -sl_pct:
                reason = "stop_loss"
            elif pnl_pct >= tp_pct:
                reason = "take_profit"
            elif row["rsi"] > RSI_EXIT_MAX:
                reason = "rsi_overbought"

            if reason:
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row["date"],
                    "entry_price": entry_price,
                    "exit_price": row["close"],
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": reason,
                    "hold_days": (row["date"] - entry_date).days,
                })
                in_position = False

    # Summary
    if trades:
        pnls = [t["pnl_pct"] for t in trades]
        wins = [p for p in pnls if p > 0]
        return {
            "trades": trades,
            "num_trades": len(trades),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "total_return": round(sum(pnls), 2),
            "avg_return": round(sum(pnls) / len(pnls), 2),
            "best_trade": round(max(pnls), 2),
            "worst_trade": round(min(pnls), 2),
            "avg_hold_days": round(sum(t["hold_days"] for t in trades) / len(trades), 1),
        }
    return {"trades": [], "num_trades": 0, "win_rate": 0, "total_return": 0}


def run_backtest(symbols: list[str] = STOCKS) -> pd.DataFrame:
    """Run backtest on all stocks, return summary DataFrame."""
    results = []

    for sym in symbols:
        path = os.path.join(DATA_DIR, f"{sym}.csv")
        if not os.path.exists(path):
            print(f"  {sym}: no data, skipping")
            continue

        df = pd.read_csv(path, parse_dates=["date"])
        if len(df) < 30:
            print(f"  {sym}: only {len(df)} rows, skipping")
            continue

        res = backtest_stock(df)
        res["symbol"] = sym
        res["data_days"] = len(df)
        results.append(res)

    if not results:
        print("No results!")
        return pd.DataFrame()

    summary = pd.DataFrame([{
        "symbol": r["symbol"],
        "data_days": r["data_days"],
        "trades": r["num_trades"],
        "win_rate": r.get("win_rate", 0),
        "total_return": r.get("total_return", 0),
        "avg_return": r.get("avg_return", 0),
        "best": r.get("best_trade", 0),
        "worst": r.get("worst_trade", 0),
        "avg_hold": r.get("avg_hold_days", 0),
    } for r in results])

    summary = summary.sort_values("total_return", ascending=False).reset_index(drop=True)
    return summary


def get_filtered_stocks(summary: pd.DataFrame = None) -> list[str]:
    """Filter stocks that pass backtest criteria.
    Criteria: >= MIN_TRADES trades, >= MIN_WIN_RATE%, >= MIN_TOTAL_RETURN%."""
    if summary is None:
        summary = run_backtest()
    if len(summary) == 0:
        return []

    filtered = summary[
        (summary["trades"] >= config.MIN_TRADES) &
        (summary["win_rate"] >= config.MIN_WIN_RATE) &
        (summary["total_return"] > config.MIN_TOTAL_RETURN)
    ]
    return filtered["symbol"].tolist()


if __name__ == "__main__":
    print("Running backtest on all stocks...\n")
    summary = run_backtest()
    if len(summary) > 0:
        print("\n" + "=" * 85)
        print("BACKTEST RESULTS (MACD+RSI+EMA Strategy)")
        print("=" * 85)
        print(summary.to_string(index=False))
        print(f"\nStocks tested: {len(summary)}")
        profitable = summary[summary["total_return"] > 0]
        print(f"Profitable: {len(profitable)}/{len(summary)}")
        print(f"Avg total return: {summary['total_return'].mean():.2f}%")

        filtered = get_filtered_stocks(summary)
        print(f"\n--- FILTERED WATCHLIST ---")
        print(f"Criteria: >= {config.MIN_TRADES} trades, >= {config.MIN_WIN_RATE}% win rate, > {config.MIN_TOTAL_RETURN}% return")
        print(f"Stocks: {', '.join(filtered) if filtered else 'None'}")
        print(f"Count: {len(filtered)}/{len(summary)}")
