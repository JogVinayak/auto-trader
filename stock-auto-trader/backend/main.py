from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime
import os
import logging

from database import get_db, engine
from models import Base, Stock, Candle, Trade, Portfolio, Holding, StrategySettings, TimeFrame, TradeType, StrategyType, IndicatorValue

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

# Helper function to get timeframe mapping
def get_timeframe_map():
    """Returns a dict mapping timeframe strings to TimeFrame enum values"""
    return {tf.value: tf for tf in TimeFrame}


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
def add_stock(
    symbol: str,
    name: Optional[str] = None,
    auto_sync: bool = True,
    db: Session = Depends(get_db)
):
    """Add a new stock to track and optionally sync candle data"""
    from services.candle_service import sync_all_timeframes, get_or_create_stock
    from services.indicator_service import calculate_indicators_for_candles

    symbol = symbol.upper().strip()

    # Normalize Binance-format symbols (BTCUSDT -> BTC, SOLUSDT -> SOL)
    if symbol.endswith('USDT') and not symbol.startswith('^'):
        # Convert Binance format to simple crypto symbol
        normalized = symbol.replace('USDT', '')
        if len(normalized) <= 6 and '.' not in normalized:
            logger = logging.getLogger(__name__)
            logger.info(f"📍 [ADD_STOCK] Normalizing Binance symbol {symbol} to {normalized}")
            symbol = normalized

    # Also handle Yahoo Finance crypto format (-USD suffix)
    # Keep -USD for now as it's the standard Yahoo Finance format for crypto
    # But remove it if user wants clean symbols
    # Actually, let's normalize to clean symbols without -USD
    if symbol.endswith('-USD') and not symbol.startswith('^'):
        base = symbol.replace('-USD', '')
        if len(base) <= 6 and '.' not in base:
            logger = logging.getLogger(__name__)
            logger.info(f"📍 [ADD_STOCK] Normalizing Yahoo crypto symbol {symbol} to {base}")
            symbol = base

    # Check if exists
    existing = db.query(Stock).filter(Stock.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stock {symbol} already exists")

    # Use get_or_create_stock to fetch name from Yahoo/Binance if not provided
    stock = get_or_create_stock(db, symbol)
    if name:
        stock.name = name
        db.commit()

    result = {"id": stock.id, "symbol": stock.symbol, "name": stock.name}

    # Auto sync candle data
    if auto_sync:
        sync_results = sync_all_timeframes(db, symbol, full_sync=False)
        result["sync_results"] = sync_results

        # Calculate indicators for all timeframes
        tf_map = get_timeframe_map()
        for tf_name, tf in tf_map.items():
            calculate_indicators_for_candles(db, stock.id, tf)

    return result


@app.delete("/stocks/{symbol}", tags=["Stocks"])
def delete_stock(symbol: str, db: Session = Depends(get_db)):
    """Remove a stock and all its related data (candles, indicators, trades, holdings)"""
    from sqlalchemy import text

    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    stock_id = stock.id

    # Delete in order to respect foreign key constraints
    # 1. Delete indicator_values (references candles)
    deleted_indicators = db.execute(
        text("DELETE FROM indicator_values WHERE candle_id IN (SELECT id FROM candles WHERE stock_id = :stock_id)"),
        {"stock_id": stock_id}
    ).rowcount

    # 2. Delete candles
    deleted_candles = db.query(Candle).filter(Candle.stock_id == stock_id).delete()

    # 3. Delete trades for this stock
    deleted_trades = db.query(Trade).filter(Trade.stock_id == stock_id).delete()

    # 4. Delete holdings for this stock
    deleted_holdings = db.query(Holding).filter(Holding.stock_id == stock_id).delete()

    # 5. Finally delete the stock
    db.delete(stock)
    db.commit()

    return {
        "message": f"Stock {symbol} and all related data deleted",
        "deleted": {
            "indicator_values": deleted_indicators,
            "candles": deleted_candles,
            "trades": deleted_trades,
            "holdings": deleted_holdings
        }
    }


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
    tf_map = get_timeframe_map()
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
    
    tf_map = get_timeframe_map()
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
    import logging
    import yfinance as yf
    from datetime import datetime
    from services.candle_service import sync_candles, sync_all_timeframes
    from services.indicator_service import calculate_indicators_for_candles

    logger = logging.getLogger(__name__)
    logger.info(f"🔄 [SYNC] Starting sync for {symbol.upper()}, timeframe={timeframe}, full_sync={full_sync}")

    # Map string to TimeFrame enum
    tf_map = get_timeframe_map()

    # Get stock_id for indicator calculation
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        logger.error(f"❌ [SYNC] Stock {symbol.upper()} not found in database")
        raise HTTPException(status_code=404, detail=f"Stock {symbol.upper()} not found. Please add it first.")

    # Detect data source (Binance for crypto, Yahoo Finance for stocks)
    from services.binance_service import is_crypto_symbol
    is_crypto = is_crypto_symbol(symbol)
    data_source = "Binance" if is_crypto else "Yahoo Finance"
    exchange = "Binance" if is_crypto else "Yahoo Finance"
    market_state = "24/7" if is_crypto else "Unknown"
    is_market_open = True if is_crypto else None  # Crypto markets are always open
    exchange_tz = "UTC"

    # For stocks, try to get market info (optional, non-blocking)
    if not is_crypto:
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.fast_info if hasattr(ticker, 'fast_info') else {}

            if not info:
                info = ticker.info

            exchange = info.get('exchange', 'Yahoo Finance')
            market_state = info.get('marketState', 'Unknown')
            is_market_open = market_state in ['REGULAR', 'PRE', 'POST']
            exchange_tz = info.get('exchangeTimezoneName', 'UTC')

            logger.info(f"📍 [SYNC] Stock Exchange: {exchange}, Market State: {market_state}, Open: {is_market_open}")
        except Exception as e:
            logger.debug(f"ℹ️ [SYNC] Could not fetch market info (non-critical): {str(e)[:100]}")
            # Continue with defaults - market info is optional
    else:
        logger.info(f"📍 [SYNC] Crypto via Binance - Market: 24/7 Open")

    if timeframe:
        tf = tf_map.get(timeframe)
        if not tf:
            logger.error(f"❌ [SYNC] Invalid timeframe: {timeframe}")
            raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 5h, 1d")

        logger.info(f"📊 [SYNC] Syncing {symbol.upper()} for timeframe {timeframe} (delta sync)")
        result = sync_candles(db, symbol, tf, full_sync)
        logger.info(f"✅ [SYNC] Sync complete: {result.get('new_candles', 0)} new candles")

        # Calculate indicators after sync
        if result.get("new_candles", 0) > 0:
            logger.info(f"📈 [SYNC] Calculating indicators for {symbol.upper()} {timeframe}")
            indicator_result = calculate_indicators_for_candles(db, stock.id, tf)
            result["indicators_calculated"] = indicator_result
            logger.info(f"✅ [SYNC] Indicators calculated: {indicator_result}")

        # Add market info
        result["exchange"] = exchange
        result["market_state"] = market_state
        result["is_market_open"] = is_market_open
        result["sync_type"] = "full" if full_sync else "delta"

        return result
    else:
        logger.info(f"📊 [SYNC] Syncing {symbol.upper()} for all timeframes (delta sync)")
        results = sync_all_timeframes(db, symbol, full_sync)

        total_new = sum(r.get("new_candles", 0) for r in results)
        logger.info(f"✅ [SYNC] All timeframes synced: {total_new} total new candles")

        # Calculate indicators for all timeframes
        if stock:
            logger.info(f"📈 [SYNC] Calculating indicators for all timeframes")
            for tf_name, tf in tf_map.items():
                indicator_result = calculate_indicators_for_candles(db, stock.id, tf)
                # Find matching result and add indicator info
                for r in results:
                    if r.get("timeframe") == tf_name:
                        r["indicators_calculated"] = indicator_result

        return {
            "symbol": symbol.upper(),
            "exchange": exchange,
            "market_state": market_state,
            "is_market_open": is_market_open,
            "exchange_timezone": exchange_tz,
            "sync_type": "full" if full_sync else "delta",
            "results": results
        }


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


# ============ MANUAL TRADING ============
@app.post("/trades/manual/buy", tags=["Manual Trading"])
def manual_buy(
    symbol: str,
    quantity: int,
    price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Execute manual buy order"""
    from utils.trading_fees import calculate_trading_fees

    # Get stock
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    # Get current price if not provided
    if price is None:
        latest_candle = (
            db.query(Candle)
            .filter(Candle.stock_id == stock.id, Candle.timeframe == TimeFrame.D1)
            .order_by(Candle.timestamp.desc())
            .first()
        )
        if not latest_candle:
            raise HTTPException(status_code=400, detail="No price data available. Please provide price manually.")
        price = latest_candle.close

    # Calculate fees
    fees = calculate_trading_fees(quantity, price, "BUY")

    # Check portfolio balance
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        portfolio = Portfolio(cash_balance=10000.0, initial_capital=10000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    if portfolio.cash_balance < fees["net_amount"]:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds. Required: ₹{fees['net_amount']:.2f}, Available: ₹{portfolio.cash_balance:.2f}"
        )

    # Create trade record
    trade = Trade(
        stock_id=stock.id,
        trade_type=TradeType.BUY,
        strategy=StrategyType.MANUAL,
        quantity=quantity,
        price=price,
        total_value=fees["net_amount"],
        notes=f"Manual buy order. Charges: ₹{fees['total_charges']:.2f}"
    )
    db.add(trade)

    # Update portfolio
    portfolio.cash_balance -= fees["net_amount"]

    # Update or create holding
    holding = db.query(Holding).filter(Holding.stock_id == stock.id).first()
    if holding:
        # Update average buy price
        total_qty = holding.quantity + quantity
        total_cost = (holding.avg_buy_price * holding.quantity) + fees["net_amount"]
        holding.avg_buy_price = total_cost / total_qty
        holding.quantity = total_qty
    else:
        holding = Holding(
            stock_id=stock.id,
            quantity=quantity,
            avg_buy_price=fees["net_amount"] / quantity
        )
        db.add(holding)

    db.commit()
    db.refresh(trade)

    return {
        "message": "Buy order executed successfully",
        "trade_id": trade.id,
        "symbol": symbol.upper(),
        "quantity": quantity,
        "price": price,
        "fees": fees,
        "remaining_balance": round(portfolio.cash_balance, 2)
    }


@app.post("/trades/manual/sell", tags=["Manual Trading"])
def manual_sell(
    symbol: str,
    quantity: int,
    price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Execute manual sell order"""
    from utils.trading_fees import calculate_trading_fees

    # Get stock
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    # Check holding
    holding = db.query(Holding).filter(Holding.stock_id == stock.id).first()
    if not holding or holding.quantity < quantity:
        available_qty = holding.quantity if holding else 0
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient shares. Available: {available_qty}, Requested: {quantity}"
        )

    # Get current price if not provided
    if price is None:
        latest_candle = (
            db.query(Candle)
            .filter(Candle.stock_id == stock.id, Candle.timeframe == TimeFrame.D1)
            .order_by(Candle.timestamp.desc())
            .first()
        )
        if not latest_candle:
            raise HTTPException(status_code=400, detail="No price data available. Please provide price manually.")
        price = latest_candle.close

    # Calculate fees
    fees = calculate_trading_fees(quantity, price, "SELL")

    # Create trade record
    trade = Trade(
        stock_id=stock.id,
        trade_type=TradeType.SELL,
        strategy=StrategyType.MANUAL,
        quantity=quantity,
        price=price,
        total_value=fees["net_amount"],
        notes=f"Manual sell order. Charges: ₹{fees['total_charges']:.2f}"
    )
    db.add(trade)

    # Update portfolio
    portfolio = db.query(Portfolio).first()
    portfolio.cash_balance += fees["net_amount"]

    # Update holding
    holding.quantity -= quantity
    if holding.quantity == 0:
        db.delete(holding)

    db.commit()
    db.refresh(trade)

    return {
        "message": "Sell order executed successfully",
        "trade_id": trade.id,
        "symbol": symbol.upper(),
        "quantity": quantity,
        "price": price,
        "fees": fees,
        "new_balance": round(portfolio.cash_balance, 2)
    }


@app.get("/trades/manual/positions", tags=["Manual Trading"])
def get_manual_positions(
    symbol: Optional[str] = None,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get open positions from manual trades with P&L"""

    # Get holdings
    holdings_query = db.query(Holding).filter(Holding.quantity > 0)
    if symbol:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if stock:
            holdings_query = holdings_query.filter(Holding.stock_id == stock.id)

    holdings = holdings_query.all()

    positions = []
    total_invested = 0
    total_current_value = 0

    for holding in holdings:
        stock = db.query(Stock).filter(Stock.id == holding.stock_id).first()
        if not stock:
            continue

        # Get current price
        latest_candle = (
            db.query(Candle)
            .filter(Candle.stock_id == stock.id, Candle.timeframe == TimeFrame.D1)
            .order_by(Candle.timestamp.desc())
            .first()
        )
        current_price = latest_candle.close if latest_candle else holding.avg_buy_price

        # Calculate P&L
        invested = holding.avg_buy_price * holding.quantity
        current_value = current_price * holding.quantity
        pnl = current_value - invested
        pnl_percent = (pnl / invested) * 100 if invested > 0 else 0

        total_invested += invested
        total_current_value += current_value

        # Get buy trades for this stock (FIFO order)
        buy_trades = (
            db.query(Trade)
            .filter(
                Trade.stock_id == stock.id,
                Trade.trade_type == TradeType.BUY,
                Trade.strategy == StrategyType.MANUAL
            )
            .order_by(Trade.timestamp.asc())
            .all()
        )

        positions.append({
            "symbol": stock.symbol,
            "name": stock.name,
            "quantity": holding.quantity,
            "avg_buy_price": round(holding.avg_buy_price, 2),
            "current_price": round(current_price, 2),
            "invested": round(invested, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "buy_trades_count": len(buy_trades)
        })

    # Apply pagination
    total_positions = len(positions)
    positions = positions[offset:offset + limit]

    overall_pnl = total_current_value - total_invested
    overall_pnl_percent = (overall_pnl / total_invested) * 100 if total_invested > 0 else 0

    return {
        "positions": positions,
        "summary": {
            "total_positions": total_positions,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_pnl": round(overall_pnl, 2),
            "total_pnl_percent": round(overall_pnl_percent, 2)
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total_positions
        }
    }


@app.get("/trades/manual/history", tags=["Manual Trading"])
def get_manual_trade_history(
    symbol: Optional[str] = None,
    trade_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get manual trade history with filters"""
    from datetime import datetime as dt

    # Build query
    query = db.query(Trade).filter(Trade.strategy == StrategyType.MANUAL)

    if symbol:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if stock:
            query = query.filter(Trade.stock_id == stock.id)

    if trade_type:
        try:
            tt = TradeType(trade_type.upper())
            query = query.filter(Trade.trade_type == tt)
        except ValueError:
            pass

    if date_from:
        try:
            from_date = dt.fromisoformat(date_from)
            query = query.filter(Trade.timestamp >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = dt.fromisoformat(date_to)
            query = query.filter(Trade.timestamp <= to_date)
        except ValueError:
            pass

    # Get total count
    total_count = query.count()

    # Apply pagination and ordering
    trades = query.order_by(Trade.timestamp.desc()).offset(offset).limit(limit).all()

    result = []
    for trade in trades:
        stock = db.query(Stock).filter(Stock.id == trade.stock_id).first()
        result.append({
            "id": trade.id,
            "symbol": stock.symbol if stock else "Unknown",
            "name": stock.name if stock else "Unknown",
            "type": trade.trade_type.value,
            "quantity": trade.quantity,
            "price": round(trade.price, 2),
            "total_value": round(trade.total_value, 2),
            "timestamp": trade.timestamp.isoformat(),
            "notes": trade.notes
        })

    return {
        "trades": result,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total_count
        }
    }


@app.get("/trades/manual/calculate-fees", tags=["Manual Trading"])
def calculate_fees_preview(
    symbol: str,
    quantity: int,
    price: Optional[float] = None,
    trade_type: str = "BUY",
    fund_percentage: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Calculate trading fees and max quantity before executing trade"""
    from utils.trading_fees import calculate_trading_fees, calculate_max_quantity

    # Get stock
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    # Get current price if not provided
    if price is None:
        latest_candle = (
            db.query(Candle)
            .filter(Candle.stock_id == stock.id, Candle.timeframe == TimeFrame.D1)
            .order_by(Candle.timestamp.desc())
            .first()
        )
        if not latest_candle:
            raise HTTPException(status_code=400, detail="No price data available")
        price = latest_candle.close

    # Get portfolio
    portfolio = db.query(Portfolio).first()
    available_funds = portfolio.cash_balance if portfolio else 0

    # Calculate fees for requested quantity
    fees = calculate_trading_fees(quantity, price, trade_type.upper())

    # Calculate max quantity if fund percentage is provided
    max_qty_info = None
    if trade_type.upper() == "BUY" and fund_percentage is not None:
        max_qty_info = calculate_max_quantity(available_funds, price, fund_percentage)

    # Get current holding for sell validation
    holding_qty = 0
    if trade_type.upper() == "SELL":
        holding = db.query(Holding).filter(Holding.stock_id == stock.id).first()
        holding_qty = holding.quantity if holding else 0

    return {
        "symbol": symbol.upper(),
        "current_price": round(price, 2),
        "quantity": quantity,
        "trade_type": trade_type.upper(),
        "fees": fees,
        "available_funds": round(available_funds, 2),
        "max_quantity_info": max_qty_info,
        "holding_quantity": holding_qty,
        "can_execute": (
            fees["net_amount"] <= available_funds if trade_type.upper() == "BUY"
            else quantity <= holding_qty
        )
    }


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


def _get_stored_indicator_values(db: Session, stock_id: int, timeframe: TimeFrame, strategy: str = None, limit: int = 500) -> Dict:
    """
    Fetch stored indicator values from database instead of recalculating.
    Returns indicator data for chart rendering.
    """
    from sqlalchemy import desc

    # Get candles with their indicator values
    candles_query = (
        db.query(Candle)
        .filter(Candle.stock_id == stock_id, Candle.timeframe == timeframe)
        .order_by(desc(Candle.timestamp))
        .limit(limit)
    )
    candles = candles_query.all()

    if not candles:
        return {}

    # Get candle IDs
    candle_ids = [c.id for c in candles]

    # Fetch indicator values for these candles
    indicator_query = db.query(IndicatorValue).filter(IndicatorValue.candle_id.in_(candle_ids))
    if strategy:
        indicator_query = indicator_query.filter(IndicatorValue.strategy == strategy.upper())
    indicators = indicator_query.all()

    # Build lookup map: candle_id -> {strategy -> indicator_data}
    indicator_map = {}
    for ind in indicators:
        if ind.candle_id not in indicator_map:
            indicator_map[ind.candle_id] = {}
        indicator_map[ind.candle_id][ind.strategy] = ind

    # Build result with candles and their indicators (in chronological order)
    result = {
        "candles": [],
        "indicators": {}
    }

    # Initialize indicator arrays for each strategy
    strategies = set(ind.strategy for ind in indicators)
    for strat in strategies:
        result["indicators"][strat] = {
            "signal": [],
            "strength": [],
            "timestamps": []
        }
        # Add strategy-specific fields
        if strat == "MACD":
            result["indicators"][strat].update({
                "macd_line": [],
                "macd_signal": [],
                "macd_histogram": []
            })
        elif strat == "RSI":
            result["indicators"][strat]["rsi_value"] = []
        elif strat == "MA_CROSSOVER":
            result["indicators"][strat].update({
                "short_ma": [],
                "long_ma": []
            })
        elif strat == "BOLLINGER":
            result["indicators"][strat].update({
                "bb_upper": [],
                "bb_middle": [],
                "bb_lower": [],
                "bb_percent_b": []
            })
        elif strat == "MTF_EMA":
            result["indicators"][strat].update({
                "ema_20": [],
                "ema_30": [],
                "ema_40": [],
                "ema_50": [],
                "ema_60": [],
                "ema_200": [],
                "ema_300": [],
                "bullish_count": [],
                "bearish_count": []
            })

    # Populate data in chronological order (reverse the desc order)
    for candle in reversed(candles):
        result["candles"].append({
            "timestamp": candle.timestamp.isoformat(),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume
        })

        candle_indicators = indicator_map.get(candle.id, {})

        for strat in strategies:
            ind = candle_indicators.get(strat)
            ts = candle.timestamp.isoformat()

            if ind:
                result["indicators"][strat]["signal"].append(ind.signal)
                result["indicators"][strat]["strength"].append(ind.strength)
                result["indicators"][strat]["timestamps"].append(ts)

                if strat == "MACD":
                    result["indicators"][strat]["macd_line"].append(ind.macd_line)
                    result["indicators"][strat]["macd_signal"].append(ind.macd_signal)
                    result["indicators"][strat]["macd_histogram"].append(ind.macd_histogram)
                elif strat == "RSI":
                    result["indicators"][strat]["rsi_value"].append(ind.rsi_value)
                elif strat == "MA_CROSSOVER":
                    result["indicators"][strat]["short_ma"].append(ind.short_ma)
                    result["indicators"][strat]["long_ma"].append(ind.long_ma)
                elif strat == "BOLLINGER":
                    result["indicators"][strat]["bb_upper"].append(ind.bb_upper)
                    result["indicators"][strat]["bb_middle"].append(ind.bb_middle)
                    result["indicators"][strat]["bb_lower"].append(ind.bb_lower)
                    result["indicators"][strat]["bb_percent_b"].append(ind.bb_percent_b)
                elif strat == "MTF_EMA":
                    result["indicators"][strat]["ema_20"].append(ind.ema_20)
                    result["indicators"][strat]["ema_30"].append(ind.ema_30)
                    result["indicators"][strat]["ema_40"].append(ind.ema_40)
                    result["indicators"][strat]["ema_50"].append(ind.ema_50)
                    result["indicators"][strat]["ema_60"].append(ind.ema_60)
                    result["indicators"][strat]["ema_200"].append(ind.ema_200)
                    result["indicators"][strat]["ema_300"].append(ind.ema_300)
                    result["indicators"][strat]["bullish_count"].append(ind.bullish_count)
                    result["indicators"][strat]["bearish_count"].append(ind.bearish_count)
            else:
                # No indicator value for this candle, append None
                result["indicators"][strat]["signal"].append(None)
                result["indicators"][strat]["strength"].append(None)
                result["indicators"][strat]["timestamps"].append(ts)

                if strat == "MACD":
                    result["indicators"][strat]["macd_line"].append(None)
                    result["indicators"][strat]["macd_signal"].append(None)
                    result["indicators"][strat]["macd_histogram"].append(None)
                elif strat == "RSI":
                    result["indicators"][strat]["rsi_value"].append(None)
                elif strat == "MA_CROSSOVER":
                    result["indicators"][strat]["short_ma"].append(None)
                    result["indicators"][strat]["long_ma"].append(None)
                elif strat == "BOLLINGER":
                    result["indicators"][strat]["bb_upper"].append(None)
                    result["indicators"][strat]["bb_middle"].append(None)
                    result["indicators"][strat]["bb_lower"].append(None)
                    result["indicators"][strat]["bb_percent_b"].append(None)
                elif strat == "MTF_EMA":
                    result["indicators"][strat]["ema_20"].append(None)
                    result["indicators"][strat]["ema_30"].append(None)
                    result["indicators"][strat]["ema_40"].append(None)
                    result["indicators"][strat]["ema_50"].append(None)
                    result["indicators"][strat]["ema_60"].append(None)
                    result["indicators"][strat]["ema_200"].append(None)
                    result["indicators"][strat]["ema_300"].append(None)
                    result["indicators"][strat]["bullish_count"].append(None)
                    result["indicators"][strat]["bearish_count"].append(None)

    return result


def _get_latest_signal_from_stored(db: Session, stock_id: int, timeframe: TimeFrame, strategy: str) -> Dict:
    """Get the latest signal for a strategy from stored indicator values"""
    from sqlalchemy import desc

    # Get the latest candle with indicator
    latest_candle = (
        db.query(Candle)
        .filter(Candle.stock_id == stock_id, Candle.timeframe == timeframe)
        .order_by(desc(Candle.timestamp))
        .first()
    )

    if not latest_candle:
        return None

    # Get indicator value for this candle
    indicator = (
        db.query(IndicatorValue)
        .filter(
            IndicatorValue.candle_id == latest_candle.id,
            IndicatorValue.strategy == strategy.upper()
        )
        .first()
    )

    if not indicator:
        return None

    # Build result based on strategy
    result = {
        "strategy": strategy.upper(),
        "signal": indicator.signal or "HOLD",
        "strength": indicator.strength or 50,
        "timestamp": latest_candle.timestamp.isoformat(),
        "indicators": {}
    }

    if strategy.upper() == "MACD":
        result["indicators"] = {
            "macd_line": indicator.macd_line,
            "macd_signal": indicator.macd_signal,
            "histogram": indicator.macd_histogram
        }
        result["reason"] = f"MACD histogram: {indicator.macd_histogram:.4f}" if indicator.macd_histogram else "MACD"
    elif strategy.upper() == "RSI":
        result["indicators"] = {"rsi": indicator.rsi_value}
        result["reason"] = f"RSI: {indicator.rsi_value:.2f}" if indicator.rsi_value else "RSI"
    elif strategy.upper() == "MA_CROSSOVER":
        result["indicators"] = {
            "short_ma": indicator.short_ma,
            "long_ma": indicator.long_ma
        }
        result["reason"] = f"Short MA: {indicator.short_ma:.2f}, Long MA: {indicator.long_ma:.2f}" if indicator.short_ma else "MA Crossover"
    elif strategy.upper() == "BOLLINGER":
        result["indicators"] = {
            "upper": indicator.bb_upper,
            "middle": indicator.bb_middle,
            "lower": indicator.bb_lower,
            "percent_b": indicator.bb_percent_b
        }
        result["reason"] = f"%B: {indicator.bb_percent_b:.2f}" if indicator.bb_percent_b else "Bollinger Bands"
    elif strategy.upper() == "MTF_EMA":
        result["indicators"] = {
            "ema_20": indicator.ema_20,
            "ema_50": indicator.ema_50,
            "ema_200": indicator.ema_200,
            "bullish_count": indicator.bullish_count,
            "bearish_count": indicator.bearish_count
        }
        result["reason"] = f"Bullish: {indicator.bullish_count}, Bearish: {indicator.bearish_count}"

    return result


def _get_mtf_candle_data(db: Session, stock_id: int) -> Dict:
    """Fetch candle data for all 10 timeframes for MTF_EMA strategy"""
    import pandas as pd

    tf_map = get_timeframe_map()
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


# ============ STORED INDICATORS API ============
@app.get("/indicators/{symbol}", tags=["Indicators"])
def get_stored_indicators(
    symbol: str,
    timeframe: str = "1d",
    strategy: Optional[str] = None,
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db)
):
    """
    Get stored indicator values for chart rendering.
    This endpoint reads pre-calculated values from the database (faster than recalculating).

    Returns candles with their associated indicator values for charting.
    """
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    tf_map = get_timeframe_map()
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    result = _get_stored_indicator_values(db, stock.id, tf, strategy, limit)

    if not result:
        raise HTTPException(status_code=404, detail="No indicator data found. Sync candles first.")

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candle_count": len(result.get("candles", [])),
        "strategies": list(result.get("indicators", {}).keys()),
        **result
    }


@app.get("/signals-fast/{symbol}", tags=["Signals"])
def get_signals_fast(
    symbol: str,
    timeframe: str = "1d",
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get trading signals from stored indicator values (faster than /signals).
    Uses pre-calculated values instead of recalculating on each request.
    """
    from strategies import STRATEGIES

    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    tf_map = get_timeframe_map()
    tf = tf_map.get(timeframe)
    if not tf:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    # Get current price from latest candle
    from sqlalchemy import desc
    latest_candle = (
        db.query(Candle)
        .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
        .order_by(desc(Candle.timestamp))
        .first()
    )
    current_price = latest_candle.close if latest_candle else 0

    if strategy:
        # Single strategy
        result = _get_latest_signal_from_stored(db, stock.id, tf, strategy)
        if not result:
            raise HTTPException(status_code=404, detail=f"No stored indicators for {strategy}")

        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "signals": [result]
        }
    else:
        # All strategies
        signals = []
        for name in STRATEGIES.keys():
            result = _get_latest_signal_from_stored(db, stock.id, tf, name)
            if result:
                signals.append(result)

        if not signals:
            raise HTTPException(status_code=404, detail="No stored indicators found. Sync candles first.")

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