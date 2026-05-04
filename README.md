# PSE Signal Alert System

Signal alert system for Philippine Stock Exchange (PSE) stocks using a MACD + RSI + EMA strategy on daily candles. No auto-execution — alerts only, you place trades manually via your broker.

## How It Works

- **Data source:** [Phisix API](http://phisix-api3.appspot.com) (free, no auth required)
- **Stock selection:** Top 25 PSE stocks ranked dynamically by 7-day average turnover
- **Strategy:** MACD crossover + EMA9 > EMA21 + RSI > 40 for entry; RSI overbought / stop-loss / take-profit for exit
- **Watchlist filter:** Stocks must have ≥ 5 trades, ≥ 50% win rate, and positive return over the backtest period

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/pse-signals.git
cd pse-signals

# Create a virtual environment
python -m venv .
Scripts/activate   # Windows
# source bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Daily routine (two commands)

```bash
# 1. Fetch latest data + scan for signals
py main.py update

# 2. Open the dashboard
py dashboard.py
# Then go to http://localhost:8050
```

### All commands

```bash
py main.py fetch [period]     # Fetch historical data (default: 2y)
py main.py backtest [period]  # Run strategy backtest
py main.py scan               # Check signals for watchlist stocks
py main.py scan-all           # Check signals for ALL 25 stocks
py main.py update             # Fetch recent data + scan watchlist
py main.py tune               # Grid search for optimal SL/TP
```

**Period format:** `30d`, `6m`, `1y`, `2y` (default: 2y)

**Options:**
```bash
--sl 6          # Override stop-loss %
--tp 12         # Override take-profit %
--min-trades 5  # Minimum trades to qualify for watchlist
--min-wr 50     # Minimum win rate %
```

### Dashboard

The web dashboard shows:
- Market overview (stocks up/down, active signals, oversold alerts)
- Watchlist table with price, 1D/7D change, RSI gauge, MACD/EMA status
- Buy/Sell/Warn signals with reasons
- Backtest stats (trades, win rate, 2Y return)
- Links to TradingView charts for each stock

## Project Structure

```
├── main.py          # CLI entry point
├── config.py        # Strategy parameters, stock list, filter criteria
├── fetcher.py       # Single-stock data fetcher
├── fast_fetch.py    # Parallel data fetcher (ThreadPool)
├── ranking.py       # Dynamic stock ranking by turnover
├── indicators.py    # MACD, RSI, EMA calculations
├── signals.py       # Signal scanner (entry/exit detection)
├── backtest.py      # Strategy backtester
├── tune.py          # SL/TP grid search optimizer
├── dashboard.py     # Web dashboard server (port 8050)
├── dashboard.html   # Dashboard frontend
└── data/            # Fetched CSV files (gitignored)
```

## Strategy Details

**Entry conditions (all must be true):**
1. MACD line crosses above signal line
2. EMA9 > EMA21 (short-term trend is up)
3. RSI > 40 (not in oversold territory)

**Exit conditions (any one triggers):**
1. RSI > 75 (overbought)
2. Price drops below stop-loss (default: 6%)
3. Price rises above take-profit (default: 12%)

## Notes

- PSE trades weekdays 9:30am–3:30pm PHT
- The Phisix API provides close price and volume only (no OHLC)
- First fetch takes a while (~2 years × 25 stocks); subsequent updates are fast
- Stock ranking refreshes automatically — new high-volume stocks enter the top 25

## Disclaimer

This project is for **educational and informational purposes only**. It is not financial advice. The authors are not licensed financial advisors. Past backtest performance does not guarantee future results. Always do your own research before making any investment decisions. Trade at your own risk.
