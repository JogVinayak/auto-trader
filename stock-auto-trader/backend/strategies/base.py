from enum import Enum
from typing import Dict, Optional
from abc import ABC, abstractmethod
import pandas as pd


class Signal(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class BaseStrategy(ABC):
    """
    Base class for all trading strategies

    All strategies must implement:
    - name: strategy identifier
    - description: human-readable description
    - calculate(df): returns signal dict with signal, strength, reason, indicators
    """

    name: str = "BASE"
    description: str = "Base strategy class"

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> Dict:
        """
        Calculate trading signal based on price data

        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume

        Returns:
            Dict with keys: strategy, signal, strength, reason, indicators
        """
        pass

    def get_result(
        self,
        signal: Signal,
        strength: int,
        reason: str,
        indicators: Optional[Dict] = None
    ) -> Dict:
        """
        Format strategy result

        Args:
            signal: Signal enum (BUY/SELL/HOLD)
            strength: Signal strength 0-100
            reason: Human-readable explanation
            indicators: Optional dict of technical indicator values

        Returns:
            Formatted result dict
        """
        return {
            "strategy": self.name,
            "signal": signal.value,
            "strength": max(0, min(100, strength)),  # Clamp to 0-100
            "reason": reason,
            "indicators": indicators or {}
        }
