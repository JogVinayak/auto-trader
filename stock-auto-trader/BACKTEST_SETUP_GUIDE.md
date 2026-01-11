# Backtesting System Setup Guide

## Overview

The backtesting system allows you to test trading strategies on historical data using a separate database, with complete control over timeframes and date ranges.

## What's Been Implemented

### Backend Components

1. **database_manager.py** - Dual database connection manager
   - Manages connections to both live and backtest databases
   - Provides easy switching between databases

2. **services/backtest_engine.py** - Core backtesting engine
   - Event-driven simulation of historical trading
   - Position sizing and capital management
   - Comprehensive performance metrics calculation
   - Sharpe ratio, max drawdown, win rate, profit factor

3. **API Endpoints in main.py**
   - `POST /backtest/run` - Execute backtest with parameters
   - `GET /backtest/data-availability` - Check available historical data

### Frontend Components

1. **BacktestModal.jsx** - Complete backtest UI
   - Strategy selection dropdown
   - Timeframe selector (1m, 5m, 1h, 1d)
   - Date range selection
   - Initial capital configuration
   - Position size adjustment
   - Results visualization with metrics grid
   - Trade history table

2. **Updated Dashboard.jsx**
   - Added "Backtest" button in header
   - Integrated BacktestModal component

3. **API Service (api.js)**
   - `backtestAPI.run()` - Run backtest
   - `backtestAPI.getDataAvailability()` - Check data

## Setup Instructions

### 1. Environment Configuration

Add to your `.env` file:

```bash
# Live database (existing)
DATABASE_URL=postgresql://user:pass@localhost/stock_trader_live

# Backtest database (new)
BACKTEST_DATABASE_URL=postgresql://user:pass@localhost/stock_trader_backtest
```

If you don't specify `BACKTEST_DATABASE_URL`, the system will use the same database as live trading.

### 2. Create Backtest Database

**Option A: Separate Database (Recommended)**

```bash
# Create new database
createdb stock_trader_backtest

# Copy schema from live database
pg_dump stock_trader_live --schema-only | psql stock_trader_backtest
```

**Option B: Use Same Database**

Skip this step if you want to use the same database. The system will work with either approach.

### 3. Load Historical Data

You need to populate the backtest database with historical candle data. Here are your options:

**Option A: Copy from Live Database**

```sql
-- Connect to backtest database
psql stock_trader_backtest

-- Copy stocks
INSERT INTO stocks SELECT * FROM dblink('dbname=stock_trader_live', 'SELECT * FROM stocks')
AS t(id integer, symbol varchar, name varchar);

-- Copy candles
INSERT INTO candles SELECT * FROM dblink('dbname=stock_trader_live',
'SELECT * FROM candles') AS t(id integer, stock_id integer, timestamp timestamp,
open numeric, high numeric, low numeric, close numeric, volume bigint, timeframe varchar);
```

**Option B: Fetch Fresh Historical Data**

Create a script to fetch historical data using yfinance or your data provider:

```python
# backend/scripts/load_historical_data.py
import yfinance as yf
from database_manager import db_manager
from models import Stock, Candle, TimeFrame
from datetime import datetime, timedelta

def load_historical_data(symbol, period='2y'):
    """Load historical data for backtesting"""
    bt_db = db_manager.get_backtest_session()

    try:
        # Get or create stock
        stock = bt_db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(symbol=symbol, name=symbol)
            bt_db.add(stock)
            bt_db.commit()
            bt_db.refresh(stock)

        # Download data
        ticker = yf.Ticker(symbol)

        # 1d data
        df_1d = ticker.history(period=period, interval='1d')
        for idx, row in df_1d.iterrows():
            candle = Candle(
                stock_id=stock.id,
                timestamp=idx.to_pydatetime(),
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume'],
                timeframe=TimeFrame.D1
            )
            bt_db.add(candle)

        # 1h data (last 730 days for hourly)
        df_1h = ticker.history(period='730d', interval='1h')
        for idx, row in df_1h.iterrows():
            candle = Candle(
                stock_id=stock.id,
                timestamp=idx.to_pydatetime(),
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume'],
                timeframe=TimeFrame.H1
            )
            bt_db.add(candle)

        bt_db.commit()
        print(f"✅ Loaded historical data for {symbol}")

    except Exception as e:
        print(f"❌ Error loading data for {symbol}: {e}")
        bt_db.rollback()
    finally:
        bt_db.close()

if __name__ == "__main__":
    # Load data for your stocks
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'RELIANCE.NS', 'TCS.NS']
    for symbol in symbols:
        load_historical_data(symbol)
```

Run the script:
```bash
cd backend
python3 scripts/load_historical_data.py
```

### 4. Test the System

**Test API Endpoint:**

```bash
curl -X POST "http://localhost:8000/backtest/run?symbol=AAPL&strategy=RSI_W_PATTERN&timeframe=1d&start_date=2023-01-01&end_date=2024-01-01&initial_capital=10000&position_size=1.0"
```

**Check Data Availability:**

```bash
curl "http://localhost:8000/backtest/data-availability?symbol=AAPL"
```

Expected response:
```json
{
  "available": true,
  "symbol": "AAPL",
  "timeframes": {
    "1d": {
      "start_date": "2022-01-03",
      "end_date": "2024-01-08",
      "candle_count": 504
    },
    "1h": {
      "start_date": "2022-01-03",
      "end_date": "2024-01-08",
      "candle_count": 3024
    }
  }
}
```

### 5. Using the UI

1. Start your backend server:
   ```bash
   cd backend
   python3 main.py
   ```

2. Start your frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open the dashboard and click the **"Backtest"** button in the header

4. Configure your backtest:
   - Select a strategy (MACD, RSI, RSI_W_PATTERN, etc.)
   - Choose timeframe (1m, 5m, 1h, 1d)
   - Set date range
   - Set initial capital
   - Adjust position size (0.1 to 1.0 = 10% to 100% of capital)

5. Click **"Run Backtest"** and view results:
   - Total return and percentage
   - Max drawdown
   - Sharpe ratio
   - Win rate and profit factor
   - Trade statistics
   - Complete trade history

## Features

### Timeframe Support
- **1 minute (1m)** - High-frequency trading
- **5 minutes (5m)** - Intraday trading
- **1 hour (1h)** - Swing trading
- **1 day (1d)** - Position trading

### Performance Metrics
- **Total Return** - Absolute and percentage profit/loss
- **Max Drawdown** - Largest peak-to-trough decline
- **Sharpe Ratio** - Risk-adjusted return metric
- **Win Rate** - Percentage of winning trades
- **Profit Factor** - Ratio of gross profit to gross loss
- **Trade Statistics** - Average win/loss, best/worst trades

### Strategy Support
All strategies are supported:
- MACD
- RSI
- MA_CROSSOVER
- BOLLINGER
- RSI_W_PATTERN

## Troubleshooting

### "Insufficient historical data" Error

**Cause**: Not enough candles in the backtest database for the selected timeframe and date range.

**Solution**: Load more historical data or adjust your date range.

### "Stock not found" Error

**Cause**: The stock doesn't exist in the backtest database.

**Solution**:
1. Check data availability: `curl "http://localhost:8000/backtest/data-availability?symbol=AAPL"`
2. If unavailable, load historical data for that stock

### No Data Shows in Modal

**Cause**: `BACKTEST_DATABASE_URL` not configured or database empty.

**Solution**:
1. Verify `.env` has `BACKTEST_DATABASE_URL`
2. Restart backend server
3. Load historical data

### Database Connection Error

**Cause**: Backtest database doesn't exist or wrong credentials.

**Solution**:
1. Verify database exists: `psql -l | grep stock_trader_backtest`
2. Check connection string in `.env`
3. Ensure database user has proper permissions

## Architecture Notes

### Why Separate Database?

1. **Data Isolation** - Historical data doesn't clutter live trading database
2. **Performance** - Large historical datasets don't impact live trading queries
3. **Safety** - Backtesting can't accidentally affect live positions or trades
4. **Flexibility** - Can use different data sources for backtesting

### How It Works

1. User clicks "Backtest" button
2. Frontend opens BacktestModal
3. User configures parameters (strategy, timeframe, dates)
4. Frontend calls `/backtest/run` API
5. Backend switches to backtest database
6. Fetches historical candles for date range
7. Generates strategy signals for each candle
8. Simulates trades based on signals
9. Calculates performance metrics
10. Returns results to frontend
11. Frontend displays metrics and trade history

## Next Steps

### Recommended Improvements

1. **Equity Curve Visualization** - Add a chart showing portfolio value over time
2. **Multiple Strategy Comparison** - Run multiple strategies side-by-side
3. **Parameter Optimization** - Test different strategy parameters automatically
4. **Walk-Forward Analysis** - Split data into training and testing periods
5. **Monte Carlo Simulation** - Assess strategy robustness
6. **Export Results** - Download backtest results as CSV/PDF

### Data Enhancements

1. **Automated Data Updates** - Cron job to refresh historical data
2. **Multiple Data Sources** - Support for different data providers
3. **Data Quality Checks** - Validate and clean historical data
4. **Gap Detection** - Identify and fill missing candles

## Support

For issues or questions about the backtesting system:
1. Check the logs: `tail -f backend/logs/app.log`
2. Verify data availability via API
3. Test with small date ranges first
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

---

**Status**: ✅ Fully Implemented and Ready to Use

**Key Files**:
- Backend: `database_manager.py`, `services/backtest_engine.py`, `main.py`
- Frontend: `BacktestModal.jsx`, `Dashboard.jsx`, `api.js`
- Documentation: `BACKTESTING_IMPLEMENTATION_GUIDE.md` (detailed technical docs)
