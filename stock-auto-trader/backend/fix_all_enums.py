#!/usr/bin/env python3
"""
Fix all enum types in PostgreSQL database.
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("🔧 Fixing all enums in database...")
print("=" * 50)

try:
    with engine.connect() as conn:
        trans = conn.begin()

        try:
            # Fix StrategyType enum
            print("\n1. Fixing StrategyType enum...")

            # Convert column to text
            conn.execute(text("ALTER TABLE trades ALTER COLUMN strategy TYPE text;"))
            conn.execute(text("ALTER TABLE strategy_settings ALTER COLUMN strategy TYPE text;"))

            # Drop and recreate enum
            conn.execute(text("DROP TYPE IF EXISTS strategytype CASCADE;"))
            conn.execute(text("""
                CREATE TYPE strategytype AS ENUM ('MACD', 'RSI', 'MA_CROSSOVER', 'BOLLINGER', 'MTF_EMA');
            """))

            # Convert back to enum
            conn.execute(text("ALTER TABLE trades ALTER COLUMN strategy TYPE strategytype USING strategy::strategytype;"))
            conn.execute(text("ALTER TABLE strategy_settings ALTER COLUMN strategy TYPE strategytype USING strategy::strategytype;"))

            print("   ✅ StrategyType enum fixed")

            # Fix TradeType enum
            print("\n2. Fixing TradeType enum...")

            # Convert column to text
            conn.execute(text("ALTER TABLE trades ALTER COLUMN trade_type TYPE text;"))

            # Drop and recreate enum
            conn.execute(text("DROP TYPE IF EXISTS tradetype CASCADE;"))
            conn.execute(text("""
                CREATE TYPE tradetype AS ENUM ('BUY', 'SELL');
            """))

            # Convert back to enum
            conn.execute(text("ALTER TABLE trades ALTER COLUMN trade_type TYPE tradetype USING trade_type::tradetype;"))

            print("   ✅ TradeType enum fixed")

            trans.commit()
            print("\n✅ All enums updated successfully!")

        except Exception as e:
            trans.rollback()
            raise e

except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)

print("\n" + "=" * 50)
print("✅ All done! Restart your backend server.")
