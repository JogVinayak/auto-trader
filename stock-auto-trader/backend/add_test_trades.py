"""
Add test trades to database to demonstrate buy/sell indicators on charts
"""
from datetime import datetime, timedelta
from database import SessionLocal
from models import Stock, Trade, TradeType, StrategyType

def add_test_trades():
    db = SessionLocal()

    try:
        # Get AAPL stock
        stock = db.query(Stock).filter(Stock.symbol == "AAPL").first()
        if not stock:
            print("❌ AAPL stock not found")
            return

        print(f"✅ Found stock: {stock.symbol}")

        # Create test trades spanning last 30 days
        base_time = datetime.now() - timedelta(days=30)

        trades_data = [
            # Trade 1: MACD BUY (closed with profit)
            {
                "stock_id": stock.id,
                "trade_type": TradeType.BUY,
                "strategy": StrategyType.MACD,
                "quantity": 10,
                "entry_price": 180.50,
                "entry_time": base_time + timedelta(days=5),
                "exit_price": 185.25,
                "exit_time": base_time + timedelta(days=10),
                "pnl": 47.50,
                "pnl_percent": 2.63
            },
            # Trade 2: RSI SELL (closed with loss)
            {
                "stock_id": stock.id,
                "trade_type": TradeType.SELL,
                "strategy": StrategyType.RSI,
                "quantity": 15,
                "entry_price": 183.00,
                "entry_time": base_time + timedelta(days=12),
                "exit_price": 182.10,
                "exit_time": base_time + timedelta(days=15),
                "pnl": -13.50,
                "pnl_percent": -0.49
            },
            # Trade 3: MA_CROSSOVER BUY (open)
            {
                "stock_id": stock.id,
                "trade_type": TradeType.BUY,
                "strategy": StrategyType.MA_CROSSOVER,
                "quantity": 20,
                "entry_price": 179.80,
                "entry_time": base_time + timedelta(days=18),
                "exit_price": None,
                "exit_time": None,
                "pnl": 0,
                "pnl_percent": 0
            },
            # Trade 4: BOLLINGER BUY (closed with profit)
            {
                "stock_id": stock.id,
                "trade_type": TradeType.BUY,
                "strategy": StrategyType.BOLLINGER,
                "quantity": 12,
                "entry_price": 177.50,
                "entry_time": base_time + timedelta(days=20),
                "exit_price": 182.00,
                "exit_time": base_time + timedelta(days=25),
                "pnl": 54.00,
                "pnl_percent": 3.04
            },
        ]

        for trade_data in trades_data:
            trade = Trade(
                stock_id=trade_data["stock_id"],
                trade_type=trade_data["trade_type"],
                strategy=trade_data["strategy"],
                quantity=trade_data["quantity"],
                entry_price=trade_data["entry_price"],
                timestamp=trade_data["entry_time"],
                exit_price=trade_data["exit_price"],
                exit_time=trade_data["exit_time"],
                pnl=trade_data["pnl"],
                pnl_percent=trade_data["pnl_percent"]
            )
            db.add(trade)
            print(f"✅ Added {trade_data['trade_type'].value} trade for {trade_data['strategy'].value}")

        db.commit()
        print("\n🎉 Successfully added test trades!")
        print("\nTrade markers will appear on charts:")
        print("  🔵 Blue circles = BUY entries")
        print("  🟠 Orange circles = SELL entries")
        print("  🟢 Green squares = Profitable exits")
        print("  🔴 Red squares = Loss exits")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_trades()
