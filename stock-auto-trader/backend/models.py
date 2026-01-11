from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float, DateTime,
    Boolean, Enum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()


class TimeFrame(enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H3 = "3h"
    H4 = "4h"
    H5 = "5h"
    D1 = "1d"


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(enum.Enum):
    MACD = "MACD"
    RSI = "RSI"
    MA_CROSSOVER = "MA_CROSSOVER"
    BOLLINGER = "BOLLINGER"
    MTF_EMA = "MTF_EMA"


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
    timeframe = Column(Enum(TimeFrame, values_callable=lambda x: [e.value for e in x]), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, default=0)  # BigInteger for crypto volumes
    
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
    trade_type = Column(Enum(TradeType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    strategy = Column(Enum(StrategyType, values_callable=lambda x: [e.value for e in x]), nullable=False)
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


# ============ INDICATOR VALUES TABLE ============
class IndicatorValue(Base):
    """Stores calculated indicator values for each candle"""
    __tablename__ = "indicator_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candle_id = Column(Integer, ForeignKey("candles.id"), nullable=False)
    strategy = Column(String(20), nullable=False)  # MACD, RSI, etc.

    # Common indicator fields
    signal = Column(String(10))  # BUY, SELL, HOLD
    strength = Column(Integer)  # 0-100

    # MACD specific
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)

    # RSI specific
    rsi_value = Column(Float)

    # MA Crossover specific
    short_ma = Column(Float)
    long_ma = Column(Float)

    # Bollinger specific
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_percent_b = Column(Float)

    # MTF_EMA specific
    ema_20 = Column(Float)
    ema_30 = Column(Float)
    ema_40 = Column(Float)
    ema_50 = Column(Float)
    ema_60 = Column(Float)
    ema_200 = Column(Float)
    ema_300 = Column(Float)
    bullish_count = Column(Integer)
    bearish_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candle = relationship("Candle", backref="indicators")

    __table_args__ = (
        UniqueConstraint('candle_id', 'strategy', name='unique_indicator_per_candle'),
        Index('idx_indicator_lookup', 'candle_id', 'strategy'),
    )


# ============ STRATEGY SETTINGS TABLE ============
class StrategySettings(Base):
    __tablename__ = "strategy_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy = Column(Enum(StrategyType, values_callable=lambda x: [e.value for e in x]), nullable=False, unique=True)

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