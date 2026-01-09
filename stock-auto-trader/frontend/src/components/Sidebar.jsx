import { useState } from 'react';
import { Search, TrendingUp, Settings } from 'lucide-react';
import StrategySettingsModal from './StrategySettingsModal';
import './Sidebar.css';

const Sidebar = ({ stocks, selectedStock, onSelectStock, strategies, selectedStrategies, onToggleStrategy }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedStrategyForSettings, setSelectedStrategyForSettings] = useState(null);

  const filteredStocks = stocks.filter((stock) =>
    stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleOpenSettings = (e, strategy) => {
    e.stopPropagation();
    setSelectedStrategyForSettings(strategy);
    setSettingsOpen(true);
  };

  const handleSaveSettings = (strategyName, settings) => {
    console.log(`Saving settings for ${strategyName}:`, settings);
    // TODO: Save settings to backend/local storage
    // You can add an API call here to save strategy settings
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
                <div className="no-stocks">No stocks found</div>
              ) : (
                filteredStocks.map((stock) => (
                  <div
                    key={stock.symbol}
                    className={`stock-item ${selectedStock === stock.symbol ? 'selected' : ''}`}
                    onClick={() => onSelectStock(stock.symbol)}
                  >
                    <span className="stock-symbol">{stock.symbol}</span>
                    <span className={`stock-change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
                      {stock.change >= 0 ? '+' : ''}
                      {stock.change}%
                    </span>
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
