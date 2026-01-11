"""
Migration script to add RSI W-Pattern columns to strategy_settings table
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("❌ DATABASE_URL not found in environment variables")
    exit(1)

# Create engine
engine = create_engine(database_url, echo=True)

print("🔄 Step 1: Adding RSI_W_PATTERN to PostgreSQL enum type...")

# SQL to add new enum value
enum_migration_sql = """
-- Add RSI_W_PATTERN to the strategytype enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'RSI_W_PATTERN'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'strategytype')
    ) THEN
        ALTER TYPE strategytype ADD VALUE 'RSI_W_PATTERN';
    END IF;
END $$;
"""

print("🔄 Step 2: Adding RSI W-Pattern columns to strategy_settings table...")

# SQL to add new columns
column_migration_sql = """
-- Add RSI W-Pattern settings columns
ALTER TABLE strategy_settings
ADD COLUMN IF NOT EXISTS rsi_w_pattern_period INTEGER DEFAULT 14,
ADD COLUMN IF NOT EXISTS rsi_w_pattern_oversold INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS rsi_w_pattern_overbought INTEGER DEFAULT 70,
ADD COLUMN IF NOT EXISTS rsi_w_pattern_min_distance INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS rsi_w_pattern_max_distance INTEGER DEFAULT 10,
ADD COLUMN IF NOT EXISTS rsi_w_pattern_tolerance FLOAT DEFAULT 3.0;
"""

try:
    with engine.connect() as conn:
        # Step 1: Add enum value
        conn.execute(text(enum_migration_sql))
        conn.commit()
        print("✅ Step 1 complete: RSI_W_PATTERN added to enum type")

        # Step 2: Add columns
        conn.execute(text(column_migration_sql))
        conn.commit()
        print("✅ Step 2 complete: RSI W-Pattern columns added")

        # Verify enum value
        result = conn.execute(text("""
            SELECT enumlabel
            FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'strategytype')
            ORDER BY enumlabel;
        """))

        enum_values = [row[0] for row in result]
        print(f"\n✅ Verified enum values ({len(enum_values)}):")
        for val in enum_values:
            print(f"   - {val}")

        # Verify columns were added
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'strategy_settings'
            AND column_name LIKE 'rsi_w_pattern%'
            ORDER BY column_name;
        """))

        columns = [row[0] for row in result]
        print(f"\n✅ Verified columns added ({len(columns)}):")
        for col in columns:
            print(f"   - {col}")

except Exception as e:
    print(f"❌ Error during migration: {e}")
    exit(1)

print("\n✅ Migration completed successfully!")
print("🚀 You can now restart your backend server.")
