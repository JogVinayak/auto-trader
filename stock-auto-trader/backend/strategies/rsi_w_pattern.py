import pandas as pd
from typing import Dict, Optional, Tuple
from .base import BaseStrategy, Signal


class RSIWPatternStrategy(BaseStrategy):
    """
    RSI W-Pattern and M-Pattern Strategy

    W-Pattern (Bullish Reversal):
    - Forms in oversold territory (RSI < threshold)
    - Two bottoms where second bottom >= first bottom (shows weakening selling pressure)
    - BUY signal when RSI breaks above the middle peak

    M-Pattern (Bearish Reversal):
    - Forms in overbought territory (RSI > threshold)
    - Two tops where second top <= first top (shows weakening buying pressure)
    - SELL signal when RSI breaks below the middle valley
    """

    name = "RSI_W_PATTERN"
    description = "RSI W-Pattern (bullish) and M-Pattern (bearish) reversal strategy"

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: int = 30,
        overbought_threshold: int = 70,
        min_distance: int = 3,
        max_distance: int = 10,
        tolerance: float = 3.0
    ):
        """
        Initialize RSI W/M Pattern strategy

        Args:
            rsi_period: Period for RSI calculation (default: 14)
            oversold_threshold: RSI level below which to look for W-patterns (default: 30)
            overbought_threshold: RSI level above which to look for M-patterns (default: 70)
            min_distance: Minimum candles between pattern bottoms/tops (default: 3)
            max_distance: Maximum candles between pattern bottoms/tops (default: 10)
            tolerance: RSI point tolerance for second bottom/top validation (default: 3.0)
        """
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.tolerance = tolerance

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI using EMA smoothing"""
        delta = prices.diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        # Use EMA for smoother RSI
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def find_local_extrema(self, rsi: pd.Series, window: int = 3) -> Tuple[list, list]:
        """
        Find local minima and maxima in RSI series

        Args:
            rsi: RSI series
            window: Window size for local extrema detection

        Returns:
            Tuple of (minima_indices, maxima_indices)
        """
        minima = []
        maxima = []

        for i in range(window, len(rsi) - window):
            # Check if local minimum
            if all(rsi.iloc[i] <= rsi.iloc[i-j] for j in range(1, window+1)) and \
               all(rsi.iloc[i] <= rsi.iloc[i+j] for j in range(1, window+1)):
                minima.append(i)

            # Check if local maximum
            if all(rsi.iloc[i] >= rsi.iloc[i-j] for j in range(1, window+1)) and \
               all(rsi.iloc[i] >= rsi.iloc[i+j] for j in range(1, window+1)):
                maxima.append(i)

        return minima, maxima

    def detect_w_pattern(self, rsi: pd.Series) -> Optional[Dict]:
        """
        Detect W-pattern in RSI (bullish reversal)

        Returns:
            Dict with pattern info if found, None otherwise
        """
        minima, maxima = self.find_local_extrema(rsi)

        # Need at least 2 minima in oversold zone
        oversold_minima = [i for i in minima if rsi.iloc[i] < self.oversold_threshold]

        if len(oversold_minima) < 2:
            return None

        # Check recent minima pairs
        for i in range(len(oversold_minima) - 1, 0, -1):
            idx2 = oversold_minima[i]  # Second bottom
            idx1 = oversold_minima[i-1]  # First bottom

            distance = idx2 - idx1

            # Check distance constraint
            if distance < self.min_distance or distance > self.max_distance:
                continue

            rsi1 = rsi.iloc[idx1]
            rsi2 = rsi.iloc[idx2]

            # Second bottom should be higher or within tolerance
            if rsi2 >= rsi1 - self.tolerance:
                # Find the peak between the two bottoms
                peak_idx = rsi.iloc[idx1:idx2+1].idxmax()
                peak_rsi = rsi.iloc[peak_idx]

                # Check if current RSI broke above the peak (confirmation)
                current_rsi = rsi.iloc[-1]
                prev_rsi = rsi.iloc[-2]

                # Signal: RSI breaks above middle peak
                if prev_rsi <= peak_rsi and current_rsi > peak_rsi:
                    return {
                        "pattern": "W",
                        "first_bottom": {"index": idx1, "rsi": rsi1},
                        "second_bottom": {"index": idx2, "rsi": rsi2},
                        "peak": {"index": peak_idx, "rsi": peak_rsi},
                        "current_rsi": current_rsi
                    }

        return None

    def detect_m_pattern(self, rsi: pd.Series) -> Optional[Dict]:
        """
        Detect M-pattern in RSI (bearish reversal)

        Returns:
            Dict with pattern info if found, None otherwise
        """
        minima, maxima = self.find_local_extrema(rsi)

        # Need at least 2 maxima in overbought zone
        overbought_maxima = [i for i in maxima if rsi.iloc[i] > self.overbought_threshold]

        if len(overbought_maxima) < 2:
            return None

        # Check recent maxima pairs
        for i in range(len(overbought_maxima) - 1, 0, -1):
            idx2 = overbought_maxima[i]  # Second top
            idx1 = overbought_maxima[i-1]  # First top

            distance = idx2 - idx1

            # Check distance constraint
            if distance < self.min_distance or distance > self.max_distance:
                continue

            rsi1 = rsi.iloc[idx1]
            rsi2 = rsi.iloc[idx2]

            # Second top should be lower or within tolerance
            if rsi2 <= rsi1 + self.tolerance:
                # Find the valley between the two tops
                valley_idx = rsi.iloc[idx1:idx2+1].idxmin()
                valley_rsi = rsi.iloc[valley_idx]

                # Check if current RSI broke below the valley (confirmation)
                current_rsi = rsi.iloc[-1]
                prev_rsi = rsi.iloc[-2]

                # Signal: RSI breaks below middle valley
                if prev_rsi >= valley_rsi and current_rsi < valley_rsi:
                    return {
                        "pattern": "M",
                        "first_top": {"index": idx1, "rsi": rsi1},
                        "second_top": {"index": idx2, "rsi": rsi2},
                        "valley": {"index": valley_idx, "rsi": valley_rsi},
                        "current_rsi": current_rsi
                    }

        return None

    def calculate(self, df: pd.DataFrame, full_history: bool = False) -> Dict:
        """Calculate trading signals based on RSI W/M patterns"""
        # Need sufficient data
        min_required = self.rsi_period + self.max_distance + 10
        if len(df) < min_required:
            return self.get_result(
                Signal.HOLD,
                0,
                f"Insufficient data for RSI W/M-Pattern (need {min_required} candles)"
            )

        # Calculate RSI
        rsi = self.calculate_rsi(df['close'])
        current_rsi = rsi.iloc[-1]

        # Prepare indicators for response
        # Use full history for backtesting, last 50 for live signals
        indicators = {
            "rsi": round(current_rsi, 2),
            "oversold_threshold": self.oversold_threshold,
            "overbought_threshold": self.overbought_threshold,
            "rsi_period": self.rsi_period,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
            # Historical data for plotting
            "rsi_line": [round(x, 2) for x in (rsi if full_history else rsi.tail(50)).tolist()],
            "timestamps": [str(t) for t in (df['timestamp'] if full_history else df['timestamp'].tail(50)).tolist()]
        }

        # Detect W-pattern (bullish)
        w_pattern = self.detect_w_pattern(rsi)
        if w_pattern:
            strength = min(100, int(
                (w_pattern["current_rsi"] - w_pattern["peak"]["rsi"]) * 5 + 70
            ))

            reason = (
                f"W-Pattern confirmed: RSI broke above middle peak ({w_pattern['peak']['rsi']:.1f}). "
                f"First bottom: {w_pattern['first_bottom']['rsi']:.1f}, "
                f"Second bottom: {w_pattern['second_bottom']['rsi']:.1f}"
            )

            indicators["pattern"] = "W"
            indicators["pattern_details"] = w_pattern

            return self.get_result(Signal.BUY, strength, reason, indicators)

        # Detect M-pattern (bearish)
        m_pattern = self.detect_m_pattern(rsi)
        if m_pattern:
            strength = min(100, int(
                (m_pattern["valley"]["rsi"] - m_pattern["current_rsi"]) * 5 + 70
            ))

            reason = (
                f"M-Pattern confirmed: RSI broke below middle valley ({m_pattern['valley']['rsi']:.1f}). "
                f"First top: {m_pattern['first_top']['rsi']:.1f}, "
                f"Second top: {m_pattern['second_top']['rsi']:.1f}"
            )

            indicators["pattern"] = "M"
            indicators["pattern_details"] = m_pattern

            return self.get_result(Signal.SELL, strength, reason, indicators)

        # No pattern detected - check if potential pattern is forming
        oversold_minima, _ = self.find_local_extrema(rsi)
        oversold_minima = [i for i in oversold_minima if rsi.iloc[i] < self.oversold_threshold]

        overbought_maxima, _ = self.find_local_extrema(rsi)
        overbought_maxima = [i for i in overbought_maxima if rsi.iloc[i] > self.overbought_threshold]

        if len(oversold_minima) >= 1 and current_rsi < self.oversold_threshold + 10:
            return self.get_result(
                Signal.HOLD,
                40,
                f"Potential W-Pattern forming in oversold zone. RSI: {current_rsi:.2f}",
                indicators
            )
        elif len(overbought_maxima) >= 1 and current_rsi > self.overbought_threshold - 10:
            return self.get_result(
                Signal.HOLD,
                40,
                f"Potential M-Pattern forming in overbought zone. RSI: {current_rsi:.2f}",
                indicators
            )
        else:
            return self.get_result(
                Signal.HOLD,
                50,
                f"No W/M-Pattern detected. RSI in neutral zone: {current_rsi:.2f}",
                indicators
            )
