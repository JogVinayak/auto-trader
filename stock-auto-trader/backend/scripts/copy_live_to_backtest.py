"""
Copy data from live database to backtest database

This script copies stocks and candles from the live trading database
to the backtest database, providing immediate historical data for backtesting.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from database_manager import db_manager
from models import Stock, Candle

def copy_live_to_backtest():
    """Copy stocks and candles from live to backtest database"""

    live_db = SessionLocal()
    backtest_db = db_manager.get_backtest_session()

    try:
        print("=" * 60)
        print("Copy Live Database to Backtest Database")
        print("=" * 60)

        # Copy stocks
        print("\n📦 Copying stocks...")
        live_stocks = live_db.query(Stock).all()
        stock_id_map = {}  # Map old IDs to new IDs

        for live_stock in live_stocks:
            # Check if stock already exists in backtest
            bt_stock = backtest_db.query(Stock).filter(
                Stock.symbol == live_stock.symbol
            ).first()

            if bt_stock:
                stock_id_map[live_stock.id] = bt_stock.id
                print(f"  ✓ {live_stock.symbol} (already exists)")
            else:
                # Create new stock
                bt_stock = Stock(
                    symbol=live_stock.symbol,
                    name=live_stock.name
                )
                backtest_db.add(bt_stock)
                backtest_db.flush()
                stock_id_map[live_stock.id] = bt_stock.id
                print(f"  + {live_stock.symbol} (created)")

        backtest_db.commit()
        print(f"✅ Copied {len(live_stocks)} stocks")

        # Copy candles
        print("\n📈 Copying candles...")
        total_candles = 0
        added_candles = 0
        skipped_candles = 0

        for live_stock_id, bt_stock_id in stock_id_map.items():
            live_stock = live_db.query(Stock).filter(Stock.id == live_stock_id).first()
            candles = live_db.query(Candle).filter(
                Candle.stock_id == live_stock_id
            ).all()

            if not candles:
                continue

            print(f"\n  Processing {live_stock.symbol}...")
            stock_added = 0
            stock_skipped = 0

            for candle in candles:
                # Check if candle already exists
                existing = backtest_db.query(Candle).filter(
                    Candle.stock_id == bt_stock_id,
                    Candle.timestamp == candle.timestamp,
                    Candle.timeframe == candle.timeframe
                ).first()

                if existing:
                    stock_skipped += 1
                    continue

                # Add candle
                bt_candle = Candle(
                    stock_id=bt_stock_id,
                    timestamp=candle.timestamp,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    timeframe=candle.timeframe
                )
                backtest_db.add(bt_candle)
                stock_added += 1
                added_candles += 1

            backtest_db.commit()
            skipped_candles += stock_skipped
            print(f"    ✅ Added: {stock_added}, Skipped: {stock_skipped}")

        total_candles = added_candles + skipped_candles

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Stocks: {len(live_stocks)}")
        print(f"Total candles: {total_candles}")
        print(f"  Added: {added_candles}")
        print(f"  Skipped (already exist): {skipped_candles}")
        print("=" * 60)
        print("\n✅ Copy complete!")
        print("\nYou can now:")
        print("1. Verify data: python3 scripts/load_historical_data.py --verify AAPL")
        print("2. Run backtests from the UI or API")
        print("3. Load more historical data: python3 scripts/load_historical_data.py --symbols AAPL")

    except Exception as e:
        print(f"\n❌ Error copying data: {e}")
        import traceback
        traceback.print_exc()
        backtest_db.rollback()
    finally:
        live_db.close()
        backtest_db.close()


if __name__ == "__main__":
    copy_live_to_backtest()
