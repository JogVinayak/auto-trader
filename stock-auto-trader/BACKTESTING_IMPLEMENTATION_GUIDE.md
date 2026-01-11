# Backtesting System Implementation Guide

## Overview

This guide shows you how to implement a comprehensive backtesting system with:
- **Separate backtest database** for historical data
- **Timeframe selection** (1m, 5m, 1h, 1d)
- **Date range selection** for backtesting period
- **Multiple strategy comparison**
- **Performance metrics** and visualization

---

## Architecture

### Database Strategy

**Option 1: Separate PostgreSQL Database (Recommended)**
```
Live Database: stock_trader_live
Backtest Database: stock_trader_backtest
```

**Option 2: Same Database, Different Schema**
```
Schema: public (live data)
Schema: backtest (historical data)
```

**Option 3: Same Database, Prefix Tables**
```
Tables: stocks, candles, trades (live)
Tables: bt_stocks, bt_candles, bt_trades (backtest)
```

---

## Implementation Steps

### Step 1: Environment Configuration

Add to `.env`:
```bash
# Live database
DATABASE_URL=postgresql://user:pass@localhost/stock_trader_live

# Backtest database
BACKTEST_DATABASE_URL=postgresql://user:pass@localhost/stock_trader_backtest

# Or use same database with schema
DATABASE_SCHEMA=public
BACKTEST_SCHEMA=backtest
```

### Step 2: Create Backtest Database

**PostgreSQL:**
```sql
-- Create backtest database
CREATE DATABASE stock_trader_backtest;

-- Or create backtest schema (if using same database)
CREATE SCHEMA IF NOT EXISTS backtest;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE stock_trader_backtest TO your_user;
-- Or for schema
GRANT ALL PRIVILEGES ON SCHEMA backtest TO your_user;
```

### Step 3: Database Connection Manager

Create `backend/database_manager.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    """Manages connections to live and backtest databases"""

    def __init__(self):
        self.live_url = os.getenv("DATABASE_URL")
        self.backtest_url = os.getenv("BACKTEST_DATABASE_URL", self.live_url)

        self.live_engine = create_engine(self.live_url, echo=False)
        self.backtest_engine = create_engine(self.backtest_url, echo=False)

        self.LiveSession = sessionmaker(bind=self.live_engine)
        self.BacktestSession = sessionmaker(bind=self.backtest_engine)

    def get_live_session(self):
        return self.LiveSession()

    def get_backtest_session(self):
        return self.BacktestSession()

    def switch_to_live(self):
        """Switch to live database"""
        return self.get_live_session()

    def switch_to_backtest(self):
        """Switch to backtest database"""
        return self.get_backtest_session()

# Global instance
db_manager = DatabaseManager()
```

### Step 4: Backtest API Endpoints

Add to `backend/main.py`:
```python
from services.backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from database_manager import db_manager
import pandas as pd

# ============ BACKTEST ENDPOINTS ============

@app.post("/backtest/run", tags=["Backtest"])
def run_backtest(
    symbol: str,
    strategy: str,
    timeframe: str = "1d",
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    initial_capital: float = 10000.0,
    position_size: float = 1.0,
    db: Session = Depends(get_db)
):
    """
    Run backtest for a strategy on historical data

    Args:
        symbol: Stock symbol
        strategy: Strategy name (MACD, RSI, RSI_W_PATTERN, etc.)
        timeframe: Candle timeframe (1m, 5m, 1h, 1d)
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        initial_capital: Starting capital
        position_size: Position size as % of capital (0-1)
    """
    try:
        # Get stock
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        # Get candles from backtest database
        bt_db = db_manager.get_backtest_session()

        tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
        tf = tf_map.get(timeframe)

        # Fetch historical candles
        from datetime import datetime
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        candles = (
            bt_db.query(Candle)
            .filter(
                Candle.stock_id == stock.id,
                Candle.timeframe == tf,
                Candle.timestamp >= start_dt,
                Candle.timestamp <= end_dt
            )
            .order_by(Candle.timestamp.asc())
            .all()
        )

        if len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient historical data. Found {len(candles)} candles, need at least 50."
            )

        # Convert to DataFrame
        df = pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        } for c in candles])

        # Get strategy with settings
        strat = _get_strategy_with_settings(strategy, db)

        # Generate signals for each candle
        signals = []
        for i in range(len(df)):
            # Get data up to current point (avoid look-ahead bias)
            df_subset = df.iloc[:i+1]
            if len(df_subset) >= 50:  # Minimum data for signal
                result = strat.calculate(df_subset)
                signals.append(result)
            else:
                signals.append({"signal": "HOLD", "strength": 0})

        # Run backtest
        config = BacktestConfig(
            symbol=symbol,
            strategy_name=strategy,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size=position_size
        )

        engine = BacktestEngine(config)
        result = engine.run(df, signals)

        # Format response
        return {
            "config": {
                "symbol": result.config.symbol,
                "strategy": result.config.strategy_name,
                "timeframe": result.config.timeframe,
                "start_date": result.config.start_date,
                "end_date": result.config.end_date,
                "initial_capital": result.config.initial_capital
            },
            "metrics": {
                "total_return": round(result.total_return, 2),
                "total_return_percent": round(result.total_return_percent, 2),
                "max_drawdown": round(result.max_drawdown, 2),
                "max_drawdown_percent": round(result.max_drawdown_percent, 2),
                "sharpe_ratio": round(result.sharpe_ratio, 2),
                "win_rate": round(result.win_rate, 2),
                "profit_factor": round(result.profit_factor, 2),
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "avg_win": round(result.avg_win, 2),
                "avg_loss": round(result.avg_loss, 2),
                "avg_trade": round(result.avg_trade, 2),
                "best_trade": round(result.best_trade, 2),
                "worst_trade": round(result.worst_trade, 2),
                "avg_trade_duration_hours": round(result.avg_trade_duration, 2)
            },
            "equity_curve": [round(e, 2) for e in result.equity_curve],
            "equity_dates": [str(d) for d in result.equity_dates],
            "trades": [
                {
                    "entry_date": str(t.entry_date),
                    "entry_price": t.entry_price,
                    "exit_date": str(t.exit_date) if t.exit_date else None,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "pnl": round(t.pnl, 2),
                    "pnl_percent": round(t.pnl_percent, 2),
                    "type": t.position_type.value
                }
                for t in result.trades
            ][:50]  # Limit to 50 trades for response size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        bt_db.close()


@app.get("/backtest/data-availability", tags=["Backtest"])
def get_backtest_data_availability(symbol: str):
    """Get available date range for backtesting a symbol"""
    bt_db = db_manager.get_backtest_session()

    try:
        stock = bt_db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return {"available": False, "message": f"Stock {symbol} not found"}

        # Get earliest and latest candles for each timeframe
        timeframes_data = {}

        for tf_name, tf_enum in [("1m", TimeFrame.M1), ("5m", TimeFrame.M5),
                                   ("1h", TimeFrame.H1), ("1d", TimeFrame.D1)]:
            earliest = (
                bt_db.query(Candle)
                .filter(Candle.stock_id == stock.id, Candle.timeframe == tf_enum)
                .order_by(Candle.timestamp.asc())
                .first()
            )

            latest = (
                bt_db.query(Candle)
                .filter(Candle.stock_id == stock.id, Candle.timeframe == tf_enum)
                .order_by(Candle.timestamp.desc())
                .first()
            )

            count = (
                bt_db.query(Candle)
                .filter(Candle.stock_id == stock.id, Candle.timeframe == tf_enum)
                .count()
            )

            if earliest and latest:
                timeframes_data[tf_name] = {
                    "start_date": str(earliest.timestamp.date()),
                    "end_date": str(latest.timestamp.date()),
                    "candle_count": count
                }

        return {
            "available": len(timeframes_data) > 0,
            "symbol": symbol,
            "timeframes": timeframes_data
        }

    finally:
        bt_db.close()
```

### Step 5: Frontend - Backtest Modal Component

Create `frontend/src/components/BacktestModal.jsx`:
```javascript
import { useState } from 'react';
import { createPortal } from 'react-dom';
import { X, PlayCircle, Calendar, Clock, DollarSign } from 'lucide-react';
import './BacktestModal.css';

const BacktestModal = ({ isOpen, onClose, symbol, strategies }) => {
  const [config, setConfig] = useState({
    strategy: strategies[0]?.name || 'MACD',
    timeframe: '1d',
    startDate: '2023-01-01',
    endDate: '2024-01-01',
    initialCapital: 10000,
    positionSize: 1.0
  });

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const handleRun = async () => {
    setRunning(true);
    try {
      const response = await fetch(
        `/backtest/run?` + new URLSearchParams({
          symbol,
          strategy: config.strategy,
          timeframe: config.timeframe,
          start_date: config.startDate,
          end_date: config.endDate,
          initial_capital: config.initialCapital,
          position_size: config.positionSize
        }),
        { method: 'POST' }
      );

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Backtest failed:', error);
    } finally {
      setRunning(false);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="backtest-modal-overlay" onClick={onClose}>
      <div className="backtest-modal" onClick={(e) => e.stopPropagation()}>
        <div className="backtest-header">
          <h2>Backtest Strategy: {symbol}</h2>
          <button onClick={onClose}><X /></button>
        </div>

        <div className="backtest-config">
          <div className="config-group">
            <label>Strategy</label>
            <select value={config.strategy} onChange={(e) => setConfig({...config, strategy: e.target.value})}>
              {strategies.map(s => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>

          <div className="config-group">
            <label><Clock size={16} /> Timeframe</label>
            <select value={config.timeframe} onChange={(e) => setConfig({...config, timeframe: e.target.value})}>
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="1d">1 Day</option>
            </select>
          </div>

          <div className="config-row">
            <div className="config-group">
              <label><Calendar size={16} /> Start Date</label>
              <input type="date" value={config.startDate} onChange={(e) => setConfig({...config, startDate: e.target.value})} />
            </div>

            <div className="config-group">
              <label><Calendar size={16} /> End Date</label>
              <input type="date" value={config.endDate} onChange={(e) => setConfig({...config, endDate: e.target.value})} />
            </div>
          </div>

          <div className="config-group">
            <label><DollarSign size={16} /> Initial Capital</label>
            <input type="number" value={config.initialCapital} onChange={(e) => setConfig({...config, initialCapital: Number(e.target.value)})} />
          </div>

          <button className="btn btn-primary" onClick={handleRun} disabled={running}>
            <PlayCircle size={16} />
            {running ? 'Running...' : 'Run Backtest'}
          </button>
        </div>

        {result && (
          <div className="backtest-results">
            <h3>Results</h3>
            <div className="metrics-grid">
              <div className="metric">
                <span>Total Return</span>
                <strong className={result.metrics.total_return >= 0 ? 'positive' : 'negative'}>
                  ${result.metrics.total_return} ({result.metrics.total_return_percent}%)
                </strong>
              </div>
              <div className="metric">
                <span>Max Drawdown</span>
                <strong className="negative">-{result.metrics.max_drawdown_percent}%</strong>
              </div>
              <div className="metric">
                <span>Sharpe Ratio</span>
                <strong>{result.metrics.sharpe_ratio}</strong>
              </div>
              <div className="metric">
                <span>Win Rate</span>
                <strong>{result.metrics.win_rate}%</strong>
              </div>
              <div className="metric">
                <span>Total Trades</span>
                <strong>{result.metrics.total_trades}</strong>
              </div>
              <div className="metric">
                <span>Profit Factor</span>
                <strong>{result.metrics.profit_factor}</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

export default BacktestModal;
```

---

## Quick Setup Instructions

### 1. Create Backtest Database
```bash
# PostgreSQL
createdb stock_trader_backtest

# Copy structure from live database
pg_dump stock_trader_live --schema-only | psql stock_trader_backtest
```

### 2. Load Historical Data
```bash
# Run this script to populate backtest database with historical data
python3 backend/scripts/load_historical_data.py
```

### 3. Update .env
```
BACKTEST_DATABASE_URL=postgresql://user:pass@localhost/stock_trader_backtest
```

### 4. Test Backtest API
```bash
curl -X POST "http://localhost:8000/backtest/run?symbol=AAPL&strategy=RSI_W_PATTERN&timeframe=1d&start_date=2023-01-01&end_date=2024-01-01"
```

---

## Summary

**Files Created:**
- ✅ `backend/services/backtest_engine.py` - Backtesting logic
- 📝 `backend/database_manager.py` - Dual database manager (create this)
- 📝 `frontend/src/components/BacktestModal.jsx` - UI (create this)

**Next Steps:**
1. Create backtest database
2. Implement database_manager.py
3. Add backtest endpoints to main.py
4. Create BacktestModal component
5. Load historical data
6. Run your first backtest!

Would you like me to implement any specific part of this system now?
