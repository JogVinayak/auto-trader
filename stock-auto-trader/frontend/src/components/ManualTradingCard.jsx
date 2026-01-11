import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Maximize2, Minimize2, TrendingUp, TrendingDown } from 'lucide-react';
import BuyModal from './BuyModal';
import SellModal from './SellModal';
import PositionsTable from './PositionsTable';
import './ManualTradingCard.css';

const ManualTradingCard = ({ selectedStock, currentPrice, onRefresh }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [showSellModal, setShowSellModal] = useState(false);
  const [positions, setPositions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setShowBuyModal(true);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'x') {
        e.preventDefault();
        setShowSellModal(true);
      }
      // Escape to close modals
      if (e.key === 'Escape') {
        setShowBuyModal(false);
        setShowSellModal(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch positions
  const fetchPositions = async () => {
    // This will be implemented with API call
    // For now, we'll set empty state
    setPositions([]);
    setSummary({
      total_pnl: 0,
      total_pnl_percent: 0,
      total_invested: 0,
      total_current_value: 0
    });
  };

  useEffect(() => {
    fetchPositions();
  }, [selectedStock]);

  const handleTradeSuccess = () => {
    fetchPositions();
    if (onRefresh) onRefresh();
  };

  // Don't show if no positions (initially)
  // Later we can change this to always show
  const hasPositions = positions.length > 0;

  return (
    <>
      <div className={`manual-trading-card ${isFullScreen ? 'fullscreen' : ''}`}>
        {/* Header */}
        <div className="manual-trading-header">
          <div className="manual-trading-title">
            <h3>Manual Trading {selectedStock && `- ${selectedStock}`}</h3>
            {summary && (
              <div className="header-summary">
                <span className={`pnl ${summary.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                  {summary.total_pnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                  ₹{Math.abs(summary.total_pnl).toFixed(2)} ({summary.total_pnl_percent.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>

          <div className="manual-trading-actions">
            {currentPrice && (
              <span className="current-price">
                LTP: ₹{currentPrice.toFixed(2)}
              </span>
            )}

            <button
              className="btn btn-buy"
              onClick={() => setShowBuyModal(true)}
              title="Buy (Cmd+B)"
            >
              Buy
            </button>

            <button
              className="btn btn-sell"
              onClick={() => setShowSellModal(true)}
              title="Sell (Cmd+X)"
            >
              Sell
            </button>

            <button
              className="btn-icon"
              onClick={() => setIsFullScreen(!isFullScreen)}
              title={isFullScreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>

            <button
              className="btn-icon"
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>
          </div>
        </div>

        {/* Collapsible Content */}
        {isExpanded && (
          <div className="manual-trading-content">
            <PositionsTable
              selectedStock={selectedStock}
              positions={positions}
              summary={summary}
              onRefresh={fetchPositions}
            />
          </div>
        )}
      </div>

      {/* Modals */}
      {showBuyModal && (
        <BuyModal
          symbol={selectedStock}
          currentPrice={currentPrice}
          onClose={() => setShowBuyModal(false)}
          onSuccess={handleTradeSuccess}
        />
      )}

      {showSellModal && (
        <SellModal
          symbol={selectedStock}
          currentPrice={currentPrice}
          onClose={() => setShowSellModal(false)}
          onSuccess={handleTradeSuccess}
        />
      )}
    </>
  );
};

export default ManualTradingCard;
