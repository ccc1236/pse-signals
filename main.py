"""PSE Signal Alert System - Main runner."""

import sys

import config
from config import get_stocks
from fast_fetch import fast_fetch_all
from backtest import run_backtest, get_filtered_stocks
from signals import scan_signals, format_signals


def parse_period(s: str) -> int:
    """Parse period string like '1y', '2y', '6m', '30d' into days."""
    s = s.lower().strip()
    if s.endswith("y"):
        return int(s[:-1]) * 365
    elif s.endswith("m"):
        return int(s[:-1]) * 30
    elif s.endswith("d"):
        return int(s[:-1])
    else:
        return int(s)  # bare number = days


def parse_args(args: list[str]) -> dict:
    """Parse optional CLI args after the command.

    Supports:
        1y / 2y / 6m / 30d   — lookback period
        --sl=5                — stop loss %
        --tp=12               — take profit %
        --min-trades=5        — min trades filter
        --min-wr=60           — min win rate filter
        --top=30              — top N stocks
    """
    opts = {}
    for arg in args:
        if arg.startswith("--sl="):
            config.STOP_LOSS_PCT = float(arg.split("=")[1])
            opts["sl"] = config.STOP_LOSS_PCT
        elif arg.startswith("--tp="):
            config.TAKE_PROFIT_PCT = float(arg.split("=")[1])
            opts["tp"] = config.TAKE_PROFIT_PCT
        elif arg.startswith("--min-trades="):
            config.MIN_TRADES = int(arg.split("=")[1])
            opts["min_trades"] = config.MIN_TRADES
        elif arg.startswith("--min-wr="):
            config.MIN_WIN_RATE = float(arg.split("=")[1])
            opts["min_wr"] = config.MIN_WIN_RATE
        elif arg.startswith("--top="):
            config.TOP_N_STOCKS = int(arg.split("=")[1])
            opts["top"] = config.TOP_N_STOCKS
        else:
            # Assume it's a period like 1y, 2y, 6m, 30d
            try:
                days = parse_period(arg)
                config.LOOKBACK_DAYS = days
                opts["period"] = arg
            except ValueError:
                print(f"Unknown argument: {arg}")
                sys.exit(1)
    return opts


def print_settings(opts: dict):
    """Print active settings if any were overridden."""
    if opts:
        parts = []
        if "period" in opts:
            parts.append(f"lookback={opts['period']}")
        if "sl" in opts:
            parts.append(f"SL={opts['sl']}%")
        if "tp" in opts:
            parts.append(f"TP={opts['tp']}%")
        if "min_trades" in opts:
            parts.append(f"min_trades={opts['min_trades']}")
        if "min_wr" in opts:
            parts.append(f"min_wr={opts['min_wr']}%")
        if "top" in opts:
            parts.append(f"top={opts['top']}")
        print(f"[Override] {', '.join(parts)}")


def cmd_fetch(args):
    """Fetch/update historical data for all stocks."""
    opts = parse_args(args)
    print_settings(opts)
    stocks = get_stocks()
    print(f"Active stocks ({len(stocks)}): {', '.join(stocks)}")
    fast_fetch_all(symbols=stocks, days=config.LOOKBACK_DAYS)


def cmd_backtest(args):
    """Run backtest and show results."""
    opts = parse_args(args)
    print_settings(opts)
    stocks = get_stocks()
    summary = run_backtest(symbols=stocks)
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


def cmd_scan(args):
    """Scan filtered watchlist for current signals."""
    parse_args(args)
    watchlist = get_filtered_stocks()
    print(f"Watchlist: {', '.join(watchlist)}\n")
    signals = scan_signals(symbols=watchlist)
    print(format_signals(signals))


def cmd_scan_all(args):
    """Scan ALL stocks for current signals (ignoring filter)."""
    parse_args(args)
    signals = scan_signals(filtered_only=False)
    print(format_signals(signals))


def cmd_update_and_scan(args):
    """Fetch latest data then scan filtered watchlist."""
    opts = parse_args(args)
    print_settings(opts)
    stocks = get_stocks()
    fast_fetch_all(symbols=stocks, days=30)
    watchlist = get_filtered_stocks()
    print(f"Watchlist: {', '.join(watchlist)}\n")
    signals = scan_signals(symbols=watchlist)
    print(format_signals(signals))


def cmd_tune(args):
    """Run SL/TP grid search tuner."""
    from tune import tune, print_results
    sl_range = [2, 3, 4, 5, 6, 7, 8]
    tp_range = [5, 8, 10, 12, 15, 18, 20]
    for arg in args:
        if arg.startswith("--sl="):
            sl_range = [float(x) for x in arg.split("=")[1].split(",")]
        elif arg.startswith("--tp="):
            tp_range = [float(x) for x in arg.split("=")[1].split(",")]
    df = tune(sl_range=sl_range, tp_range=tp_range)
    print_results(df)


COMMANDS = {
    "fetch": cmd_fetch,
    "backtest": cmd_backtest,
    "scan": cmd_scan,
    "scan-all": cmd_scan_all,
    "update": cmd_update_and_scan,
    "tune": cmd_tune,
}

USAGE = """Usage: py main.py <command> [period] [options]

Commands:
  fetch      Download historical data for all stocks
  backtest   Run strategy backtest on cached data
  scan       Check signals for filtered watchlist
  scan-all   Check signals for ALL stocks
  update     Fetch recent data then scan watchlist
  tune       Grid search for optimal SL/TP percentages

Period (optional):
  1y, 2y, 5y, 6m, 90d, etc.

Options (optional):
  --sl=5          Stop loss percentage (default: 3%)
  --tp=12         Take profit percentage (default: 8%)
  --min-trades=5  Minimum trades for watchlist filter
  --min-wr=60     Minimum win rate % for watchlist filter
  --top=30        Top N stocks to track

Examples:
  py main.py fetch 2y
  py main.py backtest 5y --sl=5 --tp=12
  py main.py backtest --min-trades=5 --min-wr=60
  py main.py update
  py main.py tune
  py main.py tune --sl=2,3,4,5 --tp=8,10,12,15,20"""


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(USAGE)
        sys.exit(1)

    COMMANDS[sys.argv[1]](sys.argv[2:])
