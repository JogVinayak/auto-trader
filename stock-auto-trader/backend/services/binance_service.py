"""
Binance API service for fetching cryptocurrency candle data.
Provides proper OHLC data for all timeframes including 1m.
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from models import TimeFrame


# Binance interval mapping
BINANCE_INTERVALS = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H2: "2h",
    TimeFrame.H3: "3h",  # Note: Binance doesn't have 3h, we'll use 1h and resample
    TimeFrame.H4: "4h",
    TimeFrame.H5: "5h",  # Note: Binance doesn't have 5h, we'll use 1h and resample
    TimeFrame.D1: "1d",
}

# Binance supports: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
# We need to resample for 3h and 5h
BINANCE_RESAMPLE_TIMEFRAMES = {
    TimeFrame.H3: "3h",
    TimeFrame.H5: "5h",
}

# Known crypto symbols that should use Binance
# Format: Yahoo symbol -> Binance symbol
CRYPTO_SYMBOL_MAP = {
    "SOL-USD": "SOLUSDT",
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT",
    "DOT-USD": "DOTUSDT",
    "MATIC-USD": "MATICUSDT",
    "LINK-USD": "LINKUSDT",
    "AVAX-USD": "AVAXUSDT",
    "SHIB-USD": "SHIBUSDT",
    "LTC-USD": "LTCUSDT",
    "UNI-USD": "UNIUSDT",
    "ATOM-USD": "ATOMUSDT",
    "XLM-USD": "XLMUSDT",
    "ALGO-USD": "ALGOUSDT",
    "VET-USD": "VETUSDT",
    "FIL-USD": "FILUSDT",
    "TRX-USD": "TRXUSDT",
    "ETC-USD": "ETCUSDT",
    "NEAR-USD": "NEARUSDT",
    "FTM-USD": "FTMUSDT",
    "SAND-USD": "SANDUSDT",
    "MANA-USD": "MANAUSDT",
    "AXS-USD": "AXSUSDT",
    "AAVE-USD": "AAVEUSDT",
    "GRT-USD": "GRTUSDT",
    "THETA-USD": "THETAUSDT",
    "XTZ-USD": "XTZUSDT",
    "EOS-USD": "EOSUSDT",
}

# Base URL for Binance API
BINANCE_API_URL = "https://api.binance.com/api/v3"


def is_crypto_symbol(symbol: str) -> bool:
    """Check if a symbol is a cryptocurrency (should use Binance)"""
    symbol = symbol.upper().strip()
    # Check if it's in our known crypto map
    if symbol in CRYPTO_SYMBOL_MAP:
        return True
    # Check if it ends with -USD (common crypto format on Yahoo)
    if symbol.endswith("-USD") and not symbol.startswith("^"):
        # Additional check: crypto symbols typically don't have dots
        base = symbol.replace("-USD", "")
        if "." not in base and len(base) <= 6:
            return True
    return False


def get_binance_symbol(yahoo_symbol: str) -> str:
    """Convert Yahoo Finance symbol to Binance symbol"""
    yahoo_symbol = yahoo_symbol.upper().strip()
    if yahoo_symbol in CRYPTO_SYMBOL_MAP:
        return CRYPTO_SYMBOL_MAP[yahoo_symbol]
    # Try to convert -USD to USDT format
    if yahoo_symbol.endswith("-USD"):
        base = yahoo_symbol.replace("-USD", "")
        return f"{base}USDT"
    return yahoo_symbol


def fetch_binance_candles(
    symbol: str,
    timeframe: TimeFrame,
    start_timestamp: Optional[int] = None,
    limit: int = 1000
) -> List[Dict]:
    """
    Fetch candles from Binance API.

    Args:
        symbol: Yahoo Finance format symbol (e.g., "SOL-USD")
        timeframe: TimeFrame enum
        start_timestamp: Unix timestamp to start from (seconds)
        limit: Max candles to fetch (Binance max is 1000)

    Returns:
        List of candle dictionaries with timestamp, open, high, low, close, volume
    """
    binance_symbol = get_binance_symbol(symbol)

    # Check if this timeframe needs resampling
    if timeframe in BINANCE_RESAMPLE_TIMEFRAMES:
        return _fetch_and_resample_binance_candles(symbol, timeframe, start_timestamp)

    interval = BINANCE_INTERVALS.get(timeframe)
    if not interval:
        raise Exception(f"Unsupported timeframe for Binance: {timeframe.value}")

    url = f"{BINANCE_API_URL}/klines"

    params = {
        "symbol": binance_symbol,
        "interval": interval,
        "limit": limit,
    }

    if start_timestamp:
        # Binance uses milliseconds
        params["startTime"] = start_timestamp * 1000

    # Add API key if available (for higher rate limits)
    headers = {}
    api_key = os.environ.get("BINANCE_API_KEY")
    if api_key:
        headers["X-MBX-APIKEY"] = api_key

    all_candles = []

    # Binance returns max 1000 candles per request, so we may need multiple requests
    while True:
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code != 200:
            error_msg = response.json().get("msg", response.text) if response.text else f"Status {response.status_code}"
            raise Exception(f"Binance API error: {error_msg}")

        data = response.json()

        if not data:
            break

        for kline in data:
            # Binance kline format:
            # [0] Open time, [1] Open, [2] High, [3] Low, [4] Close, [5] Volume,
            # [6] Close time, [7] Quote asset volume, [8] Number of trades,
            # [9] Taker buy base volume, [10] Taker buy quote volume, [11] Ignore
            open_time_ms = kline[0]
            candle_ts = datetime.fromtimestamp(open_time_ms / 1000).replace(microsecond=0)

            all_candles.append({
                "timestamp": candle_ts,
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": int(float(kline[5]))  # Base asset volume
            })

        # If we got less than limit, we've fetched all available data
        if len(data) < limit:
            break

        # Update startTime for next request (last candle's close time + 1)
        last_close_time = data[-1][6]
        params["startTime"] = last_close_time + 1

    return all_candles


def _fetch_and_resample_binance_candles(
    symbol: str,
    timeframe: TimeFrame,
    start_timestamp: Optional[int] = None
) -> List[Dict]:
    """
    Fetch 1h candles from Binance and resample to 3h or 5h.
    Binance doesn't support 3h and 5h intervals directly.
    """
    import pandas as pd

    resample_rule = BINANCE_RESAMPLE_TIMEFRAMES.get(timeframe)
    if not resample_rule:
        raise Exception(f"No resample rule for timeframe: {timeframe.value}")

    # Fetch 1h candles
    binance_symbol = get_binance_symbol(symbol)
    url = f"{BINANCE_API_URL}/klines"

    params = {
        "symbol": binance_symbol,
        "interval": "1h",
        "limit": 1000,
    }

    if start_timestamp:
        params["startTime"] = start_timestamp * 1000

    headers = {}
    api_key = os.environ.get("BINANCE_API_KEY")
    if api_key:
        headers["X-MBX-APIKEY"] = api_key

    all_candles = []

    while True:
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code != 200:
            error_msg = response.json().get("msg", response.text) if response.text else f"Status {response.status_code}"
            raise Exception(f"Binance API error: {error_msg}")

        data = response.json()

        if not data:
            break

        for kline in data:
            open_time_ms = kline[0]
            candle_ts = datetime.fromtimestamp(open_time_ms / 1000).replace(microsecond=0)

            all_candles.append({
                "timestamp": candle_ts,
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": int(float(kline[5]))
            })

        if len(data) < 1000:
            break

        last_close_time = data[-1][6]
        params["startTime"] = last_close_time + 1

    if not all_candles:
        return []

    # Create DataFrame and resample
    df = pd.DataFrame(all_candles)
    df.set_index("timestamp", inplace=True)

    resampled = df.resample(resample_rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    # Convert back to list of dicts
    result = []
    for ts, row in resampled.iterrows():
        result.append({
            "timestamp": ts.to_pydatetime(),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": int(row["volume"])
        })

    return result


def get_binance_historical_candles(
    symbol: str,
    timeframe: TimeFrame,
    start_timestamp: Optional[int] = None
) -> List[Dict]:
    """
    Fetch all available historical candles from Binance.
    This handles pagination automatically.

    Args:
        symbol: Yahoo Finance format symbol (e.g., "SOL-USD")
        timeframe: TimeFrame enum
        start_timestamp: Unix timestamp to start from (seconds)

    Returns:
        List of all candle dictionaries
    """
    return fetch_binance_candles(symbol, timeframe, start_timestamp, limit=1000)
