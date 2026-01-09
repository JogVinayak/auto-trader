import pandas as pd
from typing import Dict
from .base import BaseStrategy, Signal


class BollingerStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy
    
    BUY: Price touches/crosses below lower band (oversold)
    SELL: Price touches/crosses above upper band (overbought)
    """
    
    name = "BOLLINGER"
    description = "Bollinger Bands mean reversion strategy"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        if len(df) < self.period + 1:
            return self.get_result(Signal.HOLD, 0, "Insufficient data for Bollinger calculation")
        
        # Calculate Bollinger Bands
        middle_band = df['close'].rolling(window=self.period).mean()
        std = df['close'].rolling(window=self.period).std()
        
        upper_band = middle_band + (std * self.std_dev)
        lower_band = middle_band - (std * self.std_dev)
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_middle = middle_band.iloc[-1]
        
        prev_upper = upper_band.iloc[-2]
        prev_lower = lower_band.iloc[-2]
        
        # Calculate %B (position within bands)
        band_width = current_upper - current_lower
        percent_b = (current_price - current_lower) / band_width if band_width > 0 else 0.5
        
        # Calculate bandwidth as percentage
        bandwidth_pct = (band_width / current_middle) * 100
        
        indicators = {
            "price": round(current_price, 2),
            "upper_band": round(current_upper, 2),
            "middle_band": round(current_middle, 2),
            "lower_band": round(current_lower, 2),
            "percent_b": round(percent_b, 4),
            "bandwidth_pct": round(bandwidth_pct, 2),
            # Historical data for plotting (last 50 points)
            "upper_band_line": [round(x, 2) for x in upper_band.tail(50).tolist()],
            "middle_band_line": [round(x, 2) for x in middle_band.tail(50).tolist()],
            "lower_band_line": [round(x, 2) for x in lower_band.tail(50).tolist()],
            "timestamps": [str(t) for t in df['timestamp'].tail(50).tolist()]
        }
        
        # BUY: Price crosses below lower band or bounces from it
        if current_price <= current_lower:
            strength = min(100, int((1 - percent_b) * 100))
            return self.get_result(
                Signal.BUY,
                strength,
                f"Price at/below lower band (oversold): {current_price:.2f} <= {current_lower:.2f}",
                indicators
            )
        
        # BUY: Price bounced from lower band
        elif prev_price <= prev_lower and current_price > current_lower:
            strength = min(100, int((0.5 - percent_b) * 100) + 50) if percent_b < 0.5 else 60
            return self.get_result(
                Signal.BUY,
                strength,
                f"Price bounced from lower band: {prev_price:.2f} -> {current_price:.2f}",
                indicators
            )
        
        # SELL: Price crosses above upper band
        elif current_price >= current_upper:
            strength = min(100, int(percent_b * 100))
            return self.get_result(
                Signal.SELL,
                strength,
                f"Price at/above upper band (overbought): {current_price:.2f} >= {current_upper:.2f}",
                indicators
            )
        
        # SELL: Price rejected from upper band
        elif prev_price >= prev_upper and current_price < current_upper:
            strength = min(100, int((percent_b - 0.5) * 100) + 50) if percent_b > 0.5 else 60
            return self.get_result(
                Signal.SELL,
                strength,
                f"Price rejected from upper band: {prev_price:.2f} -> {current_price:.2f}",
                indicators
            )
        
        # HOLD: Price within bands
        else:
            if percent_b > 0.5:
                reason = f"Price in upper half of bands (%B: {percent_b:.2f})"
            else:
                reason = f"Price in lower half of bands (%B: {percent_b:.2f})"
            
            return self.get_result(Signal.HOLD, 50, reason, indicators)