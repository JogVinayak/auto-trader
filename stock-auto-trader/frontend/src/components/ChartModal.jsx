import { useEffect, useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Maximize2, RefreshCw, ChevronDown } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import MTFDashboard from './MTFDashboard';
import { candlesAPI, indicatorsAPI, signalsAPI } from '../services/api';
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

  // Fetch candles and indicators for selected timeframe
  const fetchCandlesForTimeframe = useCallback(async (timeframe) => {
    if (!symbol) return;

    try {
      setLoading(true);
      console.log(`📊 Fetching ${timeframe} data for ${symbol}...`);

      // Use stored indicators API - fetches both candles and pre-calculated indicators
      try {
        const indicatorsRes = await indicatorsAPI.get(symbol, timeframe, strategy, 200);
        const { candles, indicators } = indicatorsRes.data;

        if (candles && candles.length > 0) {
          console.log(`✅ Loaded ${candles.length} candles with stored indicators for ${timeframe}`);
          setChartCandles(candles);

          // Build signal object from stored indicators for this strategy
          const strategyIndicators = indicators?.[strategy] || {};
          if (strategyIndicators.signal && strategyIndicators.signal.length > 0) {
            const lastIdx = strategyIndicators.signal.length - 1;
            const signalValue = strategyIndicators.signal[lastIdx];
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
              signal: signalValue || 'HOLD',
              strength,
              indicators: chartIndicators,
            });
          }
        } else {
          console.log(`⚠️ No ${timeframe} data available for ${symbol}`);
          setChartCandles([]);
        }
      } catch (indicatorError) {
        console.log('Stored indicators not available, falling back to candles API:', indicatorError.message);
        // Fallback to regular candles API if stored indicators not available
        const candlesRes = await candlesAPI.get(symbol, timeframe, 200);
        if (candlesRes.data && candlesRes.data.length > 0) {
          console.log(`✅ Loaded ${candlesRes.data.length} candles for ${timeframe} (fallback)`);
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
            console.log('ℹ️ Could not fetch signals for timeframe:', signalError.message);
          }
        } else {
          console.log(`⚠️ No ${timeframe} data available for ${symbol}`);
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
            <div className={`signal-badge-modal ${(chartSignal?.signal || 'hold').toLowerCase()}`}>
              <span>{chartSignal?.signal || 'HOLD'}</span>
            </div>
            <span className="strength-text-modal">Strength: {chartSignal?.strength || 0}%</span>
          </div>
          <button className="chart-modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="chart-modal-body" ref={chartBodyRef}>
          {/* MTF Dashboard for MTF_EMA strategy - positioned top right, draggable */}
          {strategy === 'MTF_EMA' && (chartSignal?.indicators?.trend_dashboard || chartSignal?.indicators?.bullish_count !== undefined || chartSignal?.indicators?.ema_trends) && (
            <div className="mtf-dashboard-modal-overlay">
              <MTFDashboard
                trendDashboard={chartSignal.indicators.trend_dashboard}
                bullishCount={chartSignal.indicators.bullish_count}
                bearishCount={chartSignal.indicators.bearish_count}
                totalCells={chartSignal.indicators.total_cells}
                emaTrends={chartSignal.indicators.ema_trends}
                currentTimeframe={selectedTimeframe}
                draggable={true}
              />
            </div>
          )}

          {loading ? (
            <div className="chart-loading">
              <RefreshCw size={32} className="spinning" />
              <span>Loading {selectedTimeframe} data...</span>
            </div>
          ) : !chartCandles || chartCandles.length === 0 ? (
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
              currentSignal={chartSignal?.signal || 'HOLD'}
              strategyName={strategy}
              indicators={chartSignal?.indicators || {}}
              trades={trades}
            />
          )}
        </div>

        <div className="chart-modal-footer">
          <div className="chart-modal-details">
            <div className="detail-item">
              <span className="detail-label">Reason:</span>
              <span className="detail-value">{chartSignal?.reason || 'No signal data'}</span>
            </div>
            {chartSignal?.indicators && Object.keys(chartSignal.indicators).length > 0 && (
              <div className="detail-item">
                <span className="detail-label">Indicators:</span>
                <div className="indicators-list-modal">
                  {Object.entries(chartSignal.indicators)
                    .filter(([key, value]) => !key.includes('_line') && !key.includes('timestamps') && typeof value !== 'object')
                    .slice(0, 6)
                    .map(([key, value]) => (
                      <div key={key} className="indicator-chip">
                        <span className="indicator-chip-label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span className="indicator-chip-value">
                          {typeof value === 'number' ? value.toFixed(2) : String(value)}
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
