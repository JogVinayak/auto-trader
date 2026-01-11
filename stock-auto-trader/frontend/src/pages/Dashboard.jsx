import { useState, useEffect } from 'react';
import { RefreshCw, DollarSign, TrendingUp, ChevronDown } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import Sidebar from '../components/Sidebar';
import StrategyCard from '../components/StrategyCard';
import SignalsTable from '../components/SignalsTable';
import ManualTradingCard from '../components/ManualTradingCard';
import SyncModal from '../components/SyncModal';
import { stocksAPI, portfolioAPI, candlesAPI, signalsAPI, tradesAPI } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [stocks, setStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState('AAPL');
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategies, setSelectedStrategies] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [signals, setSignals] = useState([]);
  const [candles, setCandles] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [globalTimeframe, setGlobalTimeframe] = useState('1d');
  const [timeframeDropdownOpen, setTimeframeDropdownOpen] = useState(false);
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState({
    stage: 'fetching',
    message: '',
    progress: 0,
    error: false,
    success: false,
    details: [],
    exchange: null,
    marketState: null,
    isMarketOpen: null,
    syncType: null
  });

  // Fetch initial data
  const fetchInitialData = async () => {
      try {
        setLoading(true);
        console.log('🚀 Fetching initial data...');

        // Fetch strategies
        console.log('📊 Fetching strategies...');
        const strategiesRes = await signalsAPI.getStrategies();
        const stratList = strategiesRes.data.strategies;
        console.log('✅ Strategies loaded:', stratList);
        setStrategies(stratList);
        setSelectedStrategies(stratList.map((s) => s.name));

        // Fetch stocks
        console.log('📈 Fetching stocks...');
        const stocksRes = await stocksAPI.getAll();
        const stockData = stocksRes.data.map((s) => ({
          ...s,
          change: (Math.random() * 4 - 2).toFixed(2), // Mock change for now
        }));
        console.log('✅ Stocks loaded:', stockData);
        setStocks(stockData);

        // Fetch portfolio
        console.log('💰 Fetching portfolio...');
        const portfolioRes = await portfolioAPI.get();
        console.log('✅ Portfolio loaded:', portfolioRes.data);
        setPortfolio(portfolioRes.data);

        console.log('✅ All initial data loaded successfully!');
        setLoading(false);
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setError(`Failed to load data: ${error.message}`);
        setLoading(false);
      }
    };

  useEffect(() => {
    fetchInitialData();
  }, []);

  // Fetch stock data when selected stock changes
  const fetchStockData = async () => {
    if (!selectedStock) return;
      try {
        console.log(`📊 Fetching data for ${selectedStock}...`);

        // Fetch candles
        const candlesRes = await candlesAPI.get(selectedStock, '1d', 100);
        console.log('✅ Candles loaded:', candlesRes.data.length, 'candles');
        setCandles(candlesRes.data);

        // Fetch signals for all strategies
        const signalsRes = await signalsAPI.get(selectedStock, '1d');
        console.log('✅ Signals loaded:', signalsRes.data);
        setSignals(signalsRes.data.signals || []);

        // Fetch trades for this stock
        const tradesRes = await tradesAPI.getAll(selectedStock, 50);
        console.log('✅ Trades loaded:', tradesRes.data.length, 'trades');
        setTrades(tradesRes.data);
      } catch (error) {
        console.error('Error fetching stock data:', error);
        // Check if it's insufficient data error (400)
        if (error.response?.status === 400) {
          console.log('ℹ️ Stock has insufficient data, showing sync button');
        }
        // Don't set global error, just show empty state with sync button
        setSignals([]);
        setCandles([]);
      }
    };

  useEffect(() => {
    fetchStockData();
  }, [selectedStock]);

  const handleSyncCandles = async () => {
    if (!selectedStock) {
      toast.error('No stock selected');
      return;
    }

    try {
      setSyncing(true);
      setSyncModalOpen(true);

      // Stage 1: Fetching Data
      setSyncStatus({
        stage: 'fetching',
        message: `Downloading candles for ${selectedStock}...`,
        progress: 20,
        error: false,
        success: false,
        details: [],
        exchange: null,
        marketState: null,
        isMarketOpen: null,
        syncType: 'delta'
      });

      console.log(`🔄 [SYNC] Starting sync for ${selectedStock}...`);

      // Sync candles from data source
      const syncResponse = await candlesAPI.sync(selectedStock, null, false);
      console.log(`✅ [SYNC] Sync response:`, syncResponse.data);

      // Extract market info
      const exchange = syncResponse.data?.exchange || 'Yahoo Finance';
      const marketState = syncResponse.data?.market_state || 'Unknown';
      const isMarketOpen = syncResponse.data?.is_market_open;
      const syncType = syncResponse.data?.sync_type || 'delta';

      console.log(`📍 [SYNC] Exchange: ${exchange}, Market: ${marketState}, Open: ${isMarketOpen}`);

      // Check if any new candles were added
      const newCandles = syncResponse.data?.results?.reduce((total, r) => total + (r.new_candles || 0), 0) || 0;
      console.log(`📊 [SYNC] New candles synced: ${newCandles}`);

      // Format details for display
      const details = syncResponse.data?.results?.map(r => ({
        timeframe: r.timeframe,
        new_candles: r.new_candles || 0
      })) || [];

      // Stage 2: Calculating Indicators
      setSyncStatus({
        stage: 'calculating',
        message: 'Processing technical indicators...',
        progress: 60,
        error: false,
        success: false,
        details,
        exchange,
        marketState,
        isMarketOpen,
        syncType
      });

      // Refetch candles
      console.log(`📈 [SYNC] Fetching candles for ${selectedStock}...`);
      const candlesRes = await candlesAPI.get(selectedStock, '1d', 100);
      console.log(`✅ [SYNC] Fetched ${candlesRes.data.length} candles`);
      setCandles(candlesRes.data);

      // Refetch signals
      console.log(`🎯 [SYNC] Fetching signals for ${selectedStock}...`);
      const signalsRes = await signalsAPI.get(selectedStock, '1d');
      console.log(`✅ [SYNC] Fetched signals:`, signalsRes.data);
      setSignals(signalsRes.data.signals || []);

      // Stage 3: Complete
      const successMessage = newCandles > 0
        ? `Synced ${newCandles} new candles for ${selectedStock}`
        : `${selectedStock} is up to date`;

      setSyncStatus({
        stage: 'done',
        message: successMessage,
        progress: 100,
        error: false,
        success: true,
        details,
        exchange,
        marketState,
        isMarketOpen,
        syncType
      });

      setSyncing(false);

    } catch (error) {
      console.error('❌ [SYNC] Error syncing candles:', error);
      console.error('❌ [SYNC] Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });

      setSyncing(false);

      // Show error in modal
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to sync data';
      setSyncStatus({
        stage: 'fetching',
        message: errorMsg,
        progress: 0,
        error: true,
        success: false,
        details: []
      });
    }
  };

  const handleToggleStrategy = (strategyName) => {
    setSelectedStrategies((prev) =>
      prev.includes(strategyName)
        ? prev.filter((s) => s !== strategyName)
        : [...prev, strategyName]
    );
  };

  // Callback to refresh signals after strategy settings are saved
  const handleSettingsSaved = async (strategyName) => {
    if (!selectedStock) return;

    try {
      console.log(`🔄 Refreshing signals after ${strategyName} settings saved...`);
      const signalsRes = await signalsAPI.get(selectedStock, '1d');
      console.log('✅ Signals refreshed:', signalsRes.data);
      setSignals(signalsRes.data.signals || []);
    } catch (error) {
      console.error('Error refreshing signals:', error);
    }
  };

  // Callback to refresh stocks list after add/delete
  const handleStocksChange = async () => {
    try {
      console.log('🔄 Refreshing stocks list...');
      const stocksRes = await stocksAPI.getAll();
      const stockData = stocksRes.data.map((s) => ({
        ...s,
        change: (Math.random() * 4 - 2).toFixed(2),
      }));
      console.log('✅ Stocks refreshed:', stockData);
      setStocks(stockData);
    } catch (error) {
      console.error('Error refreshing stocks:', error);
    }
  };

  const filteredSignals = signals.filter((signal) =>
    selectedStrategies.includes(signal.strategy)
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <h2>Error Loading Dashboard</h2>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Reload Page
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'Space Grotesk, sans-serif',
          },
          success: {
            iconTheme: {
              primary: 'var(--accent-green)',
              secondary: 'white',
            },
          },
          error: {
            iconTheme: {
              primary: 'var(--accent-red)',
              secondary: 'white',
            },
          },
        }}
      />
      <SyncModal
        symbol={selectedStock}
        isOpen={syncModalOpen}
        onClose={() => setSyncModalOpen(false)}
        syncStatus={syncStatus}
      />
      <Sidebar
        stocks={stocks}
        selectedStock={selectedStock}
        onSelectStock={setSelectedStock}
        strategies={strategies}
        selectedStrategies={selectedStrategies}
        onToggleStrategy={handleToggleStrategy}
        onSettingsSaved={handleSettingsSaved}
        onStocksChange={handleStocksChange}
      />

      <main className="main-content">
        <div className="main-header">
          <div className="header-left">
            <h1>{selectedStock}</h1>
            {portfolio && (
              <div className="portfolio-info">
                <div className="portfolio-item">
                  <DollarSign size={16} />
                  <span>Cash: ${portfolio.cash_balance.toLocaleString()}</span>
                </div>
                <div className="portfolio-item">
                  <TrendingUp size={16} />
                  <span className={portfolio.pnl >= 0 ? 'positive' : 'negative'}>
                    P&L: ${portfolio.pnl.toLocaleString()} ({portfolio.pnl_percent}%)
                  </span>
                </div>
              </div>
            )}
          </div>
          <div className="header-actions">
            <button
              className="btn btn-secondary"
              onClick={handleSyncCandles}
              disabled={syncing}
            >
              <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
              {syncing ? 'Syncing...' : 'Sync Data'}
            </button>
          </div>
        </div>

        {/* Manual Trading Card */}
        <ManualTradingCard
          selectedStock={selectedStock}
          currentPrice={candles.length > 0 ? candles[candles.length - 1]?.close : null}
          onRefresh={() => {
            fetchStockData();
            fetchInitialData();
          }}
        />

        <div className="strategies-header">
          <h2>STRATEGIES</h2>
          <div className="global-timeframe-dropdown">
            <button
              className="timeframe-dropdown-btn"
              onClick={() => setTimeframeDropdownOpen(!timeframeDropdownOpen)}
            >
              <span>{globalTimeframe}</span>
              <ChevronDown size={14} className={timeframeDropdownOpen ? 'rotated' : ''} />
            </button>
            {timeframeDropdownOpen && (
              <div className="timeframe-dropdown-menu">
                {['1m', '5m', '1h', '1d'].map((tf) => (
                  <button
                    key={tf}
                    className={`timeframe-option ${globalTimeframe === tf ? 'active' : ''}`}
                    onClick={() => { setGlobalTimeframe(tf); setTimeframeDropdownOpen(false); }}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {filteredSignals.length === 0 ? (
          <div className="no-signals">
            <h3>No signals available</h3>
            <p>
              {signals.length === 0
                ? `No data available for ${selectedStock}. Click the "Sync Data" button above to fetch candle data.`
                : 'No strategies selected. Enable strategies from the sidebar.'}
            </p>
            {signals.length === 0 && (
              <button
                className="btn btn-primary"
                onClick={handleSyncCandles}
                disabled={syncing}
              >
                <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
                {syncing ? 'Syncing...' : 'Sync Data Now'}
              </button>
            )}
          </div>
        ) : (
          <>
            <SignalsTable signals={filteredSignals} symbol={selectedStock} />
            <div className="strategy-grid">
              {filteredSignals.map((signal) => (
                <StrategyCard
                  key={signal.strategy}
                  strategy={signal.strategy}
                  signal={signal}
                  candles={candles}
                  trades={trades}
                  symbol={selectedStock}
                  globalTimeframe={globalTimeframe}
                />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
