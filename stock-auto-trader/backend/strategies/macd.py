import pandas as pd
from typing import Dict
from .base import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy
    
    BUY: MACD line crosses above Signal line
    SELL: MACD line crosses below Signal line
    """
    
    name = "MACD"
    description = "MACD crossover strategy"
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, df: pd.DataFrame, full_history: bool = False) -> Dict:
        if len(df) < self.slow_period + self.signal_period:
            return self.get_result(Signal.HOLD, 0, "Insufficient data for MACD calculation")

        # Calculate MACD
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        # Get current and previous values
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]

        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        prev_histogram = histogram.iloc[-2]

        # Add historical data for chart plotting
        # Use full history for backtesting, last 50 for live signals
        data_slice = macd_line if full_history else macd_line.tail(50)
        indicators = {
            "macd": round(current_macd, 4),
            "signal": round(current_signal, 4),
            "histogram": round(current_histogram, 4),
            "prev_histogram": round(prev_histogram, 4),
            # Historical data for plotting
            "macd_line": [round(x, 4) for x in data_slice.tolist()],
            "signal_line": [round(x, 4) for x in (signal_line if full_history else signal_line.tail(50)).tolist()],
            "histogram_line": [round(x, 4) for x in (histogram if full_history else histogram.tail(50)).tolist()],
            "timestamps": [str(t) for t in (df['timestamp'] if full_history else df['timestamp'].tail(50)).tolist()]
        }
        
        # Detect crossover
        # BUY: MACD crosses above signal (histogram goes from negative to positive)
        if prev_histogram < 0 and current_histogram > 0:
            strength = min(100, int(abs(current_histogram) * 1000))
            return self.get_result(
                Signal.BUY, 
                strength,
                f"MACD crossed above signal line (histogram: {current_histogram:.4f})",
                indicators
            )
        
        # SELL: MACD crosses below signal (histogram goes from positive to negative)
        elif prev_histogram > 0 and current_histogram < 0:
            strength = min(100, int(abs(current_histogram) * 1000))
            return self.get_result(
                Signal.SELL,
                strength,
                f"MACD crossed below signal line (histogram: {current_histogram:.4f})",
                indicators
            )
        
        # HOLD with trend indication
        else:
            if current_histogram > 0:
                reason = f"MACD above signal (bullish), histogram: {current_histogram:.4f}"
            else:
                reason = f"MACD below signal (bearish), histogram: {current_histogram:.4f}"
            
            return self.get_result(Signal.HOLD, 50, reason, indicators)