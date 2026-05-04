"""SL/TP tuner — grid search for optimal stop-loss and take-profit percentages."""

import os
import sys
from itertools import product

import pandas as pd

import config
from config import get_stocks
from backtest import backtest_stock


def load_stock_data(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Load all stock CSVs into memory once."""
    data = {}
    for sym in symbols:
        path = os.path.join(config.DATA_DIR, f"{sym}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["date"])
            if len(df) >= 30:
                data[sym] = df
    return data


def tune(sl_range=None, tp_range=None, symbols=None):
    """Grid search over SL/TP combos, return results sorted by best total return."""
    if sl_range is None:
        sl_range = [2, 3, 4, 5, 6, 7, 8]
    if tp_range is None:
        tp_range = [5, 8, 10, 12, 15, 18, 20]
    if symbols is None:
        symbols = get_stocks()

    print(f"Tuning SL/TP on {len(symbols)} stocks")
    print(f"SL range: {sl_range}")
    print(f"TP range: {tp_range}")
    print(f"Combos: {len(sl_range) * len(tp_range)}\n")

    # Load data once
    data = load_stock_data(symbols)
    print(f"Loaded {len(data)} stocks with sufficient data\n")

    results = []
    combos = list(product(sl_range, tp_range))

    for idx, (sl, tp) in enumerate(combos, 1):
        if sl >= tp:
            continue  # SL should be less than TP

        total_trades = 0
        total_wins = 0
        total_pnl = 0.0
        stock_results = []

        for sym, df in data.items():
            res = backtest_stock(df, sl_pct=sl, tp_pct=tp)
            total_trades += res["num_trades"]
            if res["num_trades"] > 0:
                total_wins += round(res["win_rate"] / 100 * res["num_trades"])
                total_pnl += res["total_return"]
                stock_results.append({
                    "symbol": sym,
                    "trades": res["num_trades"],
                    "win_rate": res["win_rate"],
                    "total_return": res["total_return"],
                })

        win_rate = round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0
        profitable = sum(1 for s in stock_results if s["total_return"] > 0)
        avg_return = round(total_pnl / len(data), 2) if data else 0

        results.append({
            "sl": sl,
            "tp": tp,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "avg_return_per_stock": avg_return,
            "profitable_stocks": profitable,
            "total_stocks": len(data),
        })

        if idx % 10 == 0 or idx == len(combos):
            print(f"  Progress: {idx}/{len(combos)}")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("total_pnl", ascending=False).reset_index(drop=True)
    return df_results


def print_results(df: pd.DataFrame, top_n: int = 15):
    """Print tuning results table."""
    print("\n" + "=" * 100)
    print("SL/TP TUNING RESULTS (sorted by total P&L across all stocks)")
    print("=" * 100)

    header = f"{'Rank':<5} {'SL%':<6} {'TP%':<6} {'Trades':<8} {'Win%':<7} {'Total P&L':<12} {'Avg/Stock':<12} {'Profitable':<12}"
    print(header)
    print("-" * 100)

    for i, row in df.head(top_n).iterrows():
        rank = i + 1
        print(f"{rank:<5} {row['sl']:<6} {row['tp']:<6} {row['total_trades']:<8} "
              f"{row['win_rate']:<7} {row['total_pnl']:>+9.2f}%   "
              f"{row['avg_return_per_stock']:>+9.2f}%   "
              f"{row['profitable_stocks']}/{row['total_stocks']}")

    print("-" * 100)

    # Show the best combo
    best = df.iloc[0]
    print(f"\nBest combo: SL={best['sl']}% / TP={best['tp']}%")
    print(f"  Total P&L: {best['total_pnl']:+.2f}% across {best['total_stocks']} stocks")
    print(f"  Win rate: {best['win_rate']}% over {best['total_trades']} trades")
    print(f"  Profitable stocks: {best['profitable_stocks']}/{best['total_stocks']}")

    # Show current default for comparison
    from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT
    current = df[(df["sl"] == STOP_LOSS_PCT) & (df["tp"] == TAKE_PROFIT_PCT)]
    if len(current) > 0:
        c = current.iloc[0]
        print(f"\nCurrent config (SL={STOP_LOSS_PCT}% / TP={TAKE_PROFIT_PCT}%):")
        print(f"  Total P&L: {c['total_pnl']:+.2f}% | Win rate: {c['win_rate']}% | "
              f"Profitable: {c['profitable_stocks']}/{c['total_stocks']}")

    # Per-stock breakdown for the best combo
    print(f"\n--- Per-stock breakdown for best combo (SL={best['sl']}% / TP={best['tp']}%) ---")
    data = load_stock_data(get_stocks())
    stock_rows = []
    for sym, sdf in data.items():
        res = backtest_stock(sdf, sl_pct=best["sl"], tp_pct=best["tp"])
        if res["num_trades"] > 0:
            stock_rows.append({
                "symbol": sym,
                "trades": res["num_trades"],
                "win_rate": res["win_rate"],
                "total_return": res["total_return"],
                "best": res.get("best_trade", 0),
                "worst": res.get("worst_trade", 0),
            })
    stock_df = pd.DataFrame(stock_rows).sort_values("total_return", ascending=False)
    print(stock_df.to_string(index=False))


if __name__ == "__main__":
    # Parse optional args: custom SL/TP ranges
    sl_range = [2, 3, 4, 5, 6, 7, 8]
    tp_range = [5, 8, 10, 12, 15, 18, 20]

    for arg in sys.argv[1:]:
        if arg.startswith("--sl="):
            vals = arg.split("=")[1]
            sl_range = [float(x) for x in vals.split(",")]
        elif arg.startswith("--tp="):
            vals = arg.split("=")[1]
            tp_range = [float(x) for x in vals.split(",")]

    df = tune(sl_range=sl_range, tp_range=tp_range)
    print_results(df)
