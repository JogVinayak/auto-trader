import { useEffect, useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Maximize2, RefreshCw, ChevronDown } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import { candlesAPI, signalsAPI } from '../services/api';
import './ChartModal.css';

const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '1d', label: '1 Day' },
];

const ChartModal = ({ isOpen, onClose, strategy, signal, candles: initialCandles, symbol, trades = [] }) => {
  const [chartHeight, setChartHeight] = useState(0);
  const chartBodyRef = useRef(null);

  // Timeframe state
  const [selectedTimeframe, setSelectedTimeframe] = useState('1d');
  const [chartCandles, setChartCandles] = useState(initialCandles);
  const [chartSignal, setChartSignal] = useState(signal);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Calculate available height for chart
  const calculateChartHeight = useCallback(() => {
    if (chartBodyRef.current) {
      // Get the actual available height of the chart body container
      const bodyRect = chartBodyRef.current.getBoundingClientRect();
      // Subtract padding (20px top + 20px bottom = 40px)
      const availableHeight = bodyRect.height - 40;
      setChartHeight(Math.max(availableHeight, 300)); // Minimum 300px
    }
  }, []);

  // Fetch candles for selected timeframe
  const fetchCandlesForTimeframe = useCallback(async (timeframe) => {
    if (!symbol) return;

    try {
      setLoading(true);
      console.log(`📊 Fetching ${timeframe} candles for ${symbol}...`);

      // Fetch candles for the timeframe
      const candlesRes = await candlesAPI.get(symbol, timeframe, 200);

      if (candlesRes.data && candlesRes.data.length > 0) {
        console.log(`✅ Loaded ${candlesRes.data.length} candles for ${timeframe}`);
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
          console.log('ℹ️ Could not fetch signals for timeframe:', signalError.message);
        }
      } else {
        // No data available, show empty and offer to sync
        console.log(`⚠️ No ${timeframe} data available for ${symbol}`);
        setChartCandles([]);
      }
    } catch (error) {
      console.error(`Error fetching ${timeframe} candles:`, error);
      // If 400 error (insufficient data), show empty state
      if (error.response?.status === 400) {
        setChartCandles([]);
      }
    } finally {
      setLoading(false);
    }
  }, [symbol, strategy]);

  // Sync candles for the selected timeframe
  const handleSyncTimeframe = async () => {
    if (!symbol || syncing) return;

    try {
      setSyncing(true);
      console.log(`🔄 Syncing ${selectedTimeframe} data for ${symbol}...`);

      await candlesAPI.sync(symbol, selectedTimeframe, false);

      // Refetch after sync
      await fetchCandlesForTimeframe(selectedTimeframe);

      console.log(`✅ Sync complete for ${selectedTimeframe}`);
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
      setChartSignal(signal);
    }
  };

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedTimeframe('1d');
      setChartCandles(initialCandles);
      setChartSignal(signal);
    }
  }, [isOpen, initialCandles, signal]);

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

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';

    // Calculate initial height after modal renders
    const timeoutId = setTimeout(calculateChartHeight, 50);

    // Recalculate on window resize
    window.addEventListener('resize', calculateChartHeight);

    return () => {
      document.removeEventListener('keydown', handleEscape);
      window.removeEventListener('resize', calculateChartHeight);
      clearTimeout(timeoutId);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose, calculateChartHeight]);

  if (!isOpen) return null;

  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('chart-modal-overlay')) {
      onClose();
    }
  };

  // Use portal to render modal at document body level (above all other elements)
  return createPortal(
    <div className="chart-modal-overlay" onClick={handleOverlayClick}>
      <div className="chart-modal-content">
        <div className="chart-modal-header">
          <div className="chart-modal-title">
            <Maximize2 size={20} />
            <h2>{symbol} - {strategy.replace('_', ' ')}</h2>
          </div>

          <div className="chart-modal-controls">
            {/* Timeframe Dropdown */}
            <div className="timeframe-dropdown" ref={dropdownRef}>
              <button
                className="timeframe-dropdown-btn"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                disabled={loading || syncing}
              >
                <span>{TIMEFRAMES.find(tf => tf.value === selectedTimeframe)?.label || selectedTimeframe}</span>
                <ChevronDown size={16} className={dropdownOpen ? 'rotated' : ''} />
              </button>
              {dropdownOpen && (
                <div className="timeframe-dropdown-menu">
                  {TIMEFRAMES.map((tf) => (
                    <button
                      key={tf.value}
                      className={`timeframe-option ${selectedTimeframe === tf.value ? 'active' : ''}`}
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
              className="chart-sync-btn"
              onClick={handleSyncTimeframe}
              disabled={syncing || loading}
              title="Sync data for this timeframe"
            >
              <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
            </button>
          </div>

          <div className="chart-modal-info">
            <div className={`signal-badge-modal ${chartSignal.signal.toLowerCase()}`}>
              <span>{chartSignal.signal}</span>
            </div>
            <span className="strength-text-modal">Strength: {chartSignal.strength}%</span>
          </div>
          <button className="chart-modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="chart-modal-body" ref={chartBodyRef}>
          {loading ? (
            <div className="chart-loading">
              <RefreshCw size={32} className="spinning" />
              <span>Loading {selectedTimeframe} data...</span>
            </div>
          ) : chartCandles.length === 0 ? (
            <div className="chart-no-data">
              <p>No {selectedTimeframe} data available for {symbol}</p>
              <button
                className="btn btn-primary"
                onClick={handleSyncTimeframe}
                disabled={syncing}
              >
                <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
                {syncing ? 'Syncing...' : `Sync ${selectedTimeframe} Data`}
              </button>
            </div>
          ) : chartHeight > 0 && (
            <TradingChartWithIndicators
              data={chartCandles}
              height={chartHeight}
              currentSignal={chartSignal.signal}
              strategyName={strategy}
              indicators={chartSignal.indicators}
              trades={trades}
            />
          )}
        </div>

        <div className="chart-modal-footer">
          <div className="chart-modal-details">
            <div className="detail-item">
              <span className="detail-label">Reason:</span>
              <span className="detail-value">{chartSignal.reason}</span>
            </div>
            {chartSignal.indicators && Object.keys(chartSignal.indicators).length > 0 && (
              <div className="detail-item">
                <span className="detail-label">Indicators:</span>
                <div className="indicators-list-modal">
                  {Object.entries(chartSignal.indicators)
                    .filter(([key]) => !key.includes('_line') && !key.includes('timestamps'))
                    .slice(0, 6)
                    .map(([key, value]) => (
                      <div key={key} className="indicator-chip">
                        <span className="indicator-chip-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="indicator-chip-value">
                          {typeof value === 'number' ? value.toFixed(2) : value}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ChartModal;
