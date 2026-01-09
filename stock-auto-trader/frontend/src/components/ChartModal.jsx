import { useEffect, useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Maximize2 } from 'lucide-react';
import TradingChartWithIndicators from './TradingChartWithIndicators';
import './ChartModal.css';

const ChartModal = ({ isOpen, onClose, strategy, signal, candles, symbol, trades = [] }) => {
  const [chartHeight, setChartHeight] = useState(0);
  const chartBodyRef = useRef(null);

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
          <div className="chart-modal-info">
            <div className={`signal-badge-modal ${signal.signal.toLowerCase()}`}>
              <span>{signal.signal}</span>
            </div>
            <span className="strength-text-modal">Strength: {signal.strength}%</span>
          </div>
          <button className="chart-modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="chart-modal-body" ref={chartBodyRef}>
          {chartHeight > 0 && (
            <TradingChartWithIndicators
              data={candles}
              height={chartHeight}
              currentSignal={signal.signal}
              strategyName={strategy}
              indicators={signal.indicators}
              trades={trades}
            />
          )}
        </div>

        <div className="chart-modal-footer">
          <div className="chart-modal-details">
            <div className="detail-item">
              <span className="detail-label">Reason:</span>
              <span className="detail-value">{signal.reason}</span>
            </div>
            {signal.indicators && Object.keys(signal.indicators).length > 0 && (
              <div className="detail-item">
                <span className="detail-label">Indicators:</span>
                <div className="indicators-list-modal">
                  {Object.entries(signal.indicators)
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
