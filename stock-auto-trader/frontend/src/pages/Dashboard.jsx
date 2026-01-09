import { useState, useEffect } from 'react';
import { RefreshCw, DollarSign, TrendingUp } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import StrategyCard from '../components/StrategyCard';
import SignalsTable from '../components/SignalsTable';
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

  // Fetch initial data
  useEffect(() => {
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

    fetchInitialData();
  }, []);

  // Fetch stock data when selected stock changes
  useEffect(() => {
    if (!selectedStock) return;

    const fetchStockData = async () => {
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

    fetchStockData();
  }, [selectedStock]);

  const handleSyncCandles = async () => {
    if (!selectedStock) return;

    try {
      setSyncing(true);
      await candlesAPI.sync(selectedStock, null, false);

      // Refetch candles and signals
      const candlesRes = await candlesAPI.get(selectedStock, '1d', 100);
      setCandles(candlesRes.data);

      const signalsRes = await signalsAPI.get(selectedStock, '1d');
      setSignals(signalsRes.data.signals || []);

      setSyncing(false);
    } catch (error) {
      console.error('Error syncing candles:', error);
      setSyncing(false);
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
      <Sidebar
        stocks={stocks}
        selectedStock={selectedStock}
        onSelectStock={setSelectedStock}
        strategies={strategies}
        selectedStrategies={selectedStrategies}
        onToggleStrategy={handleToggleStrategy}
        onSettingsSaved={handleSettingsSaved}
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
