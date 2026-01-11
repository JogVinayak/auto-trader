"""
Database Manager for Live and Backtest Databases

Manages connections to both live trading database and separate backtest database
for historical data analysis without affecting live trading data.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class DatabaseManager:
    """Manages connections to live and backtest databases"""

    def __init__(self):
        self.live_url = os.getenv("DATABASE_URL")
        self.backtest_url = os.getenv("BACKTEST_DATABASE_URL", self.live_url)

        if not self.live_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Create engines for both databases
        self.live_engine = create_engine(self.live_url, echo=False, pool_pre_ping=True)
        self.backtest_engine = create_engine(self.backtest_url, echo=False, pool_pre_ping=True)

        # Create session makers
        self.LiveSession = sessionmaker(bind=self.live_engine, autocommit=False, autoflush=False)
        self.BacktestSession = sessionmaker(bind=self.backtest_engine, autocommit=False, autoflush=False)

    def get_live_session(self) -> Session:
        """Get a new session for the live database"""
        return self.LiveSession()

    def get_backtest_session(self) -> Session:
        """Get a new session for the backtest database"""
        return self.BacktestSession()

    def switch_to_live(self) -> Session:
        """Switch to live database (alias for get_live_session)"""
        return self.get_live_session()

    def switch_to_backtest(self) -> Session:
        """Switch to backtest database (alias for get_backtest_session)"""
        return self.get_backtest_session()

    def close_all(self):
        """Close all database connections"""
        self.live_engine.dispose()
        self.backtest_engine.dispose()


# Global instance
db_manager = DatabaseManager()
