import { useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Maximize2, Clock } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import TradesTable from './TradesTable';
import ChartModal from './ChartModal';
import './StrategyCard.css';

const StrategyCard = ({ strategy, signal, candles, trades = [], symbol, timeframe, onTimeframeChange }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const getSignalIcon = (signalType) => {
    switch (signalType) {
      case 'BUY':
        return <TrendingUp size={20} />;
      case 'SELL':
        return <TrendingDown size={20} />;
      default:
        return <Minus size={20} />;
    }
  };

  const getSignalClass = (signalType) => {
    switch (signalType) {
      case 'BUY':
        return 'buy';
      case 'SELL':
        return 'sell';
      default:
        return 'hold';
    }
  };

  const getStrategyIcon = (strategyName) => {
    const icons = {
      MACD: '📊',
      RSI: '📈',
      MA_CROSSOVER: '〰️',
      BOLLINGER: '📉',
      RSI_W_PATTERN: '📐',
    };
    return icons[strategyName] || '📊';
  };

  return (
    <div className="strategy-card">
      <div className="strategy-header">
        <div className="strategy-name">
          <div className={`strategy-icon ${strategy.toLowerCase()}`}>
            {getStrategyIcon(strategy)}
          </div>
          <div>
            <h3>{strategy.replace('_', ' ')}</h3>
            <p className="strategy-description">{signal.reason || 'No description available'}</p>
          </div>
        </div>
        {onTimeframeChange && (
          <div className="strategy-timeframe-selector">
            <Clock size={14} />
            <select
              value={timeframe}
              onChange={(e) => onTimeframeChange(e.target.value)}
              className="strategy-timeframe-dropdown"
              onClick={(e) => e.stopPropagation()}
            >
              <option value="1m">1m</option>
              <option value="5m">5m</option>
              <option value="1h">1h</option>
              <option value="1d">1d</option>
            </select>
          </div>
        )}
      </div>

      <div className="signal-section">
        <div className={`signal-badge ${getSignalClass(signal.signal)}`}>
          {getSignalIcon(signal.signal)}
          <span>{signal.signal}</span>
        </div>
        <div className="signal-strength">
          <span className="strength-label">Strength:</span>
          <div className="strength-bar">
            <div
              className={`strength-fill ${getSignalClass(signal.signal)}`}
              style={{ width: `${signal.strength}%` }}
            ></div>
          </div>
          <span className="strength-value">{signal.strength}%</span>
        </div>
      </div>

      {signal.indicators && Object.keys(signal.indicators).length > 0 && (
        <div className="indicators-section">
          <h4>Indicators</h4>
          <div className="indicators-grid">
            {Object.entries(signal.indicators).map(([key, value]) => {
              // Skip array-type values and object-type values (used for chart plotting or complex data)
              if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
                return null;
              }
              // Only render primitive values (numbers, strings, booleans)
              return (
                <div key={key} className="indicator-item">
                  <span className="indicator-label">{key.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="indicator-value">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {candles && candles.length > 0 && (
        <div className="chart-section">
          <button
            className="chart-expand-btn"
            onClick={() => setIsModalOpen(true)}
            title="Expand chart to fullscreen"
          >
            <Maximize2 size={16} />
            Expand
          </button>
          <TradingChartWithIndicators
            data={candles}
            height={900}
            currentSignal={signal.signal}
            strategyName={strategy}
            indicators={signal.indicators}
            trades={trades}
          />
        </div>
      )}

      <TradesTable trades={trades} strategy={strategy} />

      <ChartModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        strategy={strategy}
        signal={signal}
        candles={candles}
        symbol={symbol}
        trades={trades}
      />
    </div>
  );
};

export default StrategyCard;
