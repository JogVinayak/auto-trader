"""
Test Backtest Functionality

This script tests the backtesting engine directly without needing the API server.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import db_manager
from services.backtest_engine import BacktestEngine, BacktestConfig
from models import Stock, Candle, TimeFrame
from strategies import RSIWPatternStrategy
import pandas as pd
from datetime import datetime

def test_backtest(symbol='AAPL', strategy_name='RSI_W_PATTERN', timeframe='1d',
                  start_date='2024-01-01', end_date='2025-01-01'):
    """Run a test backtest"""

    print("=" * 60)
    print("Backtest Test")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Strategy: {strategy_name}")
    print(f"Timeframe: {timeframe}")
    print(f"Period: {start_date} to {end_date}")
    print()

    bt_db = db_manager.get_backtest_session()

    try:
        # Get stock
        stock = bt_db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"❌ Stock {symbol} not found in backtest database")
            return

        # Map timeframe
        tf_map = {"1m": TimeFrame.M1, "5m": TimeFrame.M5, "1h": TimeFrame.H1, "1d": TimeFrame.D1}
        tf = tf_map.get(timeframe)

        # Fetch historical candles
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        print(f"📊 Fetching candles...")
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

        print(f"✅ Found {len(candles)} candles")

        if len(candles) < 50:
            print(f"❌ Insufficient data. Need at least 50 candles, found {len(candles)}")
            return

        # Convert to DataFrame
        df = pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": int(c.volume)
        } for c in candles])

        print(f"\n📈 Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Initialize strategy
        print(f"\n🎯 Initializing {strategy_name} strategy...")
        strategy = RSIWPatternStrategy(
            rsi_period=14,
            oversold_threshold=30,
            overbought_threshold=70,
            min_distance=3,
            max_distance=10,
            tolerance=3.0
        )

        # Generate signals
        print(f"📡 Generating signals...")
        signals = []
        for i in range(len(df)):
            df_subset = df.iloc[:i+1]
            if len(df_subset) >= 50:
                result = strategy.calculate(df_subset)
                signals.append(result)
            else:
                signals.append({"signal": "HOLD", "strength": 0})

        buy_signals = sum(1 for s in signals if s.get('signal') == 'BUY')
        sell_signals = sum(1 for s in signals if s.get('signal') == 'SELL')
        print(f"✅ Generated {len(signals)} signals: {buy_signals} BUY, {sell_signals} SELL")

        # Run backtest
        print(f"\n🚀 Running backtest...")
        config = BacktestConfig(
            symbol=symbol,
            strategy_name=strategy_name,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            position_size=1.0
        )

        engine = BacktestEngine(config)
        result = engine.run(df, signals)

        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"\n💰 Performance:")
        print(f"   Initial Capital: ${config.initial_capital:,.2f}")
        print(f"   Final Value: ${config.initial_capital + result.total_return:,.2f}")
        print(f"   Total Return: ${result.total_return:,.2f} ({result.total_return_percent:.2f}%)")
        print(f"   Max Drawdown: ${result.max_drawdown:,.2f} ({result.max_drawdown_percent:.2f}%)")

        print(f"\n📊 Risk Metrics:")
        print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"   Win Rate: {result.win_rate:.2f}%")
        print(f"   Profit Factor: {result.profit_factor:.2f}")

        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades: {result.total_trades}")
        print(f"   Winning Trades: {result.winning_trades}")
        print(f"   Losing Trades: {result.losing_trades}")
        print(f"   Average Win: ${result.avg_win:.2f}")
        print(f"   Average Loss: ${result.avg_loss:.2f}")
        print(f"   Best Trade: ${result.best_trade:.2f}")
        print(f"   Worst Trade: ${result.worst_trade:.2f}")
        print(f"   Avg Duration: {result.avg_trade_duration:.2f} hours")

        if result.trades:
            print(f"\n📝 Recent Trades (last 5):")
            for trade in result.trades[-5:]:
                pnl_sign = "+" if trade.pnl >= 0 else ""
                print(f"   {trade.entry_date.date()} → {trade.exit_date.date() if trade.exit_date else 'Open'}: "
                      f"{pnl_sign}${trade.pnl:.2f} ({pnl_sign}{trade.pnl_percent:.2f}%)")

        print("\n" + "=" * 60)
        print("✅ Backtest completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running backtest: {e}")
        import traceback
        traceback.print_exc()
    finally:
        bt_db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test backtest functionality')
    parser.add_argument('--symbol', default='AAPL', help='Stock symbol')
    parser.add_argument('--strategy', default='RSI_W_PATTERN', help='Strategy name')
    parser.add_argument('--timeframe', default='1d', help='Timeframe')
    parser.add_argument('--start', default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2025-01-01', help='End date (YYYY-MM-DD)')

    args = parser.parse_args()

    test_backtest(
        symbol=args.symbol,
        strategy_name=args.strategy,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end
    )
