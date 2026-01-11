from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Boolean, Enum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()


class TimeFrame(enum.Enum):
    M1 = "1m"
    M5 = "5m"
    H1 = "1h"
    D1 = "1d"


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(enum.Enum):
    MACD = "MACD"
    RSI = "RSI"
    MA_CROSSOVER = "MA_CROSSOVER"
    BOLLINGER = "BOLLINGER"
    RSI_W_PATTERN = "RSI_W_PATTERN"


# ============ STOCKS TABLE ============
class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    candles = relationship("Candle", back_populates="stock", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="stock", cascade="all, delete-orphan")


# ============ CANDLES TABLE ============
class Candle(Base):
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    timeframe = Column(Enum(TimeFrame), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    
    # Relationships
    stock = relationship("Stock", back_populates="candles")
    
    # Unique constraint: one candle per stock/timeframe/timestamp
    __table_args__ = (
        UniqueConstraint('stock_id', 'timeframe', 'timestamp', name='unique_candle'),
        Index('idx_candle_lookup', 'stock_id', 'timeframe', 'timestamp'),
    )


# ============ TRADES TABLE ============
class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    trade_type = Column(Enum(TradeType), nullable=False)
    strategy = Column(Enum(StrategyType), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(500))
    
    # Relationships
    stock = relationship("Stock", back_populates="trades")


# ============ PORTFOLIO TABLE ============
class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cash_balance = Column(Float, default=10000.0)
    initial_capital = Column(Float, default=10000.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ HOLDINGS TABLE ============
class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, unique=True)
    quantity = Column(Integer, default=0)
    avg_buy_price = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock = relationship("Stock")


# ============ STRATEGY SETTINGS TABLE ============
class StrategySettings(Base):
    __tablename__ = "strategy_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy = Column(Enum(StrategyType), nullable=False, unique=True)

    # MACD settings
    macd_fast_period = Column(Integer, default=12)
    macd_slow_period = Column(Integer, default=26)
    macd_signal_period = Column(Integer, default=9)

    # RSI settings
    rsi_period = Column(Integer, default=14)
    rsi_overbought = Column(Integer, default=70)
    rsi_oversold = Column(Integer, default=30)

    # MA Crossover settings
    ma_short_period = Column(Integer, default=20)
    ma_long_period = Column(Integer, default=50)
    ma_type = Column(String(10), default="EMA")  # SMA or EMA

    # Bollinger Bands settings
    bollinger_period = Column(Integer, default=20)
    bollinger_std_dev = Column(Float, default=2.0)

    # RSI W-Pattern settings
    rsi_w_pattern_period = Column(Integer, default=14)
    rsi_w_pattern_oversold = Column(Integer, default=30)
    rsi_w_pattern_overbought = Column(Integer, default=70)
    rsi_w_pattern_min_distance = Column(Integer, default=3)
    rsi_w_pattern_max_distance = Column(Integer, default=10)
    rsi_w_pattern_tolerance = Column(Float, default=3.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ DATABASE SETUP ============
def get_engine(database_url: str):
    return create_engine(database_url, echo=False)


def create_tables(engine):
    Base.metadata.create_all(engine)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


# ============ INIT SCRIPT ============
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    engine = get_engine(database_url)
    create_tables(engine)
    
    # Initialize portfolio with starting capital
    session = get_session(engine)
    if not session.query(Portfolio).first():
        portfolio = Portfolio(cash_balance=10000.0, initial_capital=10000.0)
        session.add(portfolio)
        session.commit()
        print("✅ Portfolio initialized with $10,000")
    
    session.close()
    print("✅ All tables created successfully!")