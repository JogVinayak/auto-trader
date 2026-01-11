from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
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
        elif strategy_name.upper() == "RSI_W_PATTERN":
            return strategy_class(
                rsi_period=setting.rsi_w_pattern_period,
                oversold_threshold=setting.rsi_w_pattern_oversold,
                overbought_threshold=setting.rsi_w_pattern_overbought,
                min_distance=setting.rsi_w_pattern_min_distance,
                max_distance=setting.rsi_w_pattern_max_distance,
                tolerance=setting.rsi_w_pattern_tolerance
            )

    # Return with default settings
    return strategy_class()


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
        # Single strategy with DB settings
        try:
            strat = _get_strategy_with_settings(strategy, db)
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

    elif strategy_type == StrategyType.RSI_W_PATTERN:
        if "rsi_period" in settings:
            setting.rsi_w_pattern_period = settings["rsi_period"]
        if "oversold_threshold" in settings:
            setting.rsi_w_pattern_oversold = settings["oversold_threshold"]
        if "overbought_threshold" in settings:
            setting.rsi_w_pattern_overbought = settings["overbought_threshold"]
        if "min_distance" in settings:
            setting.rsi_w_pattern_min_distance = settings["min_distance"]
        if "max_distance" in settings:
            setting.rsi_w_pattern_max_distance = settings["max_distance"]
        if "tolerance" in settings:
            setting.rsi_w_pattern_tolerance = settings["tolerance"]

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
    elif strategy_type == StrategyType.RSI_W_PATTERN:
        return {
            "rsi_period": setting.rsi_w_pattern_period,
            "oversold_threshold": setting.rsi_w_pattern_oversold,
            "overbought_threshold": setting.rsi_w_pattern_overbought,
            "min_distance": setting.rsi_w_pattern_min_distance,
            "max_distance": setting.rsi_w_pattern_max_distance,
            "tolerance": setting.rsi_w_pattern_tolerance,
        }
    return {}


def _get_default_settings(strategy_type: StrategyType) -> dict:
    """Get default settings for a strategy"""
    defaults = {
        StrategyType.MACD: {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        StrategyType.RSI: {"period": 14, "overbought": 70, "oversold": 30},
        StrategyType.MA_CROSSOVER: {"short_period": 20, "long_period": 50, "ma_type": "EMA"},
        StrategyType.BOLLINGER: {"period": 20, "std_dev": 2.0},
        StrategyType.RSI_W_PATTERN: {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "min_distance": 3,
            "max_distance": 10,
            "tolerance": 3.0
        },
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
    strategy_params: str = None,  # JSON string of strategy parameters
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
        strategy_params: JSON string of strategy-specific parameters
    """
    try:
        from database_manager import db_manager
        from services.backtest_engine import BacktestEngine, BacktestConfig
        import pandas as pd

        # Helper function to extract indicators from signals
        def extract_indicators_from_signals(signals):
            """Extract indicator values from signals for chart plotting"""
            if not signals or len(signals) == 0:
                return None

            # Get indicator names from the first signal
            indicator_fields = []
            first_signal = signals[0]
            if hasattr(first_signal, 'indicators') and first_signal.indicators:
                indicator_fields = list(first_signal.indicators.keys())

            if not indicator_fields:
                return None

            result = {}
            for field in indicator_fields:
                values = []
                for signal in signals:
                    if hasattr(signal, 'indicators') and signal.indicators:
                        value = signal.indicators.get(field)
                        values.append(value)
                    else:
                        values.append(None)
                result[field] = values

            return result if result else None

        # Helper function to get candles around a trade
        def get_trade_candles(df, entry_date, exit_date, lookback_bars=50, lookforward_bars=10):
            """Get candles around a trade for visualization"""
            try:
                # Find entry index
                entry_idx = df[df['timestamp'] == entry_date].index[0] if len(df[df['timestamp'] == entry_date]) > 0 else None

                if entry_idx is None:
                    return []

                # Get candles before entry for context
                start_idx = max(0, entry_idx - lookback_bars)

                # Get candles after exit for context
                if exit_date:
                    exit_idx = df[df['timestamp'] == exit_date].index[0] if len(df[df['timestamp'] == exit_date]) > 0 else entry_idx
                    end_idx = min(len(df), exit_idx + lookforward_bars)
                else:
                    end_idx = min(len(df), entry_idx + lookforward_bars)

                # Extract candles
                trade_candles = df.iloc[start_idx:end_idx]

                return [
                    {
                        "timestamp": str(row['timestamp']),
                        "open": row['open'],
                        "high": row['high'],
                        "low": row['low'],
                        "close": row['close'],
                        "volume": row['volume']
                    }
                    for _, row in trade_candles.iterrows()
                ]
            except Exception as e:
                print(f"Error getting trade candles: {e}")
                return []

        # Get stock
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        # Get candles from backtest database
        bt_db = db_manager.get_backtest_session()

        tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
        tf = tf_map.get(timeframe)
        if not tf:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        # Fetch historical candles
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

        # Parse strategy parameters if provided
        import json
        params = {}
        if strategy_params:
            try:
                params = json.loads(strategy_params)
            except json.JSONDecodeError:
                pass

        # Get strategy with custom parameters or settings from DB
        if params:
            # Instantiate strategy with custom parameters
            from strategies import STRATEGIES

            # Get strategy class (not instance)
            strategy_class = STRATEGIES.get(strategy.upper())
            if not strategy_class:
                raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

            # Create strategy instance with custom params
            if strategy == "MACD":
                strat = strategy_class(
                    fast_period=params.get('fast_period', 12),
                    slow_period=params.get('slow_period', 26),
                    signal_period=params.get('signal_period', 9)
                )
            elif strategy == "RSI":
                strat = strategy_class(
                    period=params.get('period', 14),
                    oversold=params.get('oversold', 30),
                    overbought=params.get('overbought', 70)
                )
            elif strategy == "RSI_W_PATTERN":
                strat = strategy_class(
                    rsi_period=params.get('rsi_period', 14),
                    oversold_threshold=params.get('oversold_threshold', 30),
                    overbought_threshold=params.get('overbought_threshold', 70),
                    min_distance=params.get('min_distance', 3),
                    max_distance=params.get('max_distance', 10),
                    rsi_tolerance=params.get('rsi_tolerance', 5)
                )
            elif strategy == "MA_CROSSOVER":
                strat = strategy_class(
                    short_period=params.get('short_period', 20),
                    long_period=params.get('long_period', 50),
                    use_ema=params.get('use_ema', True)
                )
            elif strategy == "BOLLINGER":
                strat = strategy_class(
                    period=params.get('period', 20),
                    std_dev=params.get('std_dev', 2.0)
                )
            else:
                strat = strategy_class()
        else:
            # Use settings from database
            strat = _get_strategy_with_settings(strategy, db)

        # Calculate indicators for the FULL dataset for chart plotting
        full_indicators_result = strat.calculate(df, full_history=True)
        full_indicators = full_indicators_result.get('indicators', {}) if full_indicators_result else {}

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

        # Count signals for diagnostics
        buy_signals = sum(1 for s in signals if s.get('signal') == 'BUY')
        sell_signals = sum(1 for s in signals if s.get('signal') == 'SELL')
        hold_signals = sum(1 for s in signals if s.get('signal') == 'HOLD')

        engine = BacktestEngine(config)
        result = engine.run(df, signals)

        # Helper function to safely convert float values (handle inf/nan)
        import math
        def safe_float(value, default=0.0):
            if value is None or math.isnan(value) or math.isinf(value):
                return default
            return round(value, 2)

        # Helper function to sanitize indicators dictionary (handle inf/nan in arrays)
        def sanitize_indicators(indicators):
            if not indicators:
                return None
            sanitized = {}
            for key, value in indicators.items():
                if isinstance(value, list):
                    # Sanitize arrays
                    sanitized[key] = [safe_float(v) if isinstance(v, (int, float)) else v for v in value]
                elif isinstance(value, (int, float)):
                    # Sanitize single values
                    sanitized[key] = safe_float(value)
                else:
                    # Keep strings and other types as-is
                    sanitized[key] = value
            return sanitized

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
            "diagnostics": {
                "total_candles": len(candles),
                "candles_analyzed": len(signals),
                "buy_signals_found": buy_signals,
                "sell_signals_found": sell_signals,
                "hold_signals": hold_signals,
                "data_range": {
                    "start": str(df['timestamp'].min()),
                    "end": str(df['timestamp'].max())
                },
                "opportunities_found": buy_signals + sell_signals > 0
            },
            "metrics": {
                "total_return": safe_float(result.total_return),
                "total_return_percent": safe_float(result.total_return_percent),
                "max_drawdown": safe_float(result.max_drawdown),
                "max_drawdown_percent": safe_float(result.max_drawdown_percent),
                "sharpe_ratio": safe_float(result.sharpe_ratio),
                "win_rate": safe_float(result.win_rate),
                "profit_factor": safe_float(result.profit_factor),
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "avg_win": safe_float(result.avg_win),
                "avg_loss": safe_float(result.avg_loss),
                "avg_trade": safe_float(result.avg_trade),
                "best_trade": safe_float(result.best_trade),
                "worst_trade": safe_float(result.worst_trade),
                "avg_trade_duration_hours": safe_float(result.avg_trade_duration)
            },
            "equity_curve": [safe_float(e) for e in result.equity_curve],
            "equity_dates": [str(d) for d in result.equity_dates],
            "trades": [
                {
                    "entry_date": str(t.entry_date),
                    "entry_price": safe_float(t.entry_price),
                    "exit_date": str(t.exit_date) if t.exit_date else None,
                    "exit_price": safe_float(t.exit_price) if t.exit_price else None,
                    "quantity": t.quantity,
                    "pnl": safe_float(t.pnl),
                    "pnl_percent": safe_float(t.pnl_percent),
                    "type": t.position_type.value,
                    # Add candle data around trade for chart visualization
                    "candles": get_trade_candles(df, t.entry_date, t.exit_date)
                }
                for t in result.trades
            ][:50],  # Limit to 50 trades for response size
            # Include strategy and signals for condition display
            "strategy_config": strategy,
            "all_candles": candles,  # Include all candles for continuous chart
            "all_indicators": sanitize_indicators(full_indicators)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        bt_db.close()


@app.get("/backtest/data-availability", tags=["Backtest"])
def get_backtest_data_availability(symbol: str):
    """Get available date range for backtesting a symbol"""
    from database_manager import db_manager

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


@app.post("/backtest/load-data", tags=["Backtest"])
def load_backtest_data(symbol: str, timeframe: str = "1d", period: str = "2y"):
    """
    Load historical data from Yahoo Finance into backtest database

    Args:
        symbol: Stock symbol
        timeframe: Target timeframe (1m, 5m, 1h, 1d)
        period: Period to fetch (1y, 2y, 5y, max)
    """
    try:
        import yfinance as yf
        from database_manager import db_manager
        import time

        # Map timeframes
        tf_map = {
            "1m": (TimeFrame.M1, "7d"),    # Yahoo limits
            "5m": (TimeFrame.M5, "60d"),
            "1h": (TimeFrame.H1, "730d"),
            "1d": (TimeFrame.D1, period)
        }

        if timeframe not in tf_map:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        tf_enum, yahoo_period = tf_map[timeframe]

        bt_db = db_manager.get_backtest_session()

        try:
            # Get or create stock
            stock = bt_db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
            if not stock:
                stock = Stock(symbol=symbol.upper(), name=symbol.upper())
                bt_db.add(stock)
                bt_db.commit()
                bt_db.refresh(stock)

            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)

            # Add delay to avoid rate limiting
            time.sleep(1)

            df = ticker.history(period=yahoo_period, interval=timeframe)

            if df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data available from Yahoo Finance for {symbol} ({timeframe})"
                )

            # Store candles
            candles_added = 0
            candles_updated = 0

            for idx, row in df.iterrows():
                existing = bt_db.query(Candle).filter(
                    Candle.stock_id == stock.id,
                    Candle.timestamp == idx.to_pydatetime(),
                    Candle.timeframe == tf_enum
                ).first()

                if existing:
                    existing.open = float(row['Open'])
                    existing.high = float(row['High'])
                    existing.low = float(row['Low'])
                    existing.close = float(row['Close'])
                    existing.volume = int(row['Volume'])
                    candles_updated += 1
                else:
                    candle = Candle(
                        stock_id=stock.id,
                        timestamp=idx.to_pydatetime(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume']),
                        timeframe=tf_enum
                    )
                    bt_db.add(candle)
                    candles_added += 1

            bt_db.commit()

            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "period": yahoo_period,
                "candles_added": candles_added,
                "candles_updated": candles_updated,
                "total_candles": candles_added + candles_updated,
                "date_range": {
                    "start": str(df.index[0].date()),
                    "end": str(df.index[-1].date())
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            bt_db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")
        finally:
            bt_db.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)