import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import './SignalsTable.css';

const SignalsTable = ({ signals, symbol }) => {
  const getSignalIcon = (signal) => {
    switch (signal) {
      case 'BUY':
        return <TrendingUp size={16} className="signal-icon buy" />;
      case 'SELL':
        return <TrendingDown size={16} className="signal-icon sell" />;
      default:
        return <Minus size={16} className="signal-icon hold" />;
    }
  };

  const getSignalClass = (signal) => {
    switch (signal) {
      case 'BUY':
        return 'buy';
      case 'SELL':
        return 'sell';
      default:
        return 'hold';
    }
  };

  if (!signals || signals.length === 0) {
    return (
      <div className="signals-table-empty">
        <p>No signals available</p>
      </div>
    );
  }

  return (
    <div className="signals-table-container">
      <div className="signals-table-header">
        <h3>Current Signals for {symbol}</h3>
        <span className="signals-count">{signals.length} Strategies</span>
      </div>

      <div className="signals-table">
        <table>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Signal</th>
              <th>Strength</th>
              <th>Reason</th>
              <th>Key Indicators</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => (
              <tr key={signal.strategy} className={`signal-row ${getSignalClass(signal.signal)}`}>
                <td className="strategy-cell">
                  <span className="strategy-name">{signal.strategy.replace('_', ' ')}</span>
                </td>
                <td className="signal-cell">
                  <div className={`signal-badge ${getSignalClass(signal.signal)}`}>
                    {getSignalIcon(signal.signal)}
                    <span>{signal.signal}</span>
                  </div>
                </td>
                <td className="strength-cell">
                  <div className="strength-bar-small">
                    <div
                      className={`strength-fill-small ${getSignalClass(signal.signal)}`}
                      style={{ width: `${signal.strength}%` }}
                    ></div>
                  </div>
                  <span className="strength-text">{signal.strength}%</span>
                </td>
                <td className="reason-cell">{signal.reason}</td>
                <td className="indicators-cell">
                  {signal.indicators && (
                    <div className="mini-indicators">
                      {Object.entries(signal.indicators)
                        .filter(([, value]) => typeof value !== 'object' && !Array.isArray(value))
                        .slice(0, 3)
                        .map(([key, value]) => (
                        <div key={key} className="mini-indicator">
                          <span className="mini-indicator-label">{key.replace(/_/g, ' ')}:</span>
                          <span className="mini-indicator-value">
                            {typeof value === 'number' ? value.toFixed(2) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SignalsTable;
