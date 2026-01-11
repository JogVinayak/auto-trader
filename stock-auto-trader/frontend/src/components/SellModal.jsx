import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import './TradeModal.css';

const API_BASE = 'http://localhost:8000';

const SellModal = ({ symbol, currentPrice, onClose, onSuccess }) => {
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(currentPrice || 0);
  const [loading, setLoading] = useState(false);
  const [holdingQty, setHoldingQty] = useState(0);
  const [fees, setFees] = useState(null);
  const [canExecute, setCanExecute] = useState(false);

  useEffect(() => {
    fetchHolding();
  }, [symbol]);

  useEffect(() => {
    if (quantity > 0 && price > 0) {
      calculateFees();
    }
  }, [quantity, price]);

  const fetchHolding = async () => {
    try {
      const res = await axios.get(`${API_BASE}/trades/manual/calculate-fees`, {
        params: {
          symbol,
          quantity: 1,
          price: currentPrice || 100,
          trade_type: 'SELL'
        }
      });
      setHoldingQty(res.data.holding_quantity || 0);
    } catch (error) {
      console.error('Error fetching holding:', error);
    }
  };

  const calculateFees = async () => {
    try {
      const res = await axios.get(`${API_BASE}/trades/manual/calculate-fees`, {
        params: {
          symbol,
          quantity,
          price,
          trade_type: 'SELL'
        }
      });
      setFees(res.data.fees);
      setCanExecute(res.data.can_execute);
    } catch (error) {
      console.error('Error calculating fees:', error);
    }
  };

  const handleSell = async () => {
    setLoading(true);
    const toastId = toast.loading(`Selling ${quantity} shares of ${symbol}...`);

    try {
      const response = await axios.post(`${API_BASE}/trades/manual/sell`, null, {
        params: {
          symbol,
          quantity,
          price
        }
      });

      console.log('✅ Sell order executed:', response.data);
      toast.success(`Sold ${quantity} shares of ${symbol} at ₹${price}`, { id: toastId });

      onSuccess();
      onClose();
    } catch (error) {
      console.error('❌ Error executing sell:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to execute sell order';
      toast.error(errorMsg, { id: toastId, duration: 5000 });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Sell {symbol}</h3>
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
              <span className="label">Holdings:</span>
              <span className="value success">{holdingQty} shares</span>
            </div>
          </div>

          {/* Input Fields */}
          <div className="form-group">
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              min="1"
              max={holdingQty}
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              className="form-input"
            />
            <small className="form-hint">Maximum: {holdingQty} shares</small>
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

          {/* Fee Breakdown */}
          {fees && (
            <div className="fee-breakdown">
              <h4>Fee Breakdown</h4>
              <div className="fee-row">
                <span>Turnover:</span>
                <span>₹{fees.turnover.toFixed(2)}</span>
              </div>
              <div className="fee-row">
                <span>Total Charges:</span>
                <span>₹{fees.total_charges.toFixed(2)}</span>
              </div>
              <div className="fee-row highlight">
                <span>Net Amount (You'll Receive):</span>
                <span>₹{fees.net_amount.toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Warning */}
          {!canExecute && (
            <div className="warning-box">
              Insufficient shares! You have {holdingQty} shares but trying to sell {quantity}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-sell"
            onClick={handleSell}
            disabled={!canExecute || loading || holdingQty === 0}
          >
            {loading ? 'Processing...' : 'Place Sell Order'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SellModal;
