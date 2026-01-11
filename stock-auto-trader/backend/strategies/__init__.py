"""
Trading Strategy Module

Available strategies:
- MACD: Moving Average Convergence Divergence
- RSI: Relative Strength Index
- MA_CROSSOVER: Moving Average Crossover
- BOLLINGER: Bollinger Bands
- RSI_W_PATTERN: RSI W-Pattern and M-Pattern (reversal signals)
"""

from .base import BaseStrategy, Signal
from .macd import MACDStrategy
from .rsi import RSIStrategy
from .ma_crossover import MACrossoverStrategy
from .bollinger import BollingerStrategy
from .rsi_w_pattern import RSIWPatternStrategy


# Registry of all available strategies
STRATEGIES = {
    "MACD": MACDStrategy,
    "RSI": RSIStrategy,
    "MA_CROSSOVER": MACrossoverStrategy,
    "BOLLINGER": BollingerStrategy,
    "RSI_W_PATTERN": RSIWPatternStrategy,
}


def get_strategy(name: str) -> BaseStrategy:
    """
    Get a strategy instance by name

    Args:
        name: Strategy name (case-insensitive)

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy not found
    """
    name = name.upper()
    strategy_class = STRATEGIES.get(name)

    if not strategy_class:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    return strategy_class()


def get_all_strategies():
    """
    Get all available strategy names

    Returns:
        List of strategy names
    """
    return list(STRATEGIES.keys())


__all__ = [
    "BaseStrategy",
    "Signal",
    "MACDStrategy",
    "RSIStrategy",
    "MACrossoverStrategy",
    "BollingerStrategy",
    "RSIWPatternStrategy",
    "STRATEGIES",
    "get_strategy",
    "get_all_strategies",
]
