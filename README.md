# PSE Signal Alert System

Signal alert system for Philippine Stock Exchange (PSE) stocks using a MACD + RSI + EMA strategy. Supports daily and 4-hour candles. No auto-execution — alerts only, you place trades manually via your broker.

## How It Works

- **Data sources:**
  - [Phisix API](http://phisix-api3.appspot.com) — daily candles (free, no auth)
  - [TradingView](https://www.tradingview.com) via `tvDatafeed` — 4H candles with full OHLCV (free, no auth)
- **Stock selection:** Top 25 PSE stocks ranked dynamically by 7-day average turnover
- **Strategy:** MACD crossover + EMA9 > EMA21 + RSI between 40-60 for entry; RSI overbought / stop-loss / take-profit for exit
- **Watchlist filter:** Stocks must have >= 5 trades, >= 50% win rate, and positive return over the backtest period

## Setup

```bash
# Clone the repo
git clone https://github.com/ccc1236/pse-signals.git
cd pse-signals

# Create a virtual environment
python -m venv .
Scripts/activate   # Windows
# source bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Daily routine

```bash
# 1. Fetch latest data (both 1D and 4H) + scan for signals
py main.py update

# 2. Open the dashboard
py dashboard.py
# Then go to http://localhost:8050
```

### All commands

```bash
py main.py fetch [period]     # Fetch historical data (default: 2y)
py main.py fetch --tf=4h      # Fetch 4H candles from TradingView
py main.py backtest [period]  # Run strategy backtest
py main.py backtest --tf=4h   # Backtest on 4H candles
py main.py scan               # Check signals for watchlist stocks
py main.py scan-all           # Check signals for ALL stocks
py main.py update             # Fetch both 1D + 4H data, then scan
py main.py tune               # Grid search for optimal SL/TP
py main.py tune --tf=4h       # Tune on 4H candles
```

**Period format:** `30d`, `6m`, `1y`, `2y` (default: 2y)

**Options:**
```bash
--tf=4h         # Use 4H candles (default: 1d)
--sl=6          # Override stop-loss % (default: 6%)
--tp=12         # Override take-profit % (default: 12%)
--min-trades=5  # Minimum trades to qualify for watchlist
--min-wr=50     # Minimum win rate %
--top=30        # Top N stocks to track
```

### Dashboard

The web dashboard at `http://localhost:8050` shows:
- **1D / 4H toggle** — switch timeframes without restarting
- Market overview (stocks up/down, active signals, oversold alerts)
- Watchlist table with price, 1D/7D change, RSI gauge, MACD/EMA status
- Buy/Sell/Warn signals with reasons
- Clickable trade history per stock (entry/exit dates, P&L, exit reason)
- Backtest stats (trades, win rate, return)
- Links to TradingView charts for each stock
- **Fetch & Refresh** button to pull new candles directly from the dashboard

## Project Structure

```
├── main.py          # CLI entry point
├── config.py        # Strategy parameters, stock list, filter criteria
├── fetcher.py       # Single-stock daily data fetcher (Phisix API)
├── fast_fetch.py    # Parallel daily data fetcher (ThreadPool)
├── fetcher_4h.py    # 4H candle fetcher (TradingView)
├── ranking.py       # Dynamic stock ranking by turnover
├── indicators.py    # MACD, RSI, EMA calculations
├── signals.py       # Signal scanner (entry/exit detection)
├── backtest.py      # Strategy backtester
├── tune.py          # SL/TP grid search optimizer
├── dashboard.py     # Web dashboard server (port 8050)
├── dashboard.html   # Dashboard frontend
├── data/            # Daily CSV files (gitignored)
└── data/4h/         # 4H CSV files (gitignored)
```

## Strategy Details

**Entry conditions (all must be true):**
1. MACD line crosses above signal line
2. EMA9 > EMA21 (short-term trend is up)
3. RSI between 40 and 60 (early momentum, not overextended)

**Exit conditions (any one triggers):**
1. RSI > 75 (overbought)
2. Price drops below stop-loss (default: 6%)
3. Price rises above take-profit (default: 12%)

## Notes

- PSE trades weekdays 9:30am-3:30pm PHT
- Daily data from Phisix API provides close price and volume only (no OHLC)
- 4H data from TradingView provides full OHLCV
- `py main.py update` fetches both 1D and 4H data in one command
- Stock ranking refreshes automatically — new high-volume stocks enter the top 25
- The `tvDatafeed` library is unofficial — it could break if TradingView changes their backend

## Disclaimer

This project is for **educational and informational purposes only**. It is not financial advice. The authors are not licensed financial advisors. Past backtest performance does not guarantee future results. Always do your own research before making any investment decisions. Trade at your own risk.
