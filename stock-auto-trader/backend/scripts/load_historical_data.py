"""
Load Historical Data from Yahoo Finance to Backtest Database

This script fetches historical candle data from Yahoo Finance and stores it
in the backtest database for backtesting purposes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from datetime import datetime, timedelta
from database_manager import db_manager
from models import Stock, Candle, TimeFrame
from sqlalchemy.exc import IntegrityError
import time

def load_historical_data(symbol, period='2y', verbose=True):
    """
    Load historical data for a symbol from Yahoo Finance

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'RELIANCE.NS')
        period: Period to fetch ('1y', '2y', '5y', 'max')
        verbose: Print progress messages
    """
    bt_db = db_manager.get_backtest_session()

    try:
        if verbose:
            print(f"\n📊 Loading historical data for {symbol}...")

        # Get or create stock
        stock = bt_db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(symbol=symbol, name=symbol)
            bt_db.add(stock)
            bt_db.commit()
            bt_db.refresh(stock)
            if verbose:
                print(f"✅ Created stock entry for {symbol}")

        # Download data from Yahoo Finance with retry logic
        ticker = None
        max_retries = 3

        for retry in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                # Test if we can get basic info
                info = ticker.info
                break
            except Exception as e:
                if retry < max_retries - 1:
                    if verbose:
                        print(f"  ⚠️  Retry {retry + 1}/{max_retries} - Connection issue, waiting...")
                    time.sleep(2)
                else:
                    if verbose:
                        print(f"  ❌ Failed to connect to Yahoo Finance after {max_retries} retries")
                    return False

        # Load different timeframes
        timeframes = [
            ('1d', period, TimeFrame.D1),
            ('1h', '730d', TimeFrame.H1),  # Yahoo limits hourly data to 730 days
            ('5m', '60d', TimeFrame.M5),   # Yahoo limits 5m data to 60 days
            ('1m', '7d', TimeFrame.M1),    # Yahoo limits 1m data to 7 days
        ]

        total_candles = 0

        for interval, period_str, tf_enum in timeframes:
            if verbose:
                print(f"\n  📥 Fetching {interval} data (period: {period_str})...")

            try:
                # Add delay between requests to avoid rate limiting
                time.sleep(1)

                df = ticker.history(period=period_str, interval=interval)

                if df.empty:
                    if verbose:
                        print(f"  ⚠️  No data available for {interval}")
                    continue

                candles_added = 0
                candles_updated = 0

                for idx, row in df.iterrows():
                    # Check if candle already exists
                    existing = bt_db.query(Candle).filter(
                        Candle.stock_id == stock.id,
                        Candle.timestamp == idx.to_pydatetime(),
                        Candle.timeframe == tf_enum
                    ).first()

                    if existing:
                        # Update existing candle
                        existing.open = float(row['Open'])
                        existing.high = float(row['High'])
                        existing.low = float(row['Low'])
                        existing.close = float(row['Close'])
                        existing.volume = int(row['Volume'])
                        candles_updated += 1
                    else:
                        # Add new candle
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
                total_candles += candles_added + candles_updated

                if verbose:
                    print(f"  ✅ {interval}: Added {candles_added}, Updated {candles_updated} candles")
                    if len(df) > 0:
                        print(f"     Date range: {df.index[0].date()} to {df.index[-1].date()}")

            except Exception as e:
                print(f"  ❌ Error loading {interval} data: {e}")
                bt_db.rollback()
                continue

        if verbose:
            print(f"\n✅ Total: {total_candles} candles loaded for {symbol}")

        return True

    except Exception as e:
        print(f"❌ Error loading data for {symbol}: {e}")
        bt_db.rollback()
        return False
    finally:
        bt_db.close()


def load_multiple_stocks(symbols, period='2y'):
    """Load historical data for multiple stocks"""
    print("=" * 60)
    print("Historical Data Loader - Yahoo Finance to Backtest DB")
    print("=" * 60)

    successful = []
    failed = []

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
        if load_historical_data(symbol, period):
            successful.append(symbol)
        else:
            failed.append(symbol)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully loaded: {len(successful)} stocks")
    if successful:
        print("   " + ", ".join(successful))

    if failed:
        print(f"\n❌ Failed: {len(failed)} stocks")
        print("   " + ", ".join(failed))

    print("\n" + "=" * 60)


def verify_data_availability(symbol):
    """Verify what data is available for a symbol"""
    bt_db = db_manager.get_backtest_session()

    try:
        stock = bt_db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"❌ Stock {symbol} not found in backtest database")
            return

        print(f"\n📊 Data availability for {symbol}:")
        print("-" * 60)

        for tf_name, tf_enum in [("1 minute", TimeFrame.M1), ("5 minutes", TimeFrame.M5),
                                  ("1 hour", TimeFrame.H1), ("1 day", TimeFrame.D1)]:
            candles = bt_db.query(Candle).filter(
                Candle.stock_id == stock.id,
                Candle.timeframe == tf_enum
            ).order_by(Candle.timestamp.asc()).all()

            if candles:
                count = len(candles)
                start = candles[0].timestamp.date()
                end = candles[-1].timestamp.date()
                print(f"{tf_name:12} : {count:5} candles ({start} to {end})")
            else:
                print(f"{tf_name:12} : No data")

        print("-" * 60)

    finally:
        bt_db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load historical data from Yahoo Finance')
    parser.add_argument('--symbols', nargs='+', help='Stock symbols to load (e.g., AAPL GOOGL)')
    parser.add_argument('--period', default='2y', help='Period to fetch (default: 2y)')
    parser.add_argument('--verify', help='Verify data availability for a symbol')
    parser.add_argument('--default', action='store_true', help='Load default stock list')

    args = parser.parse_args()

    if args.verify:
        verify_data_availability(args.verify)
    elif args.default or not args.symbols:
        # Default stocks if none specified
        default_stocks = [
            'AAPL',      # Apple
            'GOOGL',     # Google
            'MSFT',      # Microsoft
            'TSLA',      # Tesla
            'AMZN',      # Amazon
            'RELIANCE.NS', # Reliance (India)
            'TCS.NS',    # TCS (India)
            'INFY.NS',   # Infosys (India)
        ]
        print("Loading default stock list...")
        load_multiple_stocks(default_stocks, args.period)
    else:
        load_multiple_stocks(args.symbols, args.period)

    print("\n✅ Done! You can now run backtests on this data.")
    print("   Test: curl 'http://localhost:8000/backtest/data-availability?symbol=AAPL'")
