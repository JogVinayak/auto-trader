import pandas as pd
from typing import Dict
from .base import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) Strategy
    
    BUY: RSI crosses above oversold level (30)
    SELL: RSI crosses below overbought level (70)
    """
    
    name = "RSI"
    description = "RSI overbought/oversold strategy"
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=1).mean()
        
        # Use EMA for smoother RSI
        avg_gain = gain.ewm(span=self.period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        if len(df) < self.period + 1:
            return self.get_result(Signal.HOLD, 0, "Insufficient data for RSI calculation")
        
        rsi = self.calculate_rsi(df['close'])
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        indicators = {
            "rsi": round(current_rsi, 2),
            "prev_rsi": round(prev_rsi, 2),
            "oversold": self.oversold,
            "overbought": self.overbought,
            # Historical data for plotting (last 50 points)
            "rsi_line": [round(x, 2) for x in rsi.tail(50).tolist()],
            "timestamps": [str(t) for t in df['timestamp'].tail(50).tolist()]
        }
        
        # BUY: RSI crosses above oversold level
        if prev_rsi < self.oversold and current_rsi >= self.oversold:
            strength = int((self.oversold - prev_rsi) * 3)
            return self.get_result(
                Signal.BUY,
                strength,
                f"RSI crossed above oversold ({self.oversold}): {current_rsi:.2f}",
                indicators
            )
        
        # Strong BUY: RSI in oversold territory
        elif current_rsi < self.oversold:
            strength = int((self.oversold - current_rsi) * 3)
            return self.get_result(
                Signal.BUY,
                strength,
                f"RSI in oversold territory: {current_rsi:.2f}",
                indicators
            )
        
        # SELL: RSI crosses below overbought level
        elif prev_rsi > self.overbought and current_rsi <= self.overbought:
            strength = int((prev_rsi - self.overbought) * 3)
            return self.get_result(
                Signal.SELL,
                strength,
                f"RSI crossed below overbought ({self.overbought}): {current_rsi:.2f}",
                indicators
            )
        
        # Strong SELL: RSI in overbought territory
        elif current_rsi > self.overbought:
            strength = int((current_rsi - self.overbought) * 3)
            return self.get_result(
                Signal.SELL,
                strength,
                f"RSI in overbought territory: {current_rsi:.2f}",
                indicators
            )
        
        # HOLD: RSI in neutral zone
        else:
            return self.get_result(
                Signal.HOLD,
                50,
                f"RSI in neutral zone: {current_rsi:.2f}",
                indicators
            )