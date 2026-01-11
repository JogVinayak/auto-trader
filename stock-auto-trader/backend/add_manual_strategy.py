#!/usr/bin/env python3
"""
Add MANUAL to StrategyType enum in database
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("🔧 Adding MANUAL to StrategyType enum...")
print("=" * 50)

try:
    with engine.connect() as conn:
        trans = conn.begin()

        try:
            # Check if MANUAL already exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'strategytype')
                    AND enumlabel = 'MANUAL'
                );
            """))
            exists = result.scalar()

            if exists:
                print("✅ MANUAL already exists in StrategyType enum!")
                trans.rollback()
            else:
                print("Adding MANUAL to StrategyType enum...")
                conn.execute(text("""
                    ALTER TYPE strategytype ADD VALUE 'MANUAL';
                """))
                trans.commit()
                print("✅ MANUAL added successfully!")

        except Exception as e:
            trans.rollback()
            raise e

except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)

print("\n" + "=" * 50)
print("✅ Done! Restart your backend server.")
