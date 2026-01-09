import { TrendingUp, TrendingDown, DollarSign, Clock } from 'lucide-react';
import './TradesTable.css';

const TradesTable = ({ trades, strategy = null }) => {
  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getPnLClass = (pnl) => {
    if (pnl > 0) return 'positive';
    if (pnl < 0) return 'negative';
    return 'neutral';
  };

  const filteredTrades = strategy
    ? trades.filter((trade) => trade.strategy === strategy)
    : trades;

  if (!filteredTrades || filteredTrades.length === 0) {
    return (
      <div className="trades-table-empty">
        <Clock size={48} />
        <h3>No trades yet</h3>
        <p>
          {strategy
            ? `No trades executed for ${strategy} strategy`
            : 'No trades have been executed yet. Enable auto-trading to start.'}
        </p>
      </div>
    );
  }

  return (
    <div className="trades-table-container">
      <div className="trades-table-header">
        <h3>{strategy ? `${strategy} Trades` : 'All Trades'}</h3>
        <div className="trades-stats">
          <span className="trades-count">{filteredTrades.length} trades</span>
          <span className="trades-profit">
            Total P&L:{' '}
            <span
              className={getPnLClass(
                filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0)
              )}
            >
              {formatCurrency(
                filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0)
              )}
            </span>
          </span>
        </div>
      </div>

      <div className="trades-table-scroll">
        <table className="trades-table">
          <thead>
            <tr>
              <th>Date/Time</th>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Type</th>
              <th>Quantity</th>
              <th>Entry Price</th>
              <th>Exit Price</th>
              <th>P&L</th>
              <th>P&L %</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrades.map((trade) => (
              <tr key={trade.id} className="trade-row">
                <td className="date-cell">{formatDate(trade.entry_time)}</td>
                <td className="symbol-cell">
                  <span className="symbol-badge">{trade.symbol}</span>
                </td>
                <td className="strategy-cell">{trade.strategy}</td>
                <td className="type-cell">
                  <div className={`trade-type ${trade.trade_type.toLowerCase()}`}>
                    {trade.trade_type === 'BUY' ? (
                      <TrendingUp size={14} />
                    ) : (
                      <TrendingDown size={14} />
                    )}
                    <span>{trade.trade_type}</span>
                  </div>
                </td>
                <td className="quantity-cell">{trade.quantity}</td>
                <td className="price-cell">{formatCurrency(trade.entry_price)}</td>
                <td className="price-cell">
                  {trade.exit_price ? formatCurrency(trade.exit_price) : '-'}
                </td>
                <td className={`pnl-cell ${getPnLClass(trade.pnl)}`}>
                  <div className="pnl-value">
                    {trade.pnl !== null && trade.pnl !== undefined ? (
                      <>
                        <DollarSign size={14} />
                        {formatCurrency(Math.abs(trade.pnl))}
                      </>
                    ) : (
                      '-'
                    )}
                  </div>
                </td>
                <td className={`pnl-cell ${getPnLClass(trade.pnl)}`}>
                  {trade.pnl_percent !== null && trade.pnl_percent !== undefined
                    ? `${trade.pnl_percent > 0 ? '+' : ''}${trade.pnl_percent.toFixed(2)}%`
                    : '-'}
                </td>
                <td className="status-cell">
                  <span className={`status-badge ${trade.status.toLowerCase()}`}>
                    {trade.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradesTable;
