import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from models import Stock, Candle, TimeFrame


# Timeframe mapping for Yahoo Finance API
# Note: Yahoo only supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
# 2h, 3h, 4h, 5h are NOT directly supported - we can only use available intervals
TIMEFRAME_MAP = {
    TimeFrame.M1: {"interval": "1m", "range": "7d"},
    TimeFrame.M5: {"interval": "5m", "range": "60d"},
    TimeFrame.M15: {"interval": "15m", "range": "60d"},
    TimeFrame.M30: {"interval": "30m", "range": "60d"},
    TimeFrame.H1: {"interval": "1h", "range": "730d"},
    TimeFrame.D1: {"interval": "1d", "range": "10y"},
}

# Timeframes that require resampling from 1h data
RESAMPLE_TIMEFRAMES = {
    TimeFrame.H2: "2h",
    TimeFrame.H3: "3h",
    TimeFrame.H4: "4h",
    TimeFrame.H5: "5h",
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
    # Check if this timeframe needs resampling
    if timeframe in RESAMPLE_TIMEFRAMES:
        return _fetch_and_resample_candles(symbol, timeframe, start_timestamp)

    config = TIMEFRAME_MAP.get(timeframe)
    if not config:
        raise Exception(f"Unsupported timeframe: {timeframe.value}")
    
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

        # Normalize timestamp to remove microseconds for consistent comparison
        candle_ts = datetime.fromtimestamp(ts).replace(microsecond=0)

        candles.append({
            "timestamp": candle_ts,
            "open": float(quote["open"][i]),
            "high": float(quote["high"][i]),
            "low": float(quote["low"][i]),
            "close": float(quote["close"][i]),
            "volume": int(quote["volume"][i]) if quote["volume"][i] else 0
        })

    return candles


def _fetch_and_resample_candles(
    symbol: str,
    timeframe: TimeFrame,
    start_timestamp: Optional[int] = None
) -> List[Dict]:
    """
    Fetch 1h candles and resample to higher timeframes (2h, 3h, 4h, 5h).
    Yahoo Finance doesn't support these intervals directly.
    """
    resample_rule = RESAMPLE_TIMEFRAMES.get(timeframe)
    if not resample_rule:
        raise Exception(f"No resample rule for timeframe: {timeframe.value}")

    # Fetch 1h candles
    config = TIMEFRAME_MAP[TimeFrame.H1]

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    params = {
        "interval": config["interval"],
        "range": config["range"],
    }

    if start_timestamp:
        params.pop("range", None)
        params["period1"] = start_timestamp
        params["period2"] = int(datetime.now().timestamp())

    response = requests.get(url, headers=headers, params=params, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Yahoo API returned status {response.status_code}")

    data = response.json()

    if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
        error = data.get("chart", {}).get("error", {})
        raise Exception(f"Yahoo API error: {error.get('description', 'Unknown error')}")

    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])

    if not timestamps:
        return []

    quote = result["indicators"]["quote"][0]

    # Build DataFrame for resampling
    rows = []
    for i, ts in enumerate(timestamps):
        if any(quote[k][i] is None for k in ["open", "high", "low", "close"]):
            continue
        rows.append({
            "timestamp": datetime.fromtimestamp(ts).replace(microsecond=0),
            "open": float(quote["open"][i]),
            "high": float(quote["high"][i]),
            "low": float(quote["low"][i]),
            "close": float(quote["close"][i]),
            "volume": int(quote["volume"][i]) if quote["volume"][i] else 0
        })

    if not rows:
        return []

    df = pd.DataFrame(rows)
    df.set_index("timestamp", inplace=True)

    # Resample to target timeframe
    resampled = df.resample(resample_rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    # Convert back to list of dicts
    candles = []
    for ts, row in resampled.iterrows():
        candles.append({
            "timestamp": ts.to_pydatetime(),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": int(row["volume"])
        })

    return candles


def get_existing_timestamps(db: Session, stock_id: int, timeframe: TimeFrame) -> set:
    """Get all existing timestamps for a stock/timeframe combination"""
    results = (
        db.query(Candle.timestamp)
        .filter(Candle.stock_id == stock_id, Candle.timeframe == timeframe)
        .all()
    )
    # For daily candles, use date only; for others, truncate to minute
    if timeframe == TimeFrame.D1:
        return {r[0].date() if r[0] else None for r in results}
    else:
        return {r[0].replace(second=0, microsecond=0) if r[0] else None for r in results}


def sync_candles(
    db: Session,
    symbol: str,
    timeframe: TimeFrame,
    full_sync: bool = False
) -> Dict:
    """
    Sync candles from Yahoo Finance API to database
    Checks for existing candles before inserting to prevent duplicates
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

    # Get all existing timestamps for this stock/timeframe to check duplicates
    existing_timestamps = get_existing_timestamps(db, stock.id, timeframe)

    # Filter out candles that already exist
    new_candles = []
    for candle_data in candles_data:
        # For daily candles, compare by date only; for others, truncate to minute
        if timeframe == TimeFrame.D1:
            key = candle_data["timestamp"].date()
        else:
            key = candle_data["timestamp"].replace(second=0, microsecond=0)

        if key not in existing_timestamps:
            new_candles.append(candle_data)

    skipped_count = len(candles_data) - len(new_candles)

    if not new_candles:
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe.value,
            "new_candles": 0,
            "skipped": skipped_count,
            "total_fetched": len(candles_data),
            "message": "All candles already exist in database"
        }

    # Bulk insert only new candles
    candles_to_insert = [
        Candle(
            stock_id=stock.id,
            timeframe=timeframe,
            timestamp=candle_data["timestamp"],
            open=candle_data["open"],
            high=candle_data["high"],
            low=candle_data["low"],
            close=candle_data["close"],
            volume=candle_data["volume"]
        )
        for candle_data in new_candles
    ]

    db.bulk_save_objects(candles_to_insert)
    db.commit()

    return {
        "success": True,
        "symbol": symbol,
        "timeframe": timeframe.value,
        "new_candles": len(new_candles),
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


def remove_duplicate_candles(db: Session, symbol: str = None) -> Dict:
    """
    Remove duplicate candles from database.
    For daily candles, considers same date as duplicate (ignores time).
    For other timeframes, uses exact timestamp match.
    Keeps the candle with the lowest ID for each unique combination.
    """
    from sqlalchemy import func, and_, cast, Date

    total_removed = 0

    # Get stocks to process
    if symbol:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            return {"success": False, "error": f"Stock {symbol} not found"}
        stocks = [stock]
    else:
        stocks = db.query(Stock).all()

    for stock in stocks:
        for tf in TimeFrame:
            # Get all candles for this stock/timeframe
            candles = (
                db.query(Candle)
                .filter(Candle.stock_id == stock.id, Candle.timeframe == tf)
                .order_by(Candle.id)
                .all()
            )

            if not candles:
                continue

            # Track seen timestamps/dates and IDs to delete
            seen = set()
            ids_to_delete = []

            for candle in candles:
                # For daily candles, use date only; for others use full timestamp
                if tf == TimeFrame.D1:
                    key = candle.timestamp.date()
                else:
                    # Truncate to minute for intraday
                    key = candle.timestamp.replace(second=0, microsecond=0)

                if key in seen:
                    ids_to_delete.append(candle.id)
                else:
                    seen.add(key)

            if ids_to_delete:
                db.query(Candle).filter(Candle.id.in_(ids_to_delete)).delete(synchronize_session=False)
                total_removed += len(ids_to_delete)

    db.commit()

    return {
        "success": True,
        "duplicates_removed": total_removed,
        "message": f"Removed {total_removed} duplicate candles"
    }