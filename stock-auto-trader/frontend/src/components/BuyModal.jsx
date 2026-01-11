import { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronUp, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import './TradeModal.css';

const API_BASE = 'http://localhost:8000';

const BuyModal = ({ symbol, currentPrice, onClose, onSuccess }) => {
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(currentPrice || 0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fundPercentage, setFundPercentage] = useState(100);
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Data from API
  const [availableFunds, setAvailableFunds] = useState(0);
  const [fees, setFees] = useState(null);
  const [maxQtyInfo, setMaxQtyInfo] = useState(null);
  const [canExecute, setCanExecute] = useState(false);

  // Fetch portfolio and calculate fees
  useEffect(() => {
    fetchPortfolio();
  }, []);

  useEffect(() => {
    if (quantity > 0 && price > 0) {
      calculateFees();
    }
  }, [quantity, price, fundPercentage]);

  const fetchPortfolio = async () => {
    try {
      const res = await axios.get(`${API_BASE}/portfolio`);
      setAvailableFunds(res.data.cash_balance);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
    }
  };

  const calculateFees = async () => {
    try {
      const res = await axios.get(`${API_BASE}/trades/manual/calculate-fees`, {
        params: {
          symbol,
          quantity,
          price,
          trade_type: 'BUY',
          fund_percentage: showAdvanced ? fundPercentage : null
        }
      });
      setFees(res.data.fees);
      setMaxQtyInfo(res.data.max_quantity_info);
      setCanExecute(res.data.can_execute);
    } catch (error) {
      console.error('Error calculating fees:', error);
    }
  };

  const handleFundPercentageClick = (percentage) => {
    setFundPercentage(percentage);
    if (maxQtyInfo && maxQtyInfo.max_quantity > 0) {
      // Calculate qty based on percentage
      const fundsToUse = availableFunds * (percentage / 100);
      const estimatedQty = Math.floor(fundsToUse / price);
      setQuantity(Math.max(1, estimatedQty));
    }
  };

  const handleBuy = async () => {
    setLoading(true);
    const toastId = toast.loading(`Buying ${quantity} shares of ${symbol}...`);

    try {
      const response = await axios.post(`${API_BASE}/trades/manual/buy`, null, {
        params: {
          symbol,
          quantity,
          price
        }
      });

      console.log('✅ Buy order executed:', response.data);
      toast.success(`Bought ${quantity} shares of ${symbol} at ₹${price}`, { id: toastId });

      onSuccess();
      onClose();
    } catch (error) {
      console.error('❌ Error executing buy:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to execute buy order';
      toast.error(errorMsg, { id: toastId, duration: 5000 });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmationClose = () => {
    setShowConfirmation(false);
  };

  const handleConfirm = () => {
    handleBuy();
  };

  if (showConfirmation) {
    return (
      <div className="modal-overlay" onClick={handleConfirmationClose}>
        <div className="modal-content modal-sm" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Confirm Buy Order</h3>
            <button className="close-btn" onClick={handleConfirmationClose}>
              <X size={20} />
            </button>
          </div>

          <div className="modal-body">
            <div className="confirmation-summary">
              <div className="summary-row">
                <span>Symbol:</span>
                <strong>{symbol}</strong>
              </div>
              <div className="summary-row">
                <span>Quantity:</span>
                <strong>{quantity} shares</strong>
              </div>
              <div className="summary-row">
                <span>Price:</span>
                <strong>₹{price.toFixed(2)}</strong>
              </div>
              <div className="summary-row highlight">
                <span>Total Cost:</span>
                <strong>₹{fees?.net_amount.toFixed(2)}</strong>
              </div>
              <div className="summary-row">
                <span>Charges:</span>
                <strong>₹{fees?.total_charges.toFixed(2)}</strong>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={handleConfirmationClose}>
              Cancel
            </button>
            <button
              className="btn btn-buy"
              onClick={handleConfirm}
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Confirm Buy'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Buy {symbol}</h3>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Stock Info */}
          <div className="stock-info-card">
            <div className="stock-info-row">
              <span className="label">Symbol:</span>
              <span className="value">{symbol}</span>
            </div>
            <div className="stock-info-row">
              <span className="label">LTP:</span>
              <span className="value">₹{currentPrice?.toFixed(2)}</span>
            </div>
            <div className="stock-info-row">
              <span className="label">Available Funds:</span>
              <span className="value funds">₹{availableFunds.toFixed(2)}</span>
            </div>
            {maxQtyInfo && (
              <div className="stock-info-row">
                <span className="label">Max Quantity:</span>
                <span className="value success">{maxQtyInfo.max_quantity} shares</span>
              </div>
            )}
          </div>

          {/* Input Fields */}
          <div className="form-group">
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              min="1"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="price">Price per share</label>
            <input
              id="price"
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
              className="form-input"
            />
            <small className="form-hint">Current market price: ₹{currentPrice?.toFixed(2)}</small>
          </div>

          {/* Advanced Options */}
          <div className="advanced-section">
            <button
              className="advanced-toggle"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span>Advanced Options</span>
              {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showAdvanced && (
              <div className="advanced-content">
                <label>Allocate by Fund Percentage</label>
                <div className="percentage-buttons">
                  {[25, 50, 75, 100].map((pct) => (
                    <button
                      key={pct}
                      className={`pct-btn ${fundPercentage === pct ? 'active' : ''}`}
                      onClick={() => handleFundPercentageClick(pct)}
                    >
                      {pct}%
                    </button>
                  ))}
                </div>
                {maxQtyInfo && (
                  <div className="fund-info">
                    <Info size={14} />
                    <span>
                      With {fundPercentage}% (₹{(availableFunds * fundPercentage / 100).toFixed(2)}),
                      you can buy up to {maxQtyInfo.max_quantity} shares
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Fee Breakdown */}
          {fees && (
            <div className="fee-breakdown">
              <h4>Fee Breakdown</h4>
              <div className="fee-row">
                <span>Turnover:</span>
                <span>₹{fees.turnover.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>Brokerage:</span>
                <span>₹{fees.brokerage.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>STT:</span>
                <span>₹{fees.stt.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>Exchange Charges:</span>
                <span>₹{fees.exchange_charges.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>GST:</span>
                <span>₹{fees.gst.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>Stamp Duty:</span>
                <span>₹{fees.stamp_duty.toFixed(2)}</span>
              </div>
              <div className="fee-row total">
                <span>Total Charges:</span>
                <span>₹{fees.total_charges.toFixed(2)}</span>
              </div>
              <div className="fee-row highlight">
                <span>Net Amount:</span>
                <span>₹{fees.net_amount.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>Breakeven Price:</span>
                <span>₹{fees.breakeven_price.toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Warning */}
          {!canExecute && fees && (
            <div className="warning-box">
              Insufficient funds! You need ₹{fees.net_amount.toFixed(2)} but have ₹{availableFunds.toFixed(2)}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-buy"
            onClick={() => setShowConfirmation(true)}
            disabled={!canExecute || loading}
          >
            {loading ? 'Processing...' : 'Place Buy Order'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BuyModal;
