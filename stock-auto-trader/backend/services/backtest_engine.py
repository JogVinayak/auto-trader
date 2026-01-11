"""
Backtesting Engine

Runs trading strategies on historical data and calculates performance metrics.
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    symbol: str
    strategy_name: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    position_size: float = 1.0  # Percentage of capital per trade (0-1)
    commission: float = 0.001  # 0.1% commission
    slippage: float = 0.001  # 0.1% slippage


@dataclass
class Trade:
    """Single trade record"""
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    position_type: PositionType = PositionType.LONG
    quantity: int = 0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    signal_strength: int = 0

    def close(self, exit_date: datetime, exit_price: float):
        """Close the trade"""
        self.exit_date = exit_date
        self.exit_price = exit_price

        if self.position_type == PositionType.LONG:
            self.pnl = (exit_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity

        self.pnl_percent = (self.pnl / (self.entry_price * self.quantity)) * 100


@dataclass
class BacktestResult:
    """Backtesting results with performance metrics"""
    config: BacktestConfig
    trades: List[Trade]
    equity_curve: List[float]
    equity_dates: List[datetime]

    # Performance metrics
    total_return: float = 0.0
    total_return_percent: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_trade_duration: float = 0.0  # in hours

    def calculate_metrics(self):
        """Calculate all performance metrics"""
        if not self.trades:
            return

        # Filter completed trades
        completed_trades = [t for t in self.trades if t.exit_date is not None]
        if not completed_trades:
            return

        self.total_trades = len(completed_trades)

        # Total return
        initial_capital = self.config.initial_capital
        final_capital = self.equity_curve[-1] if self.equity_curve else initial_capital
        self.total_return = final_capital - initial_capital
        self.total_return_percent = (self.total_return / initial_capital) * 100

        # Win/Loss statistics
        wins = [t for t in completed_trades if t.pnl > 0]
        losses = [t for t in completed_trades if t.pnl <= 0]

        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

        # Average metrics
        if wins:
            self.avg_win = sum(t.pnl for t in wins) / len(wins)
            self.best_trade = max(t.pnl for t in wins)

        if losses:
            self.avg_loss = sum(t.pnl for t in losses) / len(losses)
            self.worst_trade = min(t.pnl for t in losses)

        self.avg_trade = sum(t.pnl for t in completed_trades) / len(completed_trades)

        # Profit factor
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Max drawdown
        if self.equity_curve:
            peak = self.equity_curve[0]
            max_dd = 0
            for value in self.equity_curve:
                if value > peak:
                    peak = value
                dd = peak - value
                if dd > max_dd:
                    max_dd = dd

            self.max_drawdown = max_dd
            self.max_drawdown_percent = (max_dd / peak) * 100 if peak > 0 else 0

        # Sharpe ratio (simplified - assumes daily returns)
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                returns.append(ret)

            if returns:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5

                # Annualized Sharpe (assuming 252 trading days)
                self.sharpe_ratio = (mean_return / std_dev * (252 ** 0.5)) if std_dev > 0 else 0

        # Average trade duration
        durations = []
        for t in completed_trades:
            if t.entry_date and t.exit_date:
                duration = (t.exit_date - t.entry_date).total_seconds() / 3600  # hours
                durations.append(duration)

        self.avg_trade_duration = sum(durations) / len(durations) if durations else 0


class BacktestEngine:
    """
    Backtesting engine for trading strategies
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.capital = config.initial_capital
        self.position: Optional[Trade] = None
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [config.initial_capital]
        self.equity_dates: List[datetime] = []

    def run(self, candles: pd.DataFrame, signals: List[Dict]) -> BacktestResult:
        """
        Run backtest on historical data

        Args:
            candles: DataFrame with OHLCV data
            signals: List of signal dictionaries from strategy

        Returns:
            BacktestResult with trades and metrics
        """
        if candles.empty:
            return self._create_result()

        # Ensure signals are aligned with candles
        signal_dict = {i: sig for i, sig in enumerate(signals)}

        for i in range(len(candles)):
            candle = candles.iloc[i]
            signal = signal_dict.get(i, {})

            self._process_candle(candle, signal)

            # Record equity
            current_equity = self._calculate_equity(candle['close'])
            self.equity_curve.append(current_equity)
            self.equity_dates.append(candle['timestamp'])

        # Close any open position at the end
        if self.position:
            last_candle = candles.iloc[-1]
            self._close_position(last_candle['timestamp'], last_candle['close'])

        return self._create_result()

    def _process_candle(self, candle: pd.Series, signal: Dict):
        """Process a single candle and execute trades based on signals"""
        signal_type = signal.get('signal', 'HOLD')
        signal_strength = signal.get('strength', 0)

        # Exit logic - close position on opposite signal or stop loss
        if self.position:
            should_exit = False

            if self.position.position_type == PositionType.LONG and signal_type == 'SELL':
                should_exit = True
            elif self.position.position_type == PositionType.SHORT and signal_type == 'BUY':
                should_exit = True

            if should_exit:
                exit_price = self._apply_slippage(candle['close'], sell=True)
                self._close_position(candle['timestamp'], exit_price)

        # Entry logic - open position on signal
        if not self.position:
            if signal_type == 'BUY':
                entry_price = self._apply_slippage(candle['close'], sell=False)
                self._open_position(
                    candle['timestamp'],
                    entry_price,
                    PositionType.LONG,
                    signal_strength
                )
            elif signal_type == 'SELL':
                entry_price = self._apply_slippage(candle['close'], sell=True)
                self._open_position(
                    candle['timestamp'],
                    entry_price,
                    PositionType.SHORT,
                    signal_strength
                )

    def _open_position(self, date: datetime, price: float, position_type: PositionType, signal_strength: int):
        """Open a new position"""
        # Calculate position size
        capital_to_use = self.capital * self.config.position_size

        # Apply commission
        capital_after_commission = capital_to_use * (1 - self.config.commission)

        # Calculate quantity (integer shares)
        quantity = int(capital_after_commission / price)

        if quantity > 0:
            self.position = Trade(
                entry_date=date,
                entry_price=price,
                position_type=position_type,
                quantity=quantity,
                signal_strength=signal_strength
            )

            # Deduct capital
            self.capital -= quantity * price * (1 + self.config.commission)

    def _close_position(self, date: datetime, price: float):
        """Close the current position"""
        if not self.position:
            return

        # Apply commission
        proceeds = self.position.quantity * price * (1 - self.config.commission)

        # Close trade
        self.position.close(date, price)

        # Update capital
        self.capital += proceeds

        # Record trade
        self.trades.append(self.position)
        self.position = None

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current total equity"""
        equity = self.capital

        if self.position:
            # Add unrealized P&L
            if self.position.position_type == PositionType.LONG:
                position_value = self.position.quantity * current_price
            else:  # SHORT
                position_value = self.position.quantity * (2 * self.position.entry_price - current_price)

            equity += position_value

        return equity

    def _apply_slippage(self, price: float, sell: bool) -> float:
        """Apply slippage to price"""
        if sell:
            return price * (1 - self.config.slippage)
        else:
            return price * (1 + self.config.slippage)

    def _create_result(self) -> BacktestResult:
        """Create backtest result with calculated metrics"""
        result = BacktestResult(
            config=self.config,
            trades=self.trades,
            equity_curve=self.equity_curve,
            equity_dates=self.equity_dates
        )

        result.calculate_metrics()
        return result
