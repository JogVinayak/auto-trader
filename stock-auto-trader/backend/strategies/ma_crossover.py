import pandas as pd
from typing import Dict
from .base import BaseStrategy, Signal


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    BUY: Short MA crosses above Long MA (Golden Cross)
    SELL: Short MA crosses below Long MA (Death Cross)
    """
    
    name = "MA_CROSSOVER"
    description = "Moving Average crossover strategy"
    
    def __init__(self, short_period: int = 20, long_period: int = 50, use_ema: bool = True):
        self.short_period = short_period
        self.long_period = long_period
        self.use_ema = use_ema
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        if len(df) < self.long_period + 1:
            return self.get_result(Signal.HOLD, 0, "Insufficient data for MA calculation")
        
        # Calculate MAs
        if self.use_ema:
            short_ma = df['close'].ewm(span=self.short_period, adjust=False).mean()
            long_ma = df['close'].ewm(span=self.long_period, adjust=False).mean()
            ma_type = "EMA"
        else:
            short_ma = df['close'].rolling(window=self.short_period).mean()
            long_ma = df['close'].rolling(window=self.long_period).mean()
            ma_type = "SMA"
        
        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]
        
        current_price = df['close'].iloc[-1]
        
        # Calculate distance between MAs as percentage
        ma_diff_pct = ((current_short - current_long) / current_long) * 100
        
        indicators = {
            f"short_{ma_type.lower()}_{self.short_period}": round(current_short, 2),
            f"long_{ma_type.lower()}_{self.long_period}": round(current_long, 2),
            "ma_diff_pct": round(ma_diff_pct, 2),
            "price": round(current_price, 2),
            # Historical data for plotting (last 50 points)
            f"short_ma_line": [round(x, 2) for x in short_ma.tail(50).tolist()],
            f"long_ma_line": [round(x, 2) for x in long_ma.tail(50).tolist()],
            "timestamps": [str(t) for t in df['timestamp'].tail(50).tolist()]
        }
        
        # BUY: Golden Cross - Short MA crosses above Long MA
        if prev_short <= prev_long and current_short > current_long:
            strength = min(100, int(abs(ma_diff_pct) * 20))
            return self.get_result(
                Signal.BUY,
                strength,
                f"Golden Cross: {ma_type}{self.short_period} crossed above {ma_type}{self.long_period}",
                indicators
            )
        
        # SELL: Death Cross - Short MA crosses below Long MA
        elif prev_short >= prev_long and current_short < current_long:
            strength = min(100, int(abs(ma_diff_pct) * 20))
            return self.get_result(
                Signal.SELL,
                strength,
                f"Death Cross: {ma_type}{self.short_period} crossed below {ma_type}{self.long_period}",
                indicators
            )
        
        # HOLD with trend indication
        else:
            if current_short > current_long:
                reason = f"Bullish: {ma_type}{self.short_period} above {ma_type}{self.long_period} ({ma_diff_pct:.2f}%)"
            else:
                reason = f"Bearish: {ma_type}{self.short_period} below {ma_type}{self.long_period} ({ma_diff_pct:.2f}%)"
            
            return self.get_result(Signal.HOLD, 50, reason, indicators)