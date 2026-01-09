import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from models import Stock, Candle, TimeFrame


# Timeframe mapping for Yahoo Finance API
TIMEFRAME_MAP = {
    TimeFrame.M1: {"interval": "1m", "range": "7d"},
    TimeFrame.M5: {"interval": "5m", "range": "60d"},
    TimeFrame.H1: {"interval": "1h", "range": "730d"},
    TimeFrame.D1: {"interval": "1d", "range": "10y"},
}


def get_or_create_stock(db: Session, symbol: str) -> Stock:
    """Get stock from DB or create if not exists"""
    symbol = symbol.upper().strip()
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    
    if not stock:
        # Fetch name from Yahoo Finance API
        try:
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            name = data.get("quotes", [{}])[0].get("shortname", symbol)
        except:
            name = symbol
        
        stock = Stock(symbol=symbol, name=name)
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    return stock


def get_latest_candle_timestamp(db: Session, stock_id: int, timeframe: TimeFrame) -> Optional[datetime]:
    """Get the timestamp of the latest candle in DB"""
    latest = (
        db.query(Candle)
        .filter(Candle.stock_id == stock_id, Candle.timeframe == timeframe)
        .order_by(Candle.timestamp.desc())
        .first()
    )
    return latest.timestamp if latest else None


def fetch_candles_from_yahoo_api(
    symbol: str,
    timeframe: TimeFrame,
    start_timestamp: Optional[int] = None
) -> List[Dict]:
    """Fetch candles from Yahoo Finance API directly"""
    config = TIMEFRAME_MAP[timeframe]
    
    # Yahoo Finance API endpoint
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    params = {
        "interval": config["interval"],
        "range": config["range"],
    }
    
    # If we have a start timestamp, use period1/period2 instead of range
    if start_timestamp:
        params.pop("range", None)
        params["period1"] = start_timestamp
        params["period2"] = int(datetime.now().timestamp())
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Yahoo API returned status {response.status_code}")
    
    data = response.json()
    
    # Check for errors
    if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
        error = data.get("chart", {}).get("error", {})
        raise Exception(f"Yahoo API error: {error.get('description', 'Unknown error')}")
    
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    
    if not timestamps:
        return []
    
    quote = result["indicators"]["quote"][0]
    
    candles = []
    for i, ts in enumerate(timestamps):
        # Skip if any OHLC value is None
        if any(quote[k][i] is None for k in ["open", "high", "low", "close"]):
            continue
            
        candles.append({
            "timestamp": datetime.fromtimestamp(ts),
            "open": float(quote["open"][i]),
            "high": float(quote["high"][i]),
            "low": float(quote["low"][i]),
            "close": float(quote["close"][i]),
            "volume": int(quote["volume"][i]) if quote["volume"][i] else 0
        })
    
    return candles


def sync_candles(
    db: Session,
    symbol: str,
    timeframe: TimeFrame,
    full_sync: bool = False
) -> Dict:
    """
    Sync candles from Yahoo Finance API to database
    Returns: dict with sync stats
    """
    symbol = symbol.upper().strip()
    
    # Get or create stock
    stock = get_or_create_stock(db, symbol)
    
    # Determine start timestamp for sync
    start_timestamp = None
    if not full_sync:
        latest_timestamp = get_latest_candle_timestamp(db, stock.id, timeframe)
        if latest_timestamp:
            # Start from latest + 1 second to avoid duplicates
            start_timestamp = int(latest_timestamp.timestamp()) + 1
    
    # Fetch from Yahoo Finance API
    try:
        candles_data = fetch_candles_from_yahoo_api(symbol, timeframe, start_timestamp)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "timeframe": timeframe.value
        }
    
    if not candles_data:
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe.value,
            "new_candles": 0,
            "message": "No new candles available"
        }
    
    # Process and insert candles
    new_count = 0
    skipped_count = 0
    
    for candle_data in candles_data:
        timestamp = candle_data["timestamp"]
        
        # Check if candle already exists
        existing = (
            db.query(Candle)
            .filter(
                Candle.stock_id == stock.id,
                Candle.timeframe == timeframe,
                Candle.timestamp == timestamp
            )
            .first()
        )
        
        if existing:
            skipped_count += 1
            continue
        
        # Create new candle
        candle = Candle(
            stock_id=stock.id,
            timeframe=timeframe,
            timestamp=timestamp,
            open=candle_data["open"],
            high=candle_data["high"],
            low=candle_data["low"],
            close=candle_data["close"],
            volume=candle_data["volume"]
        )
        db.add(candle)
        new_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "symbol": symbol,
        "timeframe": timeframe.value,
        "new_candles": new_count,
        "skipped": skipped_count,
        "total_fetched": len(candles_data),
        "latest_timestamp": candles_data[-1]["timestamp"].isoformat() if candles_data else None
    }


def sync_all_timeframes(db: Session, symbol: str, full_sync: bool = False) -> List[Dict]:
    """Sync all timeframes for a symbol"""
    results = []
    for tf in TimeFrame:
        result = sync_candles(db, symbol, tf, full_sync)
        results.append(result)
    return results


def get_sync_status(db: Session, symbol: str) -> Dict:
    """Get sync status for all timeframes of a symbol"""
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    
    if not stock:
        return {"symbol": symbol, "exists": False, "timeframes": {}}
    
    status = {
        "symbol": symbol,
        "exists": True,
        "stock_name": stock.name,
        "timeframes": {}
    }
    
    for tf in TimeFrame:
        count = (
            db.query(Candle)
            .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
            .count()
        )
        latest = get_latest_candle_timestamp(db, stock.id, tf)
        
        status["timeframes"][tf.value] = {
            "candle_count": count,
            "latest_timestamp": latest.isoformat() if latest else None
        }
    
    return status