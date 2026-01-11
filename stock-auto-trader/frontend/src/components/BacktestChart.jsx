import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, TrendingUp, TrendingDown } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import './BacktestChart.css';

const BacktestChart = ({ trades, equityCurve, equityDates, strategyName, symbol, allCandles, allIndicators }) => {
  const [currentTradeIndex, setCurrentTradeIndex] = useState(0);
  const chartRef = useRef(null);

  if (!trades || trades.length === 0) {
    return (
      <div className="backtest-chart-empty">
        <p>No trades were executed in this backtest period.</p>
      </div>
    );
  }

  const currentTrade = trades[currentTradeIndex];

  const goToFirst = () => setCurrentTradeIndex(0);
  const goToPrevious = () => setCurrentTradeIndex(Math.max(0, currentTradeIndex - 1));
  const goToNext = () => setCurrentTradeIndex(Math.min(trades.length - 1, currentTradeIndex + 1));
  const goToLast = () => setCurrentTradeIndex(trades.length - 1);

  const isProfit = currentTrade.pnl >= 0;
  const tradeType = currentTrade.type === 'LONG' ? 'BUY' : 'SELL';

  // Use all candles if available, otherwise fall back to trade-specific candles
  const chartData = allCandles && allCandles.length > 0 ? allCandles : currentTrade.candles;

  // Create ALL trade markers for the chart (not just current trade)
  const allTradeMarkers = trades.map(trade => ({
    timestamp: trade.entry_date,
    type: trade.type === 'LONG' ? 'BUY' : 'SELL',
    entry_time: trade.entry_date,
    entry_price: trade.entry_price,
    exit_time: trade.exit_date,
    exit_price: trade.exit_price,
    pnl: trade.pnl,
    strategy: strategyName,
    isCurrentTrade: trade === currentTrade
  }));

  // Scroll to current trade when trade changes
  useEffect(() => {
    if (chartRef.current && allCandles && allCandles.length > 0) {
      // Find the entry timestamp for the current trade
      const entryTimestamp = new Date(currentTrade.entry_date).getTime() / 1000;

      // Scroll the chart to show the trade
      // The TradingChartWithIndicators component will need to expose a scroll method
      // For now, we'll pass the current trade timestamp as a prop
    }
  }, [currentTradeIndex, currentTrade, allCandles]);

  return (
    <div className="backtest-chart-container">
      <div className="trade-navigation">
        <div className="nav-header">
          <h4>Trade Explorer - {symbol}</h4>
          <span className="trade-counter">
            Trade {currentTradeIndex + 1} of {trades.length}
          </span>
        </div>

        <div className="nav-controls">
          <button
            onClick={goToFirst}
            disabled={currentTradeIndex === 0}
            className="nav-btn"
            title="First trade"
          >
            <ChevronsLeft size={18} />
          </button>
          <button
            onClick={goToPrevious}
            disabled={currentTradeIndex === 0}
            className="nav-btn"
            title="Previous trade"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={goToNext}
            disabled={currentTradeIndex === trades.length - 1}
            className="nav-btn"
            title="Next trade"
          >
            <ChevronRight size={18} />
          </button>
          <button
            onClick={goToLast}
            disabled={currentTradeIndex === trades.length - 1}
            className="nav-btn"
            title="Last trade"
          >
            <ChevronsRight size={18} />
          </button>
        </div>
      </div>

      <div className="trade-details-card">
        <div className="trade-header">
          <div className={`trade-type-badge ${tradeType.toLowerCase()}`}>
            {tradeType === 'BUY' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {tradeType}
          </div>
          <div className={`trade-result ${isProfit ? 'profit' : 'loss'}`}>
            {isProfit ? '+' : ''} ${currentTrade.pnl.toFixed(2)} ({isProfit ? '+' : ''}{currentTrade.pnl_percent.toFixed(2)}%)
          </div>
        </div>

        <div className="trade-info-grid">
          <div className="info-item">
            <span className="info-label">Entry Date</span>
            <span className="info-value">{new Date(currentTrade.entry_date).toLocaleDateString()}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Entry Price</span>
            <span className="info-value">${currentTrade.entry_price.toFixed(2)}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Exit Date</span>
            <span className="info-value">
              {currentTrade.exit_date ? new Date(currentTrade.exit_date).toLocaleDateString() : 'Open'}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">Exit Price</span>
            <span className="info-value">
              {currentTrade.exit_price ? `$${currentTrade.exit_price.toFixed(2)}` : '-'}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">Quantity</span>
            <span className="info-value">{currentTrade.quantity}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Duration</span>
            <span className="info-value">
              {currentTrade.exit_date
                ? Math.floor((new Date(currentTrade.exit_date) - new Date(currentTrade.entry_date)) / (1000 * 60 * 60 * 24)) + ' days'
                : 'Ongoing'}
            </span>
          </div>
        </div>

        {/* Candlestick Chart showing all candles or trade-specific candles */}
        {chartData && chartData.length > 0 && (
          <div className="trade-chart-section">
            <h5>
              {allCandles && allCandles.length > 0
                ? `Complete Backtest Period - Showing Trade ${currentTradeIndex + 1}`
                : 'Price Action During Trade'}
            </h5>
            <TradingChartWithIndicators
              ref={chartRef}
              data={chartData}
              height={1125}
              currentSignal={null}
              strategyName={strategyName}
              indicators={allIndicators || currentTrade.indicators || null}
              trades={allTradeMarkers}
              scrollToTimestamp={new Date(currentTrade.entry_date).getTime() / 1000}
            />
          </div>
        )}

        <div className="trade-conditions">
          <h5>Strategy Conditions - {strategyName}</h5>
          <div className="conditions-list">
            <div className="condition-item">
              <span className="condition-icon">✓</span>
              <span className="condition-text">
                {tradeType === 'BUY' ? 'Bullish signal detected' : 'Bearish signal detected'}
              </span>
            </div>
            <div className="condition-item">
              <span className="condition-icon">✓</span>
              <span className="condition-text">
                Price: ${currentTrade.entry_price.toFixed(2)}
              </span>
            </div>
            {currentTrade.exit_date && (
              <div className="condition-item">
                <span className="condition-icon">✓</span>
                <span className="condition-text">
                  Exit triggered at ${currentTrade.exit_price.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="equity-chart">
        <h5>Portfolio Equity Curve</h5>
        <p className="equity-note">Shows portfolio value over the entire backtest period</p>
        <div className="equity-placeholder">
          {equityCurve && equityCurve.length > 0 && (
            <div className="equity-stats">
              <div className="equity-stat">
                <span className="stat-label">Start</span>
                <span className="stat-value">${equityCurve[0].toFixed(2)}</span>
              </div>
              <div className="equity-stat">
                <span className="stat-label">End</span>
                <span className={`stat-value ${equityCurve[equityCurve.length - 1] >= equityCurve[0] ? 'positive' : 'negative'}`}>
                  ${equityCurve[equityCurve.length - 1].toFixed(2)}
                </span>
              </div>
              <div className="equity-stat">
                <span className="stat-label">Change</span>
                <span className={`stat-value ${equityCurve[equityCurve.length - 1] >= equityCurve[0] ? 'positive' : 'negative'}`}>
                  {((equityCurve[equityCurve.length - 1] - equityCurve[0]) / equityCurve[0] * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BacktestChart;
