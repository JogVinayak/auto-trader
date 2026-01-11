import { useState, useRef, useEffect, useCallback } from 'react';
import { GripHorizontal } from 'lucide-react';
import './MTFDashboard.css';

const EMA_PERIODS = [20, 30, 40, 50, 60, 200, 300];

const MTFDashboard = ({
  trendDashboard,
  bullishCount,
  bearishCount,
  totalCells,
  draggable = false,
  initialPosition = null,
  emaTrends = null,  // For single-timeframe view: { ema_20: true/false, ema_30: true/false, ... }
  currentTimeframe = null  // Current timeframe label for single-TF view
}) => {
  const [position, setPosition] = useState(initialPosition || { x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef(null);
  const startPosRef = useRef({ x: 0, y: 0 });
  const startMouseRef = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e) => {
    if (!draggable) return;
    e.preventDefault();
    setIsDragging(true);
    startPosRef.current = { ...position };
    startMouseRef.current = { x: e.clientX, y: e.clientY };
  }, [draggable, position]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const dx = e.clientX - startMouseRef.current.x;
    const dy = e.clientY - startMouseRef.current.y;
    setPosition({
      x: startPosRef.current.x + dx,
      y: startPosRef.current.y + dy,
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // If no trendDashboard but we have bullish/bearish counts, show a simplified view
  const hasTrendData = trendDashboard && Object.keys(trendDashboard).length > 0;
  const hasCountData = bullishCount !== undefined || bearishCount !== undefined;
  const hasEmaTrends = emaTrends && Object.keys(emaTrends).length > 0;

  if (!hasTrendData && !hasCountData && !hasEmaTrends) {
    return (
      <div className="mtf-dashboard-empty">
        <p>No multi-timeframe data available</p>
      </div>
    );
  }

  // Calculate ratio from counts or from emaTrends
  let total = (bullishCount || 0) + (bearishCount || 0);
  let actualBullishCount = bullishCount || 0;
  let actualBearishCount = bearishCount || 0;

  // If we have emaTrends but no counts, calculate from emaTrends
  if (hasEmaTrends && total === 0) {
    Object.values(emaTrends).forEach(isUp => {
      if (isUp) actualBullishCount++;
      else actualBearishCount++;
    });
    total = actualBullishCount + actualBearishCount;
  }

  const bullishRatio = total > 0 ? ((actualBullishCount / total) * 100).toFixed(1) : 0;

  // Use only timeframes that have data
  const availableTimeframes = hasTrendData ? Object.keys(trendDashboard) : [];

  const dashboardStyle = draggable ? {
    transform: `translate(${position.x}px, ${position.y}px)`,
    cursor: isDragging ? 'grabbing' : 'default',
  } : {};

  return (
    <div
      className={`mtf-dashboard ${draggable ? 'draggable' : ''} ${isDragging ? 'dragging' : ''}`}
      style={dashboardStyle}
      ref={dragRef}
    >
      {draggable && (
        <div
          className="mtf-drag-handle"
          onMouseDown={handleMouseDown}
        >
          <GripHorizontal size={16} />
        </div>
      )}

      <div className="mtf-summary">
        <span className="mtf-label">Trend Consensus{currentTimeframe ? ` (${currentTimeframe})` : ''}:</span>
        <span className={`mtf-ratio ${bullishRatio >= 65 ? 'bullish' : bullishRatio <= 35 ? 'bearish' : 'neutral'}`}>
          {bullishRatio}% Bullish
        </span>
        <span className="mtf-counts">
          ({actualBullishCount} up / {actualBearishCount} down)
        </span>
      </div>

      {/* Full multi-timeframe table */}
      {hasTrendData && (
        <div className="mtf-table-wrapper">
          <table className="mtf-table">
            <thead>
              <tr>
                <th className="mtf-corner"></th>
                {availableTimeframes.map(tf => (
                  <th key={tf} className="mtf-tf-header">{tf}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {EMA_PERIODS.map(period => (
                <tr key={period}>
                  <td className="mtf-ema-label">EMA {period}</td>
                  {availableTimeframes.map(tf => {
                    const tfData = trendDashboard[tf];
                    const trend = tfData ? tfData[`EMA_${period}`] : null;
                    const isUp = trend === 'up';
                    const isEmpty = !trend;

                    return (
                      <td
                        key={`${period}-${tf}`}
                        className={`mtf-cell ${isEmpty ? 'empty' : isUp ? 'bullish' : 'bearish'}`}
                      >
                        {isEmpty ? '-' : isUp ? '▲' : '▼'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Single timeframe EMA trends (when full dashboard not available) */}
      {!hasTrendData && hasEmaTrends && (
        <div className="mtf-table-wrapper">
          <table className="mtf-table">
            <thead>
              <tr>
                <th className="mtf-corner"></th>
                <th className="mtf-tf-header">{currentTimeframe || 'Current'}</th>
              </tr>
            </thead>
            <tbody>
              {EMA_PERIODS.map(period => {
                const emaKey = `ema_${period}`;
                const isUp = emaTrends[emaKey];
                const isEmpty = isUp === undefined || isUp === null;

                return (
                  <tr key={period}>
                    <td className="mtf-ema-label">EMA {period}</td>
                    <td className={`mtf-cell ${isEmpty ? 'empty' : isUp ? 'bullish' : 'bearish'}`}>
                      {isEmpty ? '-' : isUp ? '▲' : '▼'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MTFDashboard;
