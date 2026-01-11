"""
Setup Backtest Database

This script creates the backtest database and sets up the schema.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models import Base
from dotenv import load_dotenv
import psycopg

load_dotenv()

def setup_backtest_database():
    """Create backtest database and set up schema"""

    backtest_url = os.getenv('BACKTEST_DATABASE_URL')
    if not backtest_url:
        print("❌ BACKTEST_DATABASE_URL not found in .env file")
        print("   Please add: BACKTEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/stock_trader_backtest")
        return False

    print("=" * 60)
    print("Backtest Database Setup")
    print("=" * 60)

    # Parse connection info
    parts = backtest_url.replace('postgresql+psycopg://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ''
    host_port = host_db[0].split(':')
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else '5432'
    dbname = host_db[1]

    print(f"Database: {dbname}")
    print(f"Host: {host}:{port}")
    print()

    try:
        # Try to connect to postgres database to create our database
        print("📦 Creating backtest database...")
        try:
            # Connect to default postgres database
            conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
            conn = psycopg.connect(conn_str, autocommit=True)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{dbname}'")
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(f"CREATE DATABASE {dbname}")
                print("✅ Database created successfully")
            else:
                print("ℹ️  Database already exists")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"ℹ️  Database might already exist or unable to create: {e}")
            print("   Proceeding with schema setup...")

        # Create tables
        print("\n📋 Creating database schema...")
        engine = create_engine(backtest_url, echo=False)
        Base.metadata.create_all(engine)
        print("✅ Schema created successfully")

        # Verify tables were created
        print("\n🔍 Verifying tables...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]

            if tables:
                print(f"✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found")

        print("\n" + "=" * 60)
        print("✅ Backtest database setup complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Load historical data:")
        print("   python3 scripts/load_historical_data.py --default")
        print("\n2. Verify data:")
        print("   python3 scripts/load_historical_data.py --verify AAPL")
        print("\n3. Run a backtest from the UI or API")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_backtest_database()
    sys.exit(0 if success else 1)
