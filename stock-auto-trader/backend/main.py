from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os

from database import get_db, engine
from models import Base, Stock, Candle, Trade, Portfolio, Holding, TimeFrame, TradeType, StrategyType

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Stock Auto Trader API",
    description="Paper trading API with strategy-based signals",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ HEALTH CHECK ============
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Stock Auto Trader API is running"}


# ============ STOCKS ============
@app.get("/stocks", tags=["Stocks"])
def get_stocks(db: Session = Depends(get_db)):
    """Get all tracked stocks"""
    stocks = db.query(Stock).all()
    return [{"id": s.id, "symbol": s.symbol, "name": s.name} for s in stocks]


@app.post("/stocks", tags=["Stocks"])
def add_stock(symbol: str, name: Optional[str] = None, db: Session = Depends(get_db)):
    """Add a new stock to track"""
    symbol = symbol.upper().strip()
    
    # Check if exists
    existing = db.query(Stock).filter(Stock.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stock {symbol} already exists")
    
    stock = Stock(symbol=symbol, name=name or symbol)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    
    return {"id": stock.id, "symbol": stock.symbol, "name": stock.name}


@app.delete("/stocks/{symbol}", tags=["Stocks"])
def delete_stock(symbol: str, db: Session = Depends(get_db)):
    """Remove a stock from tracking"""
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    db.delete(stock)
    db.commit()
    return {"message": f"Stock {symbol} deleted"}


# ============ PORTFOLIO ============
@app.get("/portfolio", tags=["Portfolio"])
def get_portfolio(db: Session = Depends(get_db)):
    """Get current portfolio status"""
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        # Initialize portfolio
        portfolio = Portfolio(cash_balance=10000.0, initial_capital=10000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    
    # Get holdings
    holdings = db.query(Holding).all()
    holdings_list = []
    total_holdings_value = 0
    
    for h in holdings:
        stock = db.query(Stock).filter(Stock.id == h.stock_id).first()
        if stock and h.quantity > 0:
            holdings_list.append({
                "symbol": stock.symbol,
                "quantity": h.quantity,
                "avg_buy_price": h.avg_buy_price,
                "current_value": h.quantity * h.avg_buy_price  # Will update with live price later
            })
            total_holdings_value += h.quantity * h.avg_buy_price
    
    total_value = portfolio.cash_balance + total_holdings_value
    pnl = total_value - portfolio.initial_capital
    pnl_percent = (pnl / portfolio.initial_capital) * 100
    
    return {
        "cash_balance": round(portfolio.cash_balance, 2),
        "initial_capital": portfolio.initial_capital,
        "holdings_value": round(total_holdings_value, 2),
        "total_value": round(total_value, 2),
        "pnl": round(pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "holdings": holdings_list
    }


@app.post("/portfolio/reset", tags=["Portfolio"])
def reset_portfolio(db: Session = Depends(get_db)):
    """Reset portfolio to initial capital"""
    # Delete all holdings
    db.query(Holding).delete()
    
    # Delete all trades
    db.query(Trade).delete()
    
    # Reset portfolio
    portfolio = db.query(Portfolio).first()
    if portfolio:
        portfolio.cash_balance = 10000.0
        portfolio.initial_capital = 10000.0
    else:
        portfolio = Portfolio(cash_balance=10000.0, initial_capital=10000.0)
        db.add(portfolio)
    
    db.commit()
    return {"message": "Portfolio reset to $10,000"}


# ============ CANDLES ============
@app.get("/candles/{symbol}", tags=["Candles"])
def get_candles(
    symbol: str,
    timeframe: str = "1d",
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db)
):
    """Get candles for a stock"""
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    # Map timeframe string to enum
    tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe. Use: 1m, 5m, 1h, 1d")
    
    candles = (
        db.query(Candle)
        .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
        .order_by(Candle.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "timestamp": c.timestamp.isoformat(),
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        }
        for c in reversed(candles)  # Return in chronological order
    ]


@app.get("/candles/{symbol}/latest", tags=["Candles"])
def get_latest_candle(symbol: str, timeframe: str = "1d", db: Session = Depends(get_db)):
    """Get the latest candle timestamp for incremental sync"""
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        return {"latest_timestamp": None}
    
    tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
    tf = tf_map.get(timeframe)
    
    latest = (
        db.query(Candle)
        .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
        .order_by(Candle.timestamp.desc())
        .first()
    )
    
    return {"latest_timestamp": latest.timestamp.isoformat() if latest else None}


# ============ CANDLE SYNC ============
@app.post("/candles/{symbol}/sync", tags=["Candles"])
def sync_stock_candles(
    symbol: str,
    timeframe: Optional[str] = None,
    full_sync: bool = False,
    db: Session = Depends(get_db)
):
    """
    Sync candles from Yahoo Finance
    - timeframe: 1m, 5m, 1h, 1d (if not provided, syncs all)
    - full_sync: if True, fetches all available history
    """
    from services.candle_service import sync_candles, sync_all_timeframes
    
    tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
    
    if timeframe:
        tf = tf_map.get(timeframe)
        if not tf:
            raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 1m, 5m, 1h, 1d")
        result = sync_candles(db, symbol, tf, full_sync)
        return result
    else:
        results = sync_all_timeframes(db, symbol, full_sync)
        return {"symbol": symbol.upper(), "results": results}


@app.get("/candles/{symbol}/sync-status", tags=["Candles"])
def get_candle_sync_status(symbol: str, db: Session = Depends(get_db)):
    """Get sync status for a symbol (candle counts and latest timestamps)"""
    from services.candle_service import get_sync_status
    return get_sync_status(db, symbol)


# ============ TRADES ============
@app.get("/trades", tags=["Trades"])
def get_trades(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db)
):
    """Get trade history"""
    query = db.query(Trade).order_by(Trade.timestamp.desc())
    
    if symbol:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if stock:
            query = query.filter(Trade.stock_id == stock.id)
    
    trades = query.limit(limit).all()
    
    result = []
    for t in trades:
        stock = db.query(Stock).filter(Stock.id == t.stock_id).first()
        result.append({
            "id": t.id,
            "symbol": stock.symbol if stock else "Unknown",
            "type": t.trade_type.value,
            "strategy": t.strategy.value,
            "quantity": t.quantity,
            "price": t.price,
            "total_value": t.total_value,
            "timestamp": t.timestamp.isoformat(),
            "notes": t.notes
        })
    
    return result


# ============ SIGNALS ============
@app.get("/signals/{symbol}", tags=["Signals"])
def get_signals(
    symbol: str,
    timeframe: str = "1d",
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get trading signals for a stock
    - strategy: MACD, RSI, MA_CROSSOVER, BOLLINGER (if not provided, returns all)
    """
    from strategies import get_strategy, get_all_strategies, STRATEGIES
    import pandas as pd
    
    # Get candles
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found. Sync it first.")
    
    tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 1m, 5m, 1h, 1d")
    
    candles = (
        db.query(Candle)
        .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
        .order_by(Candle.timestamp.asc())
        .all()
    )
    
    if len(candles) < 50:
        raise HTTPException(status_code=400, detail=f"Insufficient candles ({len(candles)}). Need at least 50.")
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        "timestamp": c.timestamp,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles])
    
    current_price = df['close'].iloc[-1]
    
    # Calculate signals
    if strategy:
        # Single strategy
        try:
            strat = get_strategy(strategy)
            result = strat.calculate(df)
            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "current_price": round(current_price, 2),
                "signals": [result]
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # All strategies
        signals = []
        for name, strat_class in STRATEGIES.items():
            strat = strat_class()
            result = strat.calculate(df)
            signals.append(result)
        
        # Calculate overall recommendation
        buy_count = sum(1 for s in signals if s["signal"] == "BUY")
        sell_count = sum(1 for s in signals if s["signal"] == "SELL")
        
        if buy_count > sell_count:
            overall = "BUY"
        elif sell_count > buy_count:
            overall = "SELL"
        else:
            overall = "HOLD"
        
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "overall_signal": overall,
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "signals": signals
        }


@app.get("/strategies", tags=["Signals"])
def list_strategies():
    """List all available trading strategies"""
    from strategies import STRATEGIES
    
    return {
        "strategies": [
            {
                "name": name,
                "description": strat_class().description
            }
            for name, strat_class in STRATEGIES.items()
        ]
    }


# ============ STARTUP ============
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from database import get_db_session
    
    with get_db_session() as db:
        # Ensure portfolio exists
        if not db.query(Portfolio).first():
            portfolio = Portfolio(cash_balance=10000.0, initial_capital=10000.0)
            db.add(portfolio)
    
    print("✅ Stock Auto Trader API started!")


# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)