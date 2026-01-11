import { useState } from 'react';
import { Search, TrendingUp, Settings, Plus, Trash2, Loader2 } from 'lucide-react';
import StrategySettingsModal from './StrategySettingsModal';
import { stocksAPI } from '../services/api';
import './Sidebar.css';

const Sidebar = ({ stocks, selectedStock, onSelectStock, strategies, selectedStrategies, onToggleStrategy, onSettingsSaved, onStocksChange }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedStrategyForSettings, setSelectedStrategyForSettings] = useState(null);
  const [addingStock, setAddingStock] = useState(false);
  const [deletingStock, setDeletingStock] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);

  const filteredStocks = stocks.filter((stock) =>
    stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddStock = async () => {
    if (!searchTerm.trim()) return;

    const symbol = searchTerm.trim().toUpperCase();

    // Check if already exists
    if (stocks.some(s => s.symbol === symbol)) {
      alert(`${symbol} is already in your list`);
      return;
    }

    try {
      setAddingStock(true);
      const response = await stocksAPI.add(symbol);
      console.log('Stock added:', response.data);

      // Notify parent to refresh stocks list
      if (onStocksChange) {
        onStocksChange();
      }

      // Select the new stock
      onSelectStock(symbol);
      setSearchTerm('');
    } catch (error) {
      console.error('Error adding stock:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to add stock. Please check the symbol.';
      alert(errorMsg);
    } finally {
      setAddingStock(false);
    }
  };

  const handleDeleteStock = async (symbol) => {
    try {
      setDeletingStock(symbol);
      const response = await stocksAPI.delete(symbol);
      console.log('Stock deleted:', response.data);

      // Notify parent to refresh stocks list
      if (onStocksChange) {
        onStocksChange();
      }

      // If deleted stock was selected, select first available stock
      if (selectedStock === symbol) {
        const remainingStocks = stocks.filter(s => s.symbol !== symbol);
        if (remainingStocks.length > 0) {
          onSelectStock(remainingStocks[0].symbol);
        }
      }

      setShowDeleteConfirm(null);
    } catch (error) {
      console.error('Error deleting stock:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to delete stock';
      alert(errorMsg);
    } finally {
      setDeletingStock(null);
    }
  };

  const handleOpenSettings = (e, strategy) => {
    e.stopPropagation();
    setSelectedStrategyForSettings(strategy);
    setSettingsOpen(true);
  };

  const handleSaveSettings = (strategyName, settings) => {
    console.log(`Settings saved for ${strategyName}:`, settings);
    // Notify parent to refresh signals with new settings
    if (onSettingsSaved) {
      onSettingsSaved(strategyName);
    }
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <TrendingUp size={24} />
          </div>
          {!collapsed && <span className="logo-text">Stock Trader</span>}
        </div>
        <button
          className="toggle-btn"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '→' : '←'}
        </button>
      </div>

      {!collapsed && (
        <>
          <div className="mode-badge">
            <div className="mode-dot"></div>
            <span>Paper Trading Mode</span>
          </div>

          <div className="sidebar-section">
            <span className="section-label">Select Stock</span>
            <div className="stock-search">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search stocks..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="stock-list">
              {filteredStocks.length === 0 ? (
                <div className="no-stocks-container">
                  <div className="no-stocks">No stocks found</div>
                  {searchTerm.trim() && (
                    <button
                      className="add-stock-btn"
                      onClick={handleAddStock}
                      disabled={addingStock}
                    >
                      {addingStock ? (
                        <>
                          <Loader2 size={16} className="spinning" />
                          Adding {searchTerm.toUpperCase()}...
                        </>
                      ) : (
                        <>
                          <Plus size={16} />
                          Add "{searchTerm.toUpperCase()}"
                        </>
                      )}
                    </button>
                  )}
                </div>
              ) : (
                filteredStocks.map((stock) => (
                  <div
                    key={stock.symbol}
                    className={`stock-item ${selectedStock === stock.symbol ? 'selected' : ''}`}
                    onClick={() => onSelectStock(stock.symbol)}
                  >
                    <span className="stock-symbol">{stock.symbol}</span>
                    <div className="stock-actions">
                      <span className={`stock-change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
                        {stock.change >= 0 ? '+' : ''}
                        {stock.change}%
                      </span>
                      {showDeleteConfirm === stock.symbol ? (
                        <div className="delete-confirm">
                          <button
                            className="confirm-delete-btn"
                            onClick={(e) => { e.stopPropagation(); handleDeleteStock(stock.symbol); }}
                            disabled={deletingStock === stock.symbol}
                          >
                            {deletingStock === stock.symbol ? <Loader2 size={12} className="spinning" /> : 'Yes'}
                          </button>
                          <button
                            className="cancel-delete-btn"
                            onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(null); }}
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          className="delete-stock-btn"
                          onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(stock.symbol); }}
                          title="Delete stock"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="sidebar-section">
            <span className="section-label">Display Strategies</span>
            <div className="strategy-filter">
              {strategies.map((strategy) => (
                <div key={strategy.name} className="strategy-row">
                  <label className="strategy-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedStrategies.includes(strategy.name)}
                      onChange={() => onToggleStrategy(strategy.name)}
                    />
                    <span className="checkmark"></span>
                    <span>{strategy.name}</span>
                  </label>
                  <button
                    className="strategy-settings-btn"
                    onClick={(e) => handleOpenSettings(e, strategy)}
                    title="Configure strategy settings"
                  >
                    <Settings size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="shortcut-hint">
            <strong>Shortcuts:</strong>
            <br />
            <kbd>/</kbd> Search &nbsp; <kbd>B</kbd> Buy &nbsp; <kbd>X</kbd> Sell
            <br />
            <kbd>1-4</kbd> Toggle Strategy &nbsp; <kbd>Esc</kbd> Close
          </div>
        </>
      )}

      <StrategySettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        strategy={selectedStrategyForSettings}
        onSave={handleSaveSettings}
      />
    </aside>
  );
};

export default Sidebar;
