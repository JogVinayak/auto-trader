import { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus, Maximize2, ChevronDown, RefreshCw } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import TradesTable from './TradesTable';
import ChartModal from './ChartModal';
import { candlesAPI, signalsAPI } from '../services/api';
import './StrategyCard.css';

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '1h', label: '1h' },
  { value: '1d', label: '1d' },
];

const StrategyCard = ({ strategy, signal: initialSignal, candles: initialCandles, trades = [], symbol }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Timeframe state
  const [selectedTimeframe, setSelectedTimeframe] = useState('1d');
  const [chartCandles, setChartCandles] = useState(initialCandles);
  const [chartSignal, setChartSignal] = useState(initialSignal);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Reset to initial data when props change
  useEffect(() => {
    setChartCandles(initialCandles);
    setChartSignal(initialSignal);
    setSelectedTimeframe('1d');
  }, [initialCandles, initialSignal]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };

    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  // Fetch candles for selected timeframe
  const fetchCandlesForTimeframe = async (timeframe) => {
    if (!symbol) return;

    try {
      setLoading(true);
      const candlesRes = await candlesAPI.get(symbol, timeframe, 200);

      if (candlesRes.data && candlesRes.data.length > 0) {
        setChartCandles(candlesRes.data);

        // Also fetch signals for this timeframe
        try {
          const signalsRes = await signalsAPI.get(symbol, timeframe, strategy);
          const signals = signalsRes.data.signals || [];
          const strategySignal = signals.find(s => s.strategy === strategy);
          if (strategySignal) {
            setChartSignal(strategySignal);
          }
        } catch (signalError) {
          console.log('Could not fetch signals for timeframe:', signalError.message);
        }
      } else {
        setChartCandles([]);
      }
    } catch (error) {
      console.error(`Error fetching ${timeframe} candles:`, error);
      if (error.response?.status === 400) {
        setChartCandles([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Sync candles for the selected timeframe
  const handleSyncTimeframe = async () => {
    if (!symbol || syncing) return;

    try {
      setSyncing(true);
      await candlesAPI.sync(symbol, selectedTimeframe, false);
      await fetchCandlesForTimeframe(selectedTimeframe);
    } catch (error) {
      console.error('Error syncing candles:', error);
    } finally {
      setSyncing(false);
    }
  };

  // Handle timeframe change
  const handleTimeframeChange = (timeframe) => {
    setSelectedTimeframe(timeframe);
    setDropdownOpen(false);
    if (timeframe !== '1d') {
      fetchCandlesForTimeframe(timeframe);
    } else {
      // Reset to initial data for 1d
      setChartCandles(initialCandles);
      setChartSignal(initialSignal);
    }
  };
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
    };
    return icons[strategyName] || '📊';
  };

  // Use initialSignal for the header/badge (always shows original), chartSignal for indicators/chart
  const displaySignal = chartSignal || initialSignal;

  return (
    <div className="strategy-card">
      <div className="strategy-header">
        <div className="strategy-name">
          <div className={`strategy-icon ${strategy.toLowerCase()}`}>
            {getStrategyIcon(strategy)}
          </div>
          <div>
            <h3>{strategy.replace('_', ' ')}</h3>
            <p className="strategy-description">{initialSignal?.reason || ''}</p>
          </div>
        </div>
      </div>

      <div className="signal-section">
        <div className={`signal-badge ${getSignalClass(initialSignal?.signal)}`}>
          {getSignalIcon(initialSignal?.signal)}
          <span>{initialSignal?.signal || 'HOLD'}</span>
        </div>
        <div className="signal-strength">
          <span className="strength-label">Strength:</span>
          <div className="strength-bar">
            <div
              className={`strength-fill ${getSignalClass(initialSignal?.signal)}`}
              style={{ width: `${initialSignal?.strength || 0}%` }}
            ></div>
          </div>
          <span className="strength-value">{initialSignal?.strength || 0}%</span>
        </div>
      </div>

      {displaySignal?.indicators && Object.keys(displaySignal.indicators).length > 0 && (
        <div className="indicators-section">
          <h4>Indicators</h4>
          <div className="indicators-grid">
            {Object.entries(displaySignal.indicators).map(([key, value]) => {
              // Skip array-type values (used for chart plotting)
              if (Array.isArray(value)) {
                return null;
              }
              return (
                <div key={key} className="indicator-item">
                  <span className="indicator-label">{key.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="indicator-value">
                    {typeof value === 'number' ? value.toFixed(2) : value}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="chart-section">
        <div className="chart-controls">
          {/* Timeframe Dropdown */}
          <div className="timeframe-dropdown-card" ref={dropdownRef}>
            <button
              className="timeframe-dropdown-btn-card"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              disabled={loading || syncing}
            >
              <span>{selectedTimeframe}</span>
              <ChevronDown size={14} className={dropdownOpen ? 'rotated' : ''} />
            </button>
            {dropdownOpen && (
              <div className="timeframe-dropdown-menu-card">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf.value}
                    className={`timeframe-option-card ${selectedTimeframe === tf.value ? 'active' : ''}`}
                    onClick={() => handleTimeframeChange(tf.value)}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Sync Button */}
          <button
            className="chart-sync-btn-card"
            onClick={handleSyncTimeframe}
            disabled={syncing || loading}
            title="Sync data for this timeframe"
          >
            <RefreshCw size={14} className={syncing ? 'spinning' : ''} />
          </button>

          <button
            className="chart-expand-btn"
            onClick={() => setIsModalOpen(true)}
            title="Expand chart to fullscreen"
          >
            <Maximize2 size={16} />
            Expand
          </button>
        </div>

        {loading ? (
          <div className="chart-loading-card">
            <RefreshCw size={24} className="spinning" />
            <span>Loading {selectedTimeframe} data...</span>
          </div>
        ) : chartCandles && chartCandles.length > 0 ? (
          <TradingChartWithIndicators
            data={chartCandles}
            height={300}
            currentSignal={displaySignal?.signal || 'HOLD'}
            strategyName={strategy}
            indicators={displaySignal?.indicators || {}}
            trades={trades}
          />
        ) : (
          <div className="chart-no-data-card">
            <p>No {selectedTimeframe} data available</p>
            <button
              className="btn-sync-card"
              onClick={handleSyncTimeframe}
              disabled={syncing}
            >
              <RefreshCw size={14} className={syncing ? 'spinning' : ''} />
              {syncing ? 'Syncing...' : `Sync ${selectedTimeframe}`}
            </button>
          </div>
        )}
      </div>

      <TradesTable trades={trades} strategy={strategy} />

      <ChartModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        strategy={strategy}
        signal={displaySignal || initialSignal}
        candles={chartCandles || initialCandles}
        symbol={symbol}
        trades={trades}
      />
    </div>
  );
};

export default StrategyCard;
