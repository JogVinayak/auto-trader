"""
Indicator Calculation Service

Automatically calculates and stores indicator values for candles.
Called after candle sync to populate indicator_values table.
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict
from models import Candle, IndicatorValue, TimeFrame


def calculate_indicators_for_candles(
    db: Session,
    stock_id: int,
    timeframe: TimeFrame,
    candle_ids: List[int] = None
):
    """
    Calculate indicators for candles and store in indicator_values table.

    Args:
        db: Database session
        stock_id: Stock ID
        timeframe: Timeframe enum
        candle_ids: Optional list of specific candle IDs to calculate for.
                   If None, calculates for all candles missing indicators.
    """
    # Get candles for this stock/timeframe
    candles = (
        db.query(Candle)
        .filter(Candle.stock_id == stock_id, Candle.timeframe == timeframe)
        .order_by(Candle.timestamp.asc())
        .all()
    )

    if len(candles) < 50:
        return {"error": "Insufficient candles", "count": len(candles)}

    # Convert to DataFrame
    df = pd.DataFrame([{
        "id": c.id,
        "timestamp": c.timestamp,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles])

    results = {
        "MACD": _calculate_macd(df),
        "RSI": _calculate_rsi(df),
        "MA_CROSSOVER": _calculate_ma_crossover(df),
        "BOLLINGER": _calculate_bollinger(df),
        "MTF_EMA": _calculate_mtf_ema(df),
    }

    # Store indicator values
    stored_count = 0
    for strategy, indicator_df in results.items():
        if indicator_df is None:
            continue

        for _, row in indicator_df.iterrows():
            candle_id = int(row["id"])

            # Check if already exists
            existing = db.query(IndicatorValue).filter(
                and_(
                    IndicatorValue.candle_id == candle_id,
                    IndicatorValue.strategy == strategy
                )
            ).first()

            if existing:
                continue

            indicator = IndicatorValue(
                candle_id=candle_id,
                strategy=strategy,
                signal=row.get("signal"),
                strength=row.get("strength"),
                # MACD
                macd_line=row.get("macd_line"),
                macd_signal=row.get("macd_signal"),
                macd_histogram=row.get("macd_histogram"),
                # RSI
                rsi_value=row.get("rsi_value"),
                # MA Crossover
                short_ma=row.get("short_ma"),
                long_ma=row.get("long_ma"),
                # Bollinger
                bb_upper=row.get("bb_upper"),
                bb_middle=row.get("bb_middle"),
                bb_lower=row.get("bb_lower"),
                bb_percent_b=row.get("bb_percent_b"),
                # MTF_EMA
                ema_20=row.get("ema_20"),
                ema_30=row.get("ema_30"),
                ema_40=row.get("ema_40"),
                ema_50=row.get("ema_50"),
                ema_60=row.get("ema_60"),
                ema_200=row.get("ema_200"),
                ema_300=row.get("ema_300"),
                bullish_count=row.get("bullish_count"),
                bearish_count=row.get("bearish_count"),
            )
            db.add(indicator)
            stored_count += 1

    db.commit()
    return {"stored": stored_count, "strategies": list(results.keys())}


def _calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """Calculate MACD for all candles"""
    if len(df) < slow + signal:
        return None

    result = df[["id"]].copy()

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    result["macd_line"] = macd_line.round(4)
    result["macd_signal"] = signal_line.round(4)
    result["macd_histogram"] = histogram.round(4)

    # Signal logic
    prev_hist = histogram.shift(1)
    result["signal"] = "HOLD"
    result.loc[(prev_hist <= 0) & (histogram > 0), "signal"] = "BUY"
    result.loc[(prev_hist >= 0) & (histogram < 0), "signal"] = "SELL"

    result["strength"] = (histogram.abs() * 1000).clip(0, 100).fillna(50).astype(int)

    return result.iloc[slow + signal:]  # Skip warmup period


def _calculate_rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
    """Calculate RSI for all candles"""
    if len(df) < period + 1:
        return None

    result = df[["id"]].copy()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)

    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    result["rsi_value"] = rsi.round(2)

    # Signal logic
    prev_rsi = rsi.shift(1)
    result["signal"] = "HOLD"
    result.loc[(prev_rsi < 30) & (rsi >= 30), "signal"] = "BUY"
    result.loc[(prev_rsi > 70) & (rsi <= 70), "signal"] = "SELL"
    result.loc[rsi < 30, "signal"] = "BUY"
    result.loc[rsi > 70, "signal"] = "SELL"

    result["strength"] = ((rsi - 50).abs() * 2).clip(0, 100).fillna(50).astype(int)

    return result.iloc[period:]


def _calculate_ma_crossover(df: pd.DataFrame, short=20, long=50) -> pd.DataFrame:
    """Calculate MA Crossover for all candles"""
    if len(df) < long + 1:
        return None

    result = df[["id"]].copy()

    short_ma = df["close"].ewm(span=short, adjust=False).mean()
    long_ma = df["close"].ewm(span=long, adjust=False).mean()

    result["short_ma"] = short_ma.round(2)
    result["long_ma"] = long_ma.round(2)

    # Signal logic
    prev_short = short_ma.shift(1)
    prev_long = long_ma.shift(1)

    result["signal"] = "HOLD"
    result.loc[(prev_short <= prev_long) & (short_ma > long_ma), "signal"] = "BUY"
    result.loc[(prev_short >= prev_long) & (short_ma < long_ma), "signal"] = "SELL"

    ma_diff_pct = ((short_ma - long_ma) / long_ma * 100).abs()
    result["strength"] = (ma_diff_pct * 10).clip(0, 100).fillna(50).astype(int)

    return result.iloc[long:]


def _calculate_bollinger(df: pd.DataFrame, period=20, std_dev=2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands for all candles"""
    if len(df) < period:
        return None

    result = df[["id"]].copy()

    middle = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    result["bb_upper"] = upper.round(2)
    result["bb_middle"] = middle.round(2)
    result["bb_lower"] = lower.round(2)

    # %B indicator
    band_width = upper - lower
    percent_b = (df["close"] - lower) / band_width
    result["bb_percent_b"] = percent_b.round(4)

    # Signal logic
    result["signal"] = "HOLD"
    result.loc[df["close"] <= lower, "signal"] = "BUY"
    result.loc[df["close"] >= upper, "signal"] = "SELL"

    result["strength"] = ((percent_b - 0.5).abs() * 200).clip(0, 100).fillna(50).astype(int)

    return result.iloc[period:]


def _calculate_mtf_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MTF EMA values for all candles"""
    ema_periods = [20, 30, 40, 50, 60, 200, 300]
    min_required = max(ema_periods) + 3

    if len(df) < min_required:
        return None

    result = df[["id"]].copy()

    for period in ema_periods:
        ema = df["close"].ewm(span=period, adjust=False).mean()
        result[f"ema_{period}"] = ema.round(2)

    # Calculate trend direction (EMA > EMA[2])
    bullish = 0
    bearish = 0
    for period in ema_periods:
        ema = df["close"].ewm(span=period, adjust=False).mean()
        trend_up = ema > ema.shift(2)
        if trend_up.iloc[-1]:
            bullish += 1
        else:
            bearish += 1

    result["bullish_count"] = bullish
    result["bearish_count"] = bearish

    # Signal logic
    total = bullish + bearish
    ratio = bullish / total if total > 0 else 0.5

    if ratio >= 0.65:
        result["signal"] = "BUY"
        result["strength"] = int(ratio * 100)
    elif ratio <= 0.35:
        result["signal"] = "SELL"
        result["strength"] = int((1 - ratio) * 100)
    else:
        result["signal"] = "HOLD"
        result["strength"] = 50

    return result.iloc[min_required:]
