from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime
import os

from database import get_db, engine
from models import Base, Stock, Candle, Trade, Portfolio, Holding, StrategySettings, TimeFrame, TradeType, StrategyType

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
    tf_map = {
        "1m": TimeFrame.M1, "5m": TimeFrame.M5, "15m": TimeFrame.M15, "30m": TimeFrame.M30,
        "1h": TimeFrame.H1, "2h": TimeFrame.H2, "3h": TimeFrame.H3, "4h": TimeFrame.H4, "5h": TimeFrame.H5,
        "1d": TimeFrame.D1
    }
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe. Use: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 5h, 1d")
    
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
    
    tf_map = {
        "1m": TimeFrame.M1, "5m": TimeFrame.M5, "15m": TimeFrame.M15, "30m": TimeFrame.M30,
        "1h": TimeFrame.H1, "2h": TimeFrame.H2, "3h": TimeFrame.H3, "4h": TimeFrame.H4, "5h": TimeFrame.H5,
        "1d": TimeFrame.D1
    }
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
    - Automatically calculates indicators after sync
    """
    from services.candle_service import sync_candles, sync_all_timeframes
    from services.indicator_service import calculate_indicators_for_candles

    tf_map = {
        "1m": TimeFrame.M1, "5m": TimeFrame.M5, "15m": TimeFrame.M15, "30m": TimeFrame.M30,
        "1h": TimeFrame.H1, "2h": TimeFrame.H2, "3h": TimeFrame.H3, "4h": TimeFrame.H4, "5h": TimeFrame.H5,
        "1d": TimeFrame.D1
    }

    # Get stock_id for indicator calculation
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()

    if timeframe:
        tf = tf_map.get(timeframe)
        if not tf:
            raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 5h, 1d")
        result = sync_candles(db, symbol, tf, full_sync)

        # Calculate indicators after sync
        if stock and result.get("new_candles", 0) > 0:
            indicator_result = calculate_indicators_for_candles(db, stock.id, tf)
            result["indicators_calculated"] = indicator_result

        return result
    else:
        results = sync_all_timeframes(db, symbol, full_sync)

        # Calculate indicators for all timeframes
        if stock:
            for tf_name, tf in tf_map.items():
                indicator_result = calculate_indicators_for_candles(db, stock.id, tf)
                # Find matching result and add indicator info
                for r in results:
                    if r.get("timeframe") == tf_name:
                        r["indicators_calculated"] = indicator_result

        return {"symbol": symbol.upper(), "results": results}


@app.get("/candles/{symbol}/sync-status", tags=["Candles"])
def get_candle_sync_status(symbol: str, db: Session = Depends(get_db)):
    """Get sync status for a symbol (candle counts and latest timestamps)"""
    from services.candle_service import get_sync_status
    return get_sync_status(db, symbol)


@app.post("/candles/cleanup-duplicates", tags=["Candles"])
def cleanup_duplicate_candles(symbol: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Remove duplicate candles from the database.
    If symbol is provided, only cleans duplicates for that symbol.
    Otherwise, cleans all duplicates.
    """
    from services.candle_service import remove_duplicate_candles
    return remove_duplicate_candles(db, symbol)


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
def _get_strategy_with_settings(strategy_name: str, db: Session):
    """Create strategy instance with settings from database"""
    from strategies import STRATEGIES

    strategy_class = STRATEGIES.get(strategy_name.upper())
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    # Get settings from database
    try:
        strategy_type = StrategyType(strategy_name.upper())
        setting = db.query(StrategySettings).filter(StrategySettings.strategy == strategy_type).first()
    except ValueError:
        setting = None

    # Create strategy with custom settings if available
    if setting:
        if strategy_name.upper() == "MACD":
            return strategy_class(
                fast_period=setting.macd_fast_period,
                slow_period=setting.macd_slow_period,
                signal_period=setting.macd_signal_period
            )
        elif strategy_name.upper() == "RSI":
            return strategy_class(
                period=setting.rsi_period,
                overbought=setting.rsi_overbought,
                oversold=setting.rsi_oversold
            )
        elif strategy_name.upper() == "MA_CROSSOVER":
            return strategy_class(
                short_period=setting.ma_short_period,
                long_period=setting.ma_long_period,
                ma_type=setting.ma_type
            )
        elif strategy_name.upper() == "BOLLINGER":
            return strategy_class(
                period=setting.bollinger_period,
                std_dev=setting.bollinger_std_dev
            )

    # Return with default settings
    return strategy_class()


def _get_mtf_candle_data(db: Session, stock_id: int) -> Dict:
    """Fetch candle data for all 10 timeframes for MTF_EMA strategy"""
    import pandas as pd

    tf_map = {
        "1m": TimeFrame.M1,
        "5m": TimeFrame.M5,
        "15m": TimeFrame.M15,
        "30m": TimeFrame.M30,
        "1h": TimeFrame.H1,
        "2h": TimeFrame.H2,
        "3h": TimeFrame.H3,
        "4h": TimeFrame.H4,
        "5h": TimeFrame.H5,
        "1D": TimeFrame.D1
    }

    mtf_data = {}
    for tf_name, tf_enum in tf_map.items():
        candles = (
            db.query(Candle)
            .filter(Candle.stock_id == stock_id, Candle.timeframe == tf_enum)
            .order_by(Candle.timestamp.asc())
            .all()
        )

        if len(candles) >= 305:  # Need enough for EMA 300
            df = pd.DataFrame([{
                "timestamp": c.timestamp,
                "close": c.close
            } for c in candles])
            mtf_data[tf_name] = df

    return mtf_data


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
    from strategies import STRATEGIES
    import pandas as pd

    # Get candles
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found. Sync it first.")

    tf_map = {
        "1m": TimeFrame.M1, "5m": TimeFrame.M5, "15m": TimeFrame.M15, "30m": TimeFrame.M30,
        "1h": TimeFrame.H1, "2h": TimeFrame.H2, "3h": TimeFrame.H3, "4h": TimeFrame.H4, "5h": TimeFrame.H5,
        "1d": TimeFrame.D1
    }
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 5h, 1d")

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
        # Single strategy with DB settings
        try:
            strat = _get_strategy_with_settings(strategy, db)

            # MTF_EMA needs data from all timeframes
            if strategy.upper() == "MTF_EMA":
                mtf_data = _get_mtf_candle_data(db, stock.id)
                result = strat.calculate_mtf(df, mtf_data)
            else:
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
        # All strategies with DB settings
        signals = []
        for name in STRATEGIES.keys():
            strat = _get_strategy_with_settings(name, db)

            # MTF_EMA needs data from all timeframes
            if name == "MTF_EMA":
                mtf_data = _get_mtf_candle_data(db, stock.id)
                result = strat.calculate_mtf(df, mtf_data)
            else:
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


# ============ STRATEGY SETTINGS ============
@app.get("/strategy-settings", tags=["Strategy Settings"])
def get_all_strategy_settings(db: Session = Depends(get_db)):
    """Get settings for all strategies"""
    settings = {}
    for strategy_type in StrategyType:
        setting = db.query(StrategySettings).filter(StrategySettings.strategy == strategy_type).first()
        if setting:
            settings[strategy_type.value] = _format_strategy_settings(setting, strategy_type)
        else:
            settings[strategy_type.value] = _get_default_settings(strategy_type)
    return settings


@app.get("/strategy-settings/{strategy}", tags=["Strategy Settings"])
def get_strategy_settings(strategy: str, db: Session = Depends(get_db)):
    """Get settings for a specific strategy"""
    try:
        strategy_type = StrategyType(strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

    setting = db.query(StrategySettings).filter(StrategySettings.strategy == strategy_type).first()

    if setting:
        return _format_strategy_settings(setting, strategy_type)
    else:
        return _get_default_settings(strategy_type)


@app.post("/strategy-settings/{strategy}", tags=["Strategy Settings"])
def save_strategy_settings(strategy: str, settings: dict, db: Session = Depends(get_db)):
    """Save settings for a specific strategy"""
    try:
        strategy_type = StrategyType(strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

    # Get or create settings record
    setting = db.query(StrategySettings).filter(StrategySettings.strategy == strategy_type).first()
    if not setting:
        setting = StrategySettings(strategy=strategy_type)
        db.add(setting)

    # Update settings based on strategy type
    if strategy_type == StrategyType.MACD:
        if "fast_period" in settings:
            setting.macd_fast_period = settings["fast_period"]
        if "slow_period" in settings:
            setting.macd_slow_period = settings["slow_period"]
        if "signal_period" in settings:
            setting.macd_signal_period = settings["signal_period"]

    elif strategy_type == StrategyType.RSI:
        if "period" in settings:
            setting.rsi_period = settings["period"]
        if "overbought" in settings:
            setting.rsi_overbought = settings["overbought"]
        if "oversold" in settings:
            setting.rsi_oversold = settings["oversold"]

    elif strategy_type == StrategyType.MA_CROSSOVER:
        if "short_period" in settings:
            setting.ma_short_period = settings["short_period"]
        if "long_period" in settings:
            setting.ma_long_period = settings["long_period"]
        if "ma_type" in settings:
            setting.ma_type = settings["ma_type"]

    elif strategy_type == StrategyType.BOLLINGER:
        if "period" in settings:
            setting.bollinger_period = settings["period"]
        if "std_dev" in settings:
            setting.bollinger_std_dev = settings["std_dev"]

    setting.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(setting)

    return {"message": f"{strategy} settings saved", "settings": _format_strategy_settings(setting, strategy_type)}


def _format_strategy_settings(setting: StrategySettings, strategy_type: StrategyType) -> dict:
    """Format strategy settings for API response"""
    if strategy_type == StrategyType.MACD:
        return {
            "fast_period": setting.macd_fast_period,
            "slow_period": setting.macd_slow_period,
            "signal_period": setting.macd_signal_period,
        }
    elif strategy_type == StrategyType.RSI:
        return {
            "period": setting.rsi_period,
            "overbought": setting.rsi_overbought,
            "oversold": setting.rsi_oversold,
        }
    elif strategy_type == StrategyType.MA_CROSSOVER:
        return {
            "short_period": setting.ma_short_period,
            "long_period": setting.ma_long_period,
            "ma_type": setting.ma_type,
        }
    elif strategy_type == StrategyType.BOLLINGER:
        return {
            "period": setting.bollinger_period,
            "std_dev": setting.bollinger_std_dev,
        }
    return {}


def _get_default_settings(strategy_type: StrategyType) -> dict:
    """Get default settings for a strategy"""
    defaults = {
        StrategyType.MACD: {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        StrategyType.RSI: {"period": 14, "overbought": 70, "oversold": 30},
        StrategyType.MA_CROSSOVER: {"short_period": 20, "long_period": 50, "ma_type": "EMA"},
        StrategyType.BOLLINGER: {"period": 20, "std_dev": 2.0},
    }
    return defaults.get(strategy_type, {})


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