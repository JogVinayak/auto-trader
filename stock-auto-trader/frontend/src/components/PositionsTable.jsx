import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, ChevronDown } from 'lucide-react';
import axios from 'axios';
import './PositionsTable.css';

const API_BASE = 'http://localhost:8000';

const PositionsTable = ({ selectedStock, positions: propsPositions, summary: propsSummary, onRefresh }) => {
  const [activeTab, setActiveTab] = useState('positions'); // 'positions' or 'history'
  const [positions, setPositions] = useState([]);
  const [history, setHistory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchData();
  }, [selectedStock, activeTab, limit, offset]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'positions') {
        const res = await axios.get(`${API_BASE}/trades/manual/positions`, {
          params: { symbol: selectedStock, limit, offset }
        });
        setPositions(res.data.positions);
        setSummary(res.data.summary);
        setTotalCount(res.data.pagination.total);
      } else {
        const res = await axios.get(`${API_BASE}/trades/manual/history`, {
          params: { symbol: selectedStock, limit, offset }
        });
        setHistory(res.data.trades);
        setTotalCount(res.data.pagination.total);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = () => {
    setOffset(offset + limit);
  };

  const handleRefresh = () => {
    setOffset(0);
    fetchData();
    if (onRefresh) onRefresh();
  };

  return (
    <div className="positions-table-container">
      {/* Tabs */}
      <div className="positions-tabs">
        <button
          className={`tab ${activeTab === 'positions' ? 'active' : ''}`}
          onClick={() => { setActiveTab('positions'); setOffset(0); }}
        >
          Open Positions {summary && `(${summary.total_positions})`}
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => { setActiveTab('history'); setOffset(0); }}
        >
          Trade History
        </button>
        <button className="refresh-btn" onClick={handleRefresh} title="Refresh">
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {/* Summary Card (only for positions tab) */}
      {activeTab === 'positions' && summary && (
        <div className="summary-card">
          <div className="summary-item">
            <span className="summary-label">Total Invested</span>
            <span className="summary-value">₹{summary.total_invested.toFixed(2)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Current Value</span>
            <span className="summary-value">₹{summary.total_current_value.toFixed(2)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Total P&L</span>
            <span className={`summary-value ${summary.total_pnl >= 0 ? 'positive' : 'negative'}`}>
              {summary.total_pnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              ₹{Math.abs(summary.total_pnl).toFixed(2)} ({summary.total_pnl_percent.toFixed(2)}%)
            </span>
          </div>
        </div>
      )}

      {/* Table */}
      {loading && offset === 0 ? (
        <div className="loading-state">Loading...</div>
      ) : (
        <>
          {activeTab === 'positions' ? (
            <div className="table-wrapper">
              {positions.length === 0 ? (
                <div className="empty-state">
                  <p>No open positions</p>
                  <small>Buy some stocks to see them here</small>
                </div>
              ) : (
                <table className="positions-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Qty</th>
                      <th>Avg Price</th>
                      <th>LTP</th>
                      <th>Invested</th>
                      <th>Current</th>
                      <th>P&L</th>
                      <th>P&L %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos, idx) => (
                      <tr key={idx}>
                        <td className="symbol-cell">{pos.symbol}</td>
                        <td>{pos.quantity}</td>
                        <td>₹{pos.avg_buy_price.toFixed(2)}</td>
                        <td>₹{pos.current_price.toFixed(2)}</td>
                        <td>₹{pos.invested.toFixed(2)}</td>
                        <td>₹{pos.current_value.toFixed(2)}</td>
                        <td className={pos.pnl >= 0 ? 'positive' : 'negative'}>
                          ₹{pos.pnl.toFixed(2)}
                        </td>
                        <td className={pos.pnl_percent >= 0 ? 'positive' : 'negative'}>
                          {pos.pnl_percent.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            <div className="table-wrapper">
              {history.length === 0 ? (
                <div className="empty-state">
                  <p>No trade history</p>
                  <small>Your manual trades will appear here</small>
                </div>
              ) : (
                <table className="positions-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((trade) => (
                      <tr key={trade.id}>
                        <td>{new Date(trade.timestamp).toLocaleDateString()}</td>
                        <td className="symbol-cell">{trade.symbol}</td>
                        <td>
                          <span className={`trade-type ${trade.type.toLowerCase()}`}>
                            {trade.type}
                          </span>
                        </td>
                        <td>{trade.quantity}</td>
                        <td>₹{trade.price.toFixed(2)}</td>
                        <td>₹{trade.total_value.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Load More */}
          {totalCount > (offset + limit) && (
            <div className="load-more-section">
              <button className="btn-load-more" onClick={handleLoadMore} disabled={loading}>
                {loading ? 'Loading...' : `Load 10 More (${totalCount - offset - limit} remaining)`}
              </button>
              <div className="limit-selector">
                Show:
                <select value={limit} onChange={(e) => { setLimit(parseInt(e.target.value)); setOffset(0); }}>
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PositionsTable;
