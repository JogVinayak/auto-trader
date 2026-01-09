# Stock Auto Trader - Application Context

## Overview
A paper trading (simulated) stock market application focused on Indian stocks and technical analysis. Combines a FastAPI backend with a React/Vite frontend to provide a real-time trading dashboard with multiple technical indicator strategies.

## Technology Stack

### Backend
- **FastAPI 0.115.6** - Python API framework
- **PostgreSQL 15** - Database (via psycopg)
- **SQLAlchemy 2.0.36** - ORM
- **pandas 2.2.3** - Data manipulation
- **TA (Technical Analysis)** - Indicator calculations
- **yfinance 0.2.50** - Yahoo Finance API integration
- **Pydantic 2.10.4** - Data validation

### Frontend
- **React 19.2.0** - UI library
- **Vite 7.2.4** - Build tool
- **Lightweight Charts 4.1.3** - Professional charting
- **Axios 1.13.2** - HTTP client
- **Lucide React** - Icons

### Infrastructure
- Docker Compose for local development
- CORS enabled for cross-origin requests

## Directory Structure

```
/stock-auto-trader/
├── backend/
│   ├── main.py                 # FastAPI app with endpoints
│   ├── models.py               # SQLAlchemy database models
│   ├── database.py             # Database connection & sessions
│   ├── requirements.txt        # Python dependencies
│   ├── services/
│   │   └── candle_service.py   # Yahoo Finance data sync
│   ├── strategies/             # Technical analysis strategies
│   │   ├── base.py             # Abstract base strategy
│   │   ├── macd.py             # MACD crossover
│   │   ├── rsi.py              # RSI overbought/oversold
│   │   ├── ma_crossover.py     # Moving average crossover
│   │   └── bollinger.py        # Bollinger Bands
│   ├── add_indian_stocks.py    # Populate Indian stocks
│   └── add_test_trades.py      # Demo trade data
├── frontend/
│   ├── src/
│   │   ├── main.jsx            # React entry point
│   │   ├── App.jsx             # Main component
│   │   ├── pages/
│   │   │   └── Dashboard.jsx   # Main dashboard
│   │   ├── components/         # React components
│   │   │   ├── Sidebar.jsx
│   │   │   ├── SignalsTable.jsx
│   │   │   ├── StrategyCard.jsx
│   │   │   ├── TradingChart.jsx
│   │   │   ├── TradingChartWithIndicators.jsx
│   │   │   ├── TradesTable.jsx
│   │   │   ├── ChartModal.jsx
│   │   │   └── StrategySettingsModal.jsx
│   │   └── services/
│   │       └── api.js          # Axios API layer
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── docker-compose.yml          # PostgreSQL container
└── design/                     # Design assets
```

## Database Schema

### Models
1. **Stock** - Tracked stocks (symbol, name)
2. **Candle** - OHLCV data with timeframes (1m, 5m, 1h, 1d)
3. **Trade** - Executed trades with entry/exit details
4. **Portfolio** - Cash balance and capital tracking
5. **Holding** - Current stock positions with average buy price

### Enums
- **TimeFrame**: 1m, 5m, 1h, 1d
- **TradeType**: BUY, SELL
- **StrategyType**: MACD, RSI, MA_CROSSOVER, BOLLINGER

## API Endpoints

### Health & Config
- `GET /` - Health check
- `GET /strategies` - List available strategies

### Stock Management
- `GET /stocks` - List all stocks
- `POST /stocks` - Add new stock
- `DELETE /stocks/{symbol}` - Remove stock

### Portfolio
- `GET /portfolio` - Portfolio status (balance, holdings, P&L)
- `POST /portfolio/reset` - Reset to initial capital

### Candles (Price Data)
- `GET /candles/{symbol}` - Historical candles
- `POST /candles/{symbol}/sync` - Sync from Yahoo Finance
- `GET /candles/{symbol}/latest` - Latest candle timestamp
- `GET /candles/{symbol}/sync-status` - Sync statistics

### Trading Signals
- `GET /signals/{symbol}` - Get signals for strategies
  - Returns: signal (BUY/SELL/HOLD), strength (0-100), reason, indicators

### Trades
- `GET /trades` - Trade history

## Trading Strategies

### 1. MACD (Moving Average Convergence Divergence)
- **BUY**: MACD line crosses above signal line
- **SELL**: MACD line crosses below signal line
- **Params**: fast=12, slow=26, signal=9

### 2. RSI (Relative Strength Index)
- **BUY**: RSI crosses above 30 (oversold)
- **SELL**: RSI crosses below 70 (overbought)
- **Params**: period=14, oversold=30, overbought=70

### 3. Moving Average Crossover
- **BUY**: Short MA (20) crosses above Long MA (50) - Golden Cross
- **SELL**: Short MA crosses below Long MA - Death Cross
- Uses EMA by default

### 4. Bollinger Bands
- **BUY**: Price at/below lower band (oversold)
- **SELL**: Price at/above upper band (overbought)
- **Params**: period=20, std_dev=2.0

## Key Features

1. **Paper Trading** - Simulated trading with $10,000 starting capital
2. **Multi-Strategy Analysis** - 4 complementary technical indicators
3. **Real-time Data** - Yahoo Finance API with multiple timeframes
4. **Signal Strength** - 0-100 strength metric per signal
5. **Trade History** - Complete trade logging with P&L tracking
6. **Portfolio Tracking** - Cash balance, holdings value, overall P&L
7. **Indian Stock Focus** - Pre-configured NSE/BSE stocks
8. **Interactive Charts** - Candlestick charts with technical overlays

## Configuration

### Backend (.env)
```
DATABASE_URL=postgresql://...
INITIAL_CAPITAL=10000
DEBUG=True
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

## Running the Application

### Start Database
```bash
docker-compose up -d
```

### Backend
```bash
cd stock-auto-trader/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd stock-auto-trader/frontend
npm install
npm run dev
```
