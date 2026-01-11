import { ChevronDown, Maximize2, Minus, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { candlesAPI, indicatorsAPI, signalsAPI } from '../services/api';
import ChartModal from './ChartModal';
import MTFDashboard from './MTFDashboard';
import './StrategyCard.css';
import TradesTable from './TradesTable';
import TradingChartWithIndicators from './TradingChartWithIndicators';

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '1h', label: '1h' },
  { value: '1d', label: '1d' },
];

const StrategyCard = ({ strategy, signal: initialSignal, candles: initialCandles, trades = [], symbol, globalTimeframe = '1d' }) => {
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
    setSelectedTimeframe(globalTimeframe);
  }, [initialCandles, initialSignal, globalTimeframe]);

  // Sync with global timeframe changes
  useEffect(() => {
    if (globalTimeframe !== selectedTimeframe) {
      setSelectedTimeframe(globalTimeframe);
      if (globalTimeframe !== '1d') {
        fetchCandlesForTimeframe(globalTimeframe);
      } else {
        setChartCandles(initialCandles);
        setChartSignal(initialSignal);
      }
    }
  }, [globalTimeframe]);

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

  // Fetch candles and indicators for selected timeframe
  const fetchCandlesForTimeframe = async (timeframe) => {
    if (!symbol) return;

    try {
      setLoading(true);

      // Use stored indicators API - fetches both candles and pre-calculated indicators
      try {
        const indicatorsRes = await indicatorsAPI.get(symbol, timeframe, strategy, 200);
        const { candles, indicators } = indicatorsRes.data;

        if (candles && candles.length > 0) {
          setChartCandles(candles);

          // Build signal object from stored indicators for this strategy
          const strategyIndicators = indicators?.[strategy] || {};
          if (strategyIndicators.signal && strategyIndicators.signal.length > 0) {
            const lastIdx = strategyIndicators.signal.length - 1;
            const signal = strategyIndicators.signal[lastIdx];
            const strength = strategyIndicators.strength?.[lastIdx] || 50;

            // Build indicators object for chart rendering
            const chartIndicators = {
              timestamps: strategyIndicators.timestamps || [],
            };

            // Get the last candle price
            const lastCandle = candles[candles.length - 1];
            const price = lastCandle?.close;

            // Add strategy-specific indicator data
            if (strategy === 'MACD') {
              chartIndicators.macd_line = strategyIndicators.macd_line || [];
              chartIndicators.signal_line = strategyIndicators.macd_signal || [];
              chartIndicators.histogram_line = strategyIndicators.macd_histogram || [];
              // Add scalar values for display
              chartIndicators.price = price;
              chartIndicators.macd = strategyIndicators.macd_line?.[lastIdx];
              chartIndicators.signal = strategyIndicators.macd_signal?.[lastIdx];
              chartIndicators.histogram = strategyIndicators.macd_histogram?.[lastIdx];
            } else if (strategy === 'RSI') {
              chartIndicators.rsi_line = strategyIndicators.rsi_value || [];
              // Add scalar values for display
              chartIndicators.price = price;
              chartIndicators.rsi = strategyIndicators.rsi_value?.[lastIdx];
            } else if (strategy === 'MA_CROSSOVER') {
              chartIndicators.short_ma_line = strategyIndicators.short_ma || [];
              chartIndicators.long_ma_line = strategyIndicators.long_ma || [];
              // Add scalar values for display
              chartIndicators.price = price;
              chartIndicators.short_ma = strategyIndicators.short_ma?.[lastIdx];
              chartIndicators.long_ma = strategyIndicators.long_ma?.[lastIdx];
            } else if (strategy === 'BOLLINGER') {
              chartIndicators.upper_band_line = strategyIndicators.bb_upper || [];
              chartIndicators.middle_band_line = strategyIndicators.bb_middle || [];
              chartIndicators.lower_band_line = strategyIndicators.bb_lower || [];
              // Add scalar values for display
              chartIndicators.price = price;
              chartIndicators.upper_band = strategyIndicators.bb_upper?.[lastIdx];
              chartIndicators.middle_band = strategyIndicators.bb_middle?.[lastIdx];
              chartIndicators.lower_band = strategyIndicators.bb_lower?.[lastIdx];
              chartIndicators.percent_b = strategyIndicators.bb_percent_b?.[lastIdx];
              // Calculate bandwidth percentage
              const upper = strategyIndicators.bb_upper?.[lastIdx];
              const lower = strategyIndicators.bb_lower?.[lastIdx];
              const middle = strategyIndicators.bb_middle?.[lastIdx];
              if (upper && lower && middle) {
                chartIndicators.bandwidth_pct = ((upper - lower) / middle * 100);
              }
            } else if (strategy === 'MTF_EMA') {
              const emaPeriods = [20, 30, 40, 50, 60, 200, 300];
              chartIndicators.ema_lines = {
                ema_20: strategyIndicators.ema_20 || [],
                ema_30: strategyIndicators.ema_30 || [],
                ema_40: strategyIndicators.ema_40 || [],
                ema_50: strategyIndicators.ema_50 || [],
                ema_60: strategyIndicators.ema_60 || [],
                ema_200: strategyIndicators.ema_200 || [],
                ema_300: strategyIndicators.ema_300 || [],
              };
              // Calculate ema_trends from the stored values (EMA > EMA[2-bars-ago] = bullish)
              chartIndicators.ema_trends = {};
              emaPeriods.forEach(period => {
                const emaKey = `ema_${period}`;
                const emaValues = strategyIndicators[emaKey] || [];
                if (emaValues.length >= 3) {
                  const current = emaValues[emaValues.length - 1];
                  const prev2 = emaValues[emaValues.length - 3];
                  chartIndicators.ema_trends[emaKey] = current > prev2;
                } else {
                  chartIndicators.ema_trends[emaKey] = true; // default bullish
                }
              });
              chartIndicators.bullish_count = strategyIndicators.bullish_count?.[lastIdx];
              chartIndicators.bearish_count = strategyIndicators.bearish_count?.[lastIdx];

              // Fetch full MTF dashboard from signals API (contains all timeframes)
              try {
                const mtfSignalsRes = await signalsAPI.get(symbol, '1d', 'MTF_EMA');
                const mtfSignals = mtfSignalsRes.data.signals || [];
                const mtfSignal = mtfSignals.find(s => s.strategy === 'MTF_EMA');
                if (mtfSignal?.indicators?.trend_dashboard) {
                  chartIndicators.trend_dashboard = mtfSignal.indicators.trend_dashboard;
                  chartIndicators.bullish_count = mtfSignal.indicators.bullish_count;
                  chartIndicators.bearish_count = mtfSignal.indicators.bearish_count;
                  chartIndicators.total_cells = mtfSignal.indicators.total_cells;
                }
              } catch (mtfError) {
                console.log('Could not fetch MTF dashboard:', mtfError.message);
              }
            }

            setChartSignal({
              strategy,
              signal: signal || 'HOLD',
              strength,
              indicators: chartIndicators,
            });
          }
        } else {
          setChartCandles([]);
        }
      } catch (indicatorError) {
        console.log('Stored indicators not available, falling back to candles API:', indicatorError.message);
        // Fallback to regular candles API if stored indicators not available
        const candlesRes = await candlesAPI.get(symbol, timeframe, 200);
        if (candlesRes.data && candlesRes.data.length > 0) {
          setChartCandles(candlesRes.data);
          // Try to get signals the old way as fallback
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
      }
    } catch (error) {
      console.error(`Error fetching ${timeframe} data:`, error);
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
      MTF_EMA: '📶',
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

      {/* MTF_EMA Dashboard */}
      {strategy === 'MTF_EMA' && (displaySignal?.indicators?.trend_dashboard || displaySignal?.indicators?.ema_trends) && (
        <MTFDashboard
          trendDashboard={displaySignal.indicators.trend_dashboard}
          bullishCount={displaySignal.indicators.bullish_count}
          bearishCount={displaySignal.indicators.bearish_count}
          totalCells={displaySignal.indicators.total_cells}
          emaTrends={displaySignal.indicators.ema_trends}
          currentTimeframe={selectedTimeframe}
        />
      )}

      {displaySignal?.indicators && Object.keys(displaySignal.indicators).length > 0 && strategy !== 'MTF_EMA' && (
        <div className="indicators-section">
          <h4>Indicators</h4>
          <div className="indicators-grid">
            {Object.entries(displaySignal.indicators).map(([key, value]) => {
              // Skip array-type and object-type values
              if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
                return null;
              }
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
