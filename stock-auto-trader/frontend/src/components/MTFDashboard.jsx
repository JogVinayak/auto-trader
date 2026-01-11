import './MTFDashboard.css';

const EMA_PERIODS = [20, 30, 40, 50, 60, 200, 300];

const MTFDashboard = ({ trendDashboard, bullishCount, bearishCount, totalCells }) => {
  if (!trendDashboard || Object.keys(trendDashboard).length === 0) {
    return (
      <div className="mtf-dashboard-empty">
        <p>No multi-timeframe data available</p>
      </div>
    );
  }

  // Use only timeframes that have data
  const availableTimeframes = Object.keys(trendDashboard);
  const bullishRatio = totalCells > 0 ? ((bullishCount / totalCells) * 100).toFixed(1) : 0;

  return (
    <div className="mtf-dashboard">
      <div className="mtf-summary">
        <span className="mtf-label">Trend Consensus:</span>
        <span className={`mtf-ratio ${bullishRatio >= 65 ? 'bullish' : bullishRatio <= 35 ? 'bearish' : 'neutral'}`}>
          {bullishRatio}% Bullish
        </span>
        <span className="mtf-counts">
          ({bullishCount} up / {bearishCount} down)
        </span>
      </div>

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
    </div>
  );
};

export default MTFDashboard;
