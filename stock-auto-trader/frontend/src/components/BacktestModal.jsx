import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, PlayCircle, Calendar, Clock, DollarSign, TrendingUp, TrendingDown, Activity, Maximize2, Minimize2 } from 'lucide-react';
import BacktestChart from './BacktestChart';
import './BacktestModal.css';

const BacktestModal = ({ isOpen, onClose, symbol, strategies }) => {
  const [config, setConfig] = useState({
    strategy: strategies[0]?.name || 'MACD',
    timeframe: '1d',
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    initialCapital: 10000,
    positionSize: 1.0
  });

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [dataAvailability, setDataAvailability] = useState(null);
  const [error, setError] = useState(null);
  const [loadingData, setLoadingData] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [strategyParams, setStrategyParams] = useState({
    // MACD
    fast_period: 12,
    slow_period: 26,
    signal_period: 9,
    // RSI
    rsi_period: 14,
    oversold: 30,
    overbought: 70,
    // RSI_W_PATTERN
    oversold_threshold: 30,
    overbought_threshold: 70,
    min_distance: 3,
    max_distance: 10,
    rsi_tolerance: 5,
    // MA_CROSSOVER
    short_period: 20,
    long_period: 50,
    use_ema: true,
    // BOLLINGER
    period: 20,
    std_dev: 2.0
  });

  useEffect(() => {
    if (isOpen && symbol) {
      fetchDataAvailability();
    }
  }, [isOpen, symbol]);

  const fetchDataAvailability = async () => {
    try {
      const response = await fetch(`http://localhost:8000/backtest/data-availability?symbol=${symbol}`);
      const data = await response.json();
      setDataAvailability(data);

      // Set default dates based on availability if data exists
      if (data.available && data.timeframes[config.timeframe]) {
        const tf = data.timeframes[config.timeframe];
        // Use the full available range, or a sensible default
        const endDate = tf.end_date;
        // Calculate a good start date (1 year back for daily, or use available start)
        const end = new Date(endDate);
        const start = new Date(end);
        start.setFullYear(start.getFullYear() - 1); // 1 year back

        const startDate = start < new Date(tf.start_date) ? tf.start_date : start.toISOString().split('T')[0];

        setConfig(prev => ({
          ...prev,
          startDate: startDate,
          endDate: endDate
        }));
      }
    } catch (err) {
      console.error('Failed to fetch data availability:', err);
    }
  };

  const loadHistoricalData = async () => {
    const TIMEOUT_SECONDS = 30;
    setLoadingData(true);
    setError(null);
    setCountdown(TIMEOUT_SECONDS);

    // Start countdown timer
    const countdownInterval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Set timeout to auto-enable everything after 30 seconds
    const timeoutId = setTimeout(() => {
      setLoadingData(false);
      setLoadingMessage('');
      setCountdown(0);
      setError('Data loading timed out after 30 seconds. You can try again or continue with existing data.');
      clearInterval(countdownInterval);
    }, TIMEOUT_SECONDS * 1000);

    try {
      setLoadingMessage(`Fetching historical data from Yahoo Finance for ${symbol}...`);

      const response = await fetch(
        `http://localhost:8000/backtest/load-data?` + new URLSearchParams({
          symbol,
          timeframe: config.timeframe,
          period: '2y'
        }),
        { method: 'POST' }
      );

      // Clear timeout if request completes
      clearTimeout(timeoutId);
      clearInterval(countdownInterval);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load data');
      }

      const data = await response.json();
      setLoadingMessage(
        `✅ Loaded ${data.total_candles} candles (${data.candles_added} new, ${data.candles_updated} updated)`
      );

      // Wait a moment to show the message
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Refresh data availability
      await fetchDataAvailability();

      setLoadingMessage('');
      setCountdown(0);
      return true;
    } catch (err) {
      clearTimeout(timeoutId);
      clearInterval(countdownInterval);
      setError(`Failed to load data: ${err.message}`);
      setLoadingMessage('');
      setCountdown(0);
      return false;
    } finally {
      setLoadingData(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);

    try {
      // Build strategy parameters based on selected strategy
      const params = {};
      if (config.strategy === 'MACD') {
        params.fast_period = strategyParams.fast_period;
        params.slow_period = strategyParams.slow_period;
        params.signal_period = strategyParams.signal_period;
      } else if (config.strategy === 'RSI') {
        params.period = strategyParams.rsi_period;
        params.oversold = strategyParams.oversold;
        params.overbought = strategyParams.overbought;
      } else if (config.strategy === 'RSI_W_PATTERN') {
        params.rsi_period = strategyParams.rsi_period;
        params.oversold_threshold = strategyParams.oversold_threshold;
        params.overbought_threshold = strategyParams.overbought_threshold;
        params.min_distance = strategyParams.min_distance;
        params.max_distance = strategyParams.max_distance;
        params.rsi_tolerance = strategyParams.rsi_tolerance;
      } else if (config.strategy === 'MA_CROSSOVER') {
        params.short_period = strategyParams.short_period;
        params.long_period = strategyParams.long_period;
        params.use_ema = strategyParams.use_ema;
      } else if (config.strategy === 'BOLLINGER') {
        params.period = strategyParams.period;
        params.std_dev = strategyParams.std_dev;
      }

      // First attempt to run backtest
      const queryParams = {
        symbol,
        strategy: config.strategy,
        timeframe: config.timeframe,
        start_date: config.startDate,
        end_date: config.endDate,
        initial_capital: config.initialCapital,
        position_size: config.positionSize
      };

      // Add strategy params if we're in advanced mode
      if (showAdvanced && Object.keys(params).length > 0) {
        queryParams.strategy_params = JSON.stringify(params);
      }

      const response = await fetch(
        `http://localhost:8000/backtest/run?` + new URLSearchParams(queryParams),
        { method: 'POST' }
      );

      if (!response.ok) {
        const errorData = await response.json();

        // Check if error is due to insufficient data
        if (errorData.detail && errorData.detail.includes('Insufficient historical data')) {
          setError('Insufficient data detected. Loading historical data from Yahoo Finance...');

          // Try to load data
          const loaded = await loadHistoricalData();

          if (loaded) {
            setError('Data loaded successfully. Running backtest...');
            // Retry the backtest
            return await handleRun();
          } else {
            return; // Error already set by loadHistoricalData
          }
        }

        throw new Error(errorData.detail || 'Backtest failed');
      }

      const data = await response.json();
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Backtest failed:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleTimeframeChange = (newTimeframe) => {
    setConfig(prev => ({ ...prev, timeframe: newTimeframe }));

    // Update date range based on new timeframe availability
    if (dataAvailability?.timeframes[newTimeframe]) {
      const tf = dataAvailability.timeframes[newTimeframe];
      setConfig(prev => ({
        ...prev,
        startDate: tf.start_date,
        endDate: tf.end_date
      }));
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className={`backtest-modal-overlay ${isFullscreen ? 'fullscreen' : ''}`} onClick={onClose}>
      <div className={`backtest-modal ${isFullscreen ? 'fullscreen' : ''}`} onClick={(e) => e.stopPropagation()}>
        <div className="backtest-header">
          <h2>Backtest Strategy: {symbol}</h2>
          <div className="header-buttons">
            <button onClick={() => setIsFullscreen(!isFullscreen)} className="fullscreen-btn" title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}>
              {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
            </button>
            <button onClick={onClose} className="close-btn">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="backtest-config">
          <div className="config-group">
            <label>Strategy</label>
            <select
              value={config.strategy}
              onChange={(e) => setConfig({...config, strategy: e.target.value})}
            >
              {strategies.map(s => (
                <option key={s.name} value={s.name}>{s.name.replace('_', ' ')}</option>
              ))}
            </select>
          </div>

          <div className="config-group">
            <label><Clock size={16} /> Timeframe</label>
            <select
              value={config.timeframe}
              onChange={(e) => handleTimeframeChange(e.target.value)}
            >
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="1d">1 Day</option>
            </select>
            {dataAvailability?.timeframes[config.timeframe] && (
              <span className="data-info">
                {dataAvailability.timeframes[config.timeframe].candle_count} candles available
              </span>
            )}
          </div>

          <div className="config-row">
            <div className="config-group">
              <label><Calendar size={16} /> Start Date</label>
              <input
                type="date"
                value={config.startDate}
                onChange={(e) => setConfig({...config, startDate: e.target.value})}
              />
            </div>

            <div className="config-group">
              <label><Calendar size={16} /> End Date</label>
              <input
                type="date"
                value={config.endDate}
                onChange={(e) => setConfig({...config, endDate: e.target.value})}
              />
            </div>
          </div>

          <div className="config-row">
            <div className="config-group">
              <label><DollarSign size={16} /> Initial Capital</label>
              <input
                type="number"
                value={config.initialCapital}
                onChange={(e) => setConfig({...config, initialCapital: Number(e.target.value)})}
              />
            </div>

            <div className="config-group">
              <label>Position Size</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="1.0"
                value={config.positionSize}
                onChange={(e) => setConfig({...config, positionSize: Number(e.target.value)})}
              />
              <span className="data-info">{(config.positionSize * 100).toFixed(0)}% of capital</span>
            </div>
          </div>

          {!dataAvailability?.available && (
            <div className="warning-message">
              No historical data available for {symbol}. Click "Load Data" to fetch from Yahoo Finance.
            </div>
          )}

          {loadingMessage && (
            <div className="info-message loading-progress">
              <div className="loading-content">
                {loadingMessage}
                {countdown > 0 && (
                  <div className="countdown-timer">
                    Timeout in {countdown}s
                  </div>
                )}
              </div>
              {countdown > 0 && (
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${(countdown / 30) * 100}%` }}
                  ></div>
                </div>
              )}
            </div>
          )}

          {!loadingMessage && (
            <div className="info-message">
              <strong>Tip:</strong> You need at least 50 candles for backtesting.
              For 1d timeframe, use at least 3 months. For 1h, use at least 1 month.
            </div>
          )}

          <div className="button-row">
            {!dataAvailability?.available && (
              <button
                className="btn btn-secondary"
                onClick={loadHistoricalData}
                disabled={loadingData || running}
              >
                <Activity size={16} />
                {loadingData ? 'Loading Data...' : 'Load Data from Yahoo Finance'}
              </button>
            )}

            <button
              className="btn btn-secondary"
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{ marginTop: '12px', width: '100%' }}
            >
              {showAdvanced ? '▼' : '►'} Advanced Strategy Parameters
            </button>
          </div>

          {/* Advanced Strategy Parameters */}
          {showAdvanced && (
            <div className="advanced-params">
              <h4>Strategy Parameters</h4>

              {config.strategy === 'MACD' && (
                <div className="params-grid">
                  <div className="config-group">
                    <label>Fast Period</label>
                    <input
                      type="number"
                      value={strategyParams.fast_period}
                      onChange={(e) => setStrategyParams({...strategyParams, fast_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Slow Period</label>
                    <input
                      type="number"
                      value={strategyParams.slow_period}
                      onChange={(e) => setStrategyParams({...strategyParams, slow_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Signal Period</label>
                    <input
                      type="number"
                      value={strategyParams.signal_period}
                      onChange={(e) => setStrategyParams({...strategyParams, signal_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                </div>
              )}

              {config.strategy === 'RSI' && (
                <div className="params-grid">
                  <div className="config-group">
                    <label>RSI Period</label>
                    <input
                      type="number"
                      value={strategyParams.rsi_period}
                      onChange={(e) => setStrategyParams({...strategyParams, rsi_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Oversold Level</label>
                    <input
                      type="number"
                      value={strategyParams.oversold}
                      onChange={(e) => setStrategyParams({...strategyParams, oversold: parseInt(e.target.value)})}
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="config-group">
                    <label>Overbought Level</label>
                    <input
                      type="number"
                      value={strategyParams.overbought}
                      onChange={(e) => setStrategyParams({...strategyParams, overbought: parseInt(e.target.value)})}
                      min="0"
                      max="100"
                    />
                  </div>
                </div>
              )}

              {config.strategy === 'RSI_W_PATTERN' && (
                <div className="params-grid">
                  <div className="config-group">
                    <label>RSI Period</label>
                    <input
                      type="number"
                      value={strategyParams.rsi_period}
                      onChange={(e) => setStrategyParams({...strategyParams, rsi_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Oversold Threshold</label>
                    <input
                      type="number"
                      value={strategyParams.oversold_threshold}
                      onChange={(e) => setStrategyParams({...strategyParams, oversold_threshold: parseInt(e.target.value)})}
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="config-group">
                    <label>Overbought Threshold</label>
                    <input
                      type="number"
                      value={strategyParams.overbought_threshold}
                      onChange={(e) => setStrategyParams({...strategyParams, overbought_threshold: parseInt(e.target.value)})}
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="config-group">
                    <label>Min Distance</label>
                    <input
                      type="number"
                      value={strategyParams.min_distance}
                      onChange={(e) => setStrategyParams({...strategyParams, min_distance: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Max Distance</label>
                    <input
                      type="number"
                      value={strategyParams.max_distance}
                      onChange={(e) => setStrategyParams({...strategyParams, max_distance: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>RSI Tolerance</label>
                    <input
                      type="number"
                      value={strategyParams.rsi_tolerance}
                      onChange={(e) => setStrategyParams({...strategyParams, rsi_tolerance: parseInt(e.target.value)})}
                      min="0"
                    />
                  </div>
                </div>
              )}

              {config.strategy === 'MA_CROSSOVER' && (
                <div className="params-grid">
                  <div className="config-group">
                    <label>Short Period</label>
                    <input
                      type="number"
                      value={strategyParams.short_period}
                      onChange={(e) => setStrategyParams({...strategyParams, short_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Long Period</label>
                    <input
                      type="number"
                      value={strategyParams.long_period}
                      onChange={(e) => setStrategyParams({...strategyParams, long_period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Use EMA</label>
                    <select
                      value={strategyParams.use_ema}
                      onChange={(e) => setStrategyParams({...strategyParams, use_ema: e.target.value === 'true'})}
                    >
                      <option value="true">Yes</option>
                      <option value="false">No (SMA)</option>
                    </select>
                  </div>
                </div>
              )}

              {config.strategy === 'BOLLINGER' && (
                <div className="params-grid">
                  <div className="config-group">
                    <label>Period</label>
                    <input
                      type="number"
                      value={strategyParams.period}
                      onChange={(e) => setStrategyParams({...strategyParams, period: parseInt(e.target.value)})}
                      min="1"
                    />
                  </div>
                  <div className="config-group">
                    <label>Standard Deviation</label>
                    <input
                      type="number"
                      step="0.1"
                      value={strategyParams.std_dev}
                      onChange={(e) => setStrategyParams({...strategyParams, std_dev: parseFloat(e.target.value)})}
                      min="0.1"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: '16px' }}>
            <button
              className="btn btn-primary backtest-run-btn"
              onClick={handleRun}
              disabled={running || loadingData}
            >
              <PlayCircle size={16} />
              {running ? 'Running Backtest...' : 'Run Backtest'}
            </button>
          </div>
        </div>

        {running && (
          <div className="backtest-loading">
            <div className="spinner"></div>
            <p>Running backtest simulation...</p>
            <p className="loading-detail">Analyzing {config.strategy} strategy on {symbol}</p>
          </div>
        )}

        {error && !running && (
          <div className="backtest-error">
            <h3>Error</h3>
            <p>{error}</p>
          </div>
        )}

        {result && !running && (
          <div className="backtest-results">
            <div className="results-header">
              <h3>Backtest Results</h3>
              <button
                className="btn btn-secondary btn-sm"
                onClick={loadHistoricalData}
                disabled={loadingData}
                title="Force reload data from Yahoo Finance"
              >
                <Activity size={14} />
                {loadingData ? 'Reloading...' : 'Force Reload Data'}
              </button>
            </div>

            {result.diagnostics && (
              <div className="diagnostics-info">
                <h4>Analysis Details</h4>
                <div className="diagnostic-grid">
                  <div className="diagnostic-item">
                    <span className="diag-label">Candles Analyzed</span>
                    <span className="diag-value">{result.diagnostics.total_candles}</span>
                  </div>
                  <div className="diagnostic-item">
                    <span className="diag-label">BUY Signals Found</span>
                    <span className={`diag-value ${result.diagnostics.buy_signals_found > 0 ? 'positive' : ''}`}>
                      {result.diagnostics.buy_signals_found}
                    </span>
                  </div>
                  <div className="diagnostic-item">
                    <span className="diag-label">SELL Signals Found</span>
                    <span className={`diag-value ${result.diagnostics.sell_signals_found > 0 ? 'positive' : ''}`}>
                      {result.diagnostics.sell_signals_found}
                    </span>
                  </div>
                  <div className="diagnostic-item">
                    <span className="diag-label">Data Range</span>
                    <span className="diag-value diag-small">
                      {result.diagnostics.data_range?.start ? new Date(result.diagnostics.data_range.start).toLocaleDateString() : 'N/A'} -
                      {result.diagnostics.data_range?.end ? new Date(result.diagnostics.data_range.end).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                </div>

                {!result.diagnostics.opportunities_found && (
                  <div className="warning-message">
                    No trading opportunities found in this period. The strategy did not detect any BUY or SELL signals.
                    Try adjusting the date range, timeframe, or strategy parameters.
                  </div>
                )}
              </div>
            )}

            <div className="results-summary">
              <div className="summary-item">
                <span className="summary-label">Period</span>
                <span className="summary-value">
                  {result.config.start_date} to {result.config.end_date}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Strategy</span>
                <span className="summary-value">{result.config.strategy}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Timeframe</span>
                <span className="summary-value">{result.config.timeframe}</span>
              </div>
            </div>

            <div className="metrics-grid">
              <div className="metric-card highlight">
                <div className="metric-icon">
                  {result.metrics.total_return >= 0 ?
                    <TrendingUp className="positive" /> :
                    <TrendingDown className="negative" />
                  }
                </div>
                <div className="metric-content">
                  <span className="metric-label">Total Return</span>
                  <span className={`metric-value ${result.metrics.total_return >= 0 ? 'positive' : 'negative'}`}>
                    ${result.metrics.total_return} ({result.metrics.total_return_percent}%)
                  </span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">
                  <Activity />
                </div>
                <div className="metric-content">
                  <span className="metric-label">Max Drawdown</span>
                  <span className="metric-value negative">
                    -{result.metrics.max_drawdown_percent}%
                  </span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Sharpe Ratio</span>
                  <span className="metric-value">{result.metrics.sharpe_ratio}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Win Rate</span>
                  <span className="metric-value">{result.metrics.win_rate}%</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Total Trades</span>
                  <span className="metric-value">{result.metrics.total_trades}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Profit Factor</span>
                  <span className="metric-value">{result.metrics.profit_factor}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Winning Trades</span>
                  <span className="metric-value positive">{result.metrics.winning_trades}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Losing Trades</span>
                  <span className="metric-value negative">{result.metrics.losing_trades}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Avg Win</span>
                  <span className="metric-value positive">${result.metrics.avg_win}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Avg Loss</span>
                  <span className="metric-value negative">${result.metrics.avg_loss}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Best Trade</span>
                  <span className="metric-value positive">${result.metrics.best_trade}</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <span className="metric-label">Worst Trade</span>
                  <span className="metric-value negative">${result.metrics.worst_trade}</span>
                </div>
              </div>
            </div>

            {result.trades && result.trades.length > 0 && (
              <BacktestChart
                trades={result.trades}
                equityCurve={result.equity_curve}
                equityDates={result.equity_dates}
                strategyName={config.strategy}
                symbol={symbol}
                allCandles={result.all_candles || []}
                allIndicators={result.all_indicators || null}
              />
            )}

            {result.trades && result.trades.length > 0 && (
              <div className="trades-section">
                <h4>All Trades (Last 50)</h4>
                <div className="trades-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Entry Date</th>
                        <th>Entry Price</th>
                        <th>Exit Date</th>
                        <th>Exit Price</th>
                        <th>Quantity</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades.map((trade, idx) => (
                        <tr key={idx}>
                          <td>{new Date(trade.entry_date).toLocaleDateString()}</td>
                          <td>${trade.entry_price.toFixed(2)}</td>
                          <td>{trade.exit_date ? new Date(trade.exit_date).toLocaleDateString() : 'Open'}</td>
                          <td>{trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}</td>
                          <td>{trade.quantity}</td>
                          <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                            ${trade.pnl.toFixed(2)}
                          </td>
                          <td className={trade.pnl_percent >= 0 ? 'positive' : 'negative'}>
                            {trade.pnl_percent.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

export default BacktestModal;
