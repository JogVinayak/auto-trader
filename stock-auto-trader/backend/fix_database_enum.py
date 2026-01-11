#!/usr/bin/env python3
"""
Fix TimeFrame enum in PostgreSQL database.
This script updates the enum to match the Python model definitions.
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("🔧 Fixing TimeFrame enum in database...")
print("=" * 50)

try:
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()

        try:
            # Check current enum values
            result = conn.execute(text("""
                SELECT enumlabel
                FROM pg_enum
                WHERE enumtypid = (
                    SELECT oid
                    FROM pg_type
                    WHERE typname = 'timeframe'
                )
                ORDER BY enumsortorder;
            """))

            current_values = [row[0] for row in result]
            print(f"Current enum values: {current_values}")

            # Expected values from Python enum
            expected_values = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '5h', '1d']
            print(f"Expected enum values: {expected_values}")

            # Check if we need to update
            if set(current_values) == set(expected_values):
                print("✅ Enum values are already correct!")
                trans.rollback()
            else:
                print("\n🔄 Updating enum values...")

                # Drop and recreate the enum type
                # First, we need to alter the columns to use text temporarily
                print("1. Converting timeframe column to text...")
                conn.execute(text("""
                    ALTER TABLE candles
                    ALTER COLUMN timeframe TYPE text
                    USING timeframe::text;
                """))

                print("2. Dropping old enum type...")
                conn.execute(text("DROP TYPE IF EXISTS timeframe CASCADE;"))

                print("3. Creating new enum type...")
                conn.execute(text("""
                    CREATE TYPE timeframe AS ENUM (
                        '1m', '5m', '15m', '30m',
                        '1h', '2h', '3h', '4h', '5h',
                        '1d'
                    );
                """))

                print("4. Updating timeframe values in data...")
                # Map old values to new values
                conn.execute(text("""
                    UPDATE candles SET timeframe = '1m' WHERE timeframe = 'M1';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '5m' WHERE timeframe = 'M5';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '15m' WHERE timeframe = 'M15';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '30m' WHERE timeframe = 'M30';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '1h' WHERE timeframe = 'H1';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '2h' WHERE timeframe = 'H2';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '3h' WHERE timeframe = 'H3';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '4h' WHERE timeframe = 'H4';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '5h' WHERE timeframe = 'H5';
                """))
                conn.execute(text("""
                    UPDATE candles SET timeframe = '1d' WHERE timeframe = 'D1';
                """))

                print("5. Converting timeframe column back to enum...")
                conn.execute(text("""
                    ALTER TABLE candles
                    ALTER COLUMN timeframe TYPE timeframe
                    USING timeframe::timeframe;
                """))

                # Commit the transaction
                trans.commit()
                print("\n✅ Database enum updated successfully!")

        except Exception as e:
            trans.rollback()
            raise e

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL is running")
    print("2. Check DATABASE_URL in .env file")
    print("3. Ensure you have database permissions")
    exit(1)

print("\n" + "=" * 50)
print("✅ All done! Restart your backend server.")
