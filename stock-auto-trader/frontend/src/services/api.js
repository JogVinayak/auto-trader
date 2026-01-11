import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Stocks API
export const stocksAPI = {
  getAll: () => api.get('/stocks'),
  add: (symbol, name) => api.post('/stocks', null, { params: { symbol, name } }),
  delete: (symbol) => api.delete(`/stocks/${symbol}`),
};

// Portfolio API
export const portfolioAPI = {
  get: () => api.get('/portfolio'),
  reset: () => api.post('/portfolio/reset'),
};

// Candles API
export const candlesAPI = {
  get: (symbol, timeframe = '1d', limit = 100) =>
    api.get(`/candles/${symbol}`, { params: { timeframe, limit } }),
  getLatest: (symbol, timeframe = '1d') =>
    api.get(`/candles/${symbol}/latest`, { params: { timeframe } }),
  sync: (symbol, timeframe = null, fullSync = false) =>
    api.post(`/candles/${symbol}/sync`, null, {
      params: { timeframe, full_sync: fullSync },
    }),
  getSyncStatus: (symbol) => api.get(`/candles/${symbol}/sync-status`),
};

// Signals API
export const signalsAPI = {
  get: (symbol, timeframe = '1d', strategy = null) =>
    api.get(`/signals/${symbol}`, { params: { timeframe, strategy } }),
  // Fast version using stored indicator values (no recalculation)
  getFast: (symbol, timeframe = '1d', strategy = null) =>
    api.get(`/signals-fast/${symbol}`, { params: { timeframe, strategy } }),
  getStrategies: () => api.get('/strategies'),
};

// Indicators API - for chart rendering using stored values
export const indicatorsAPI = {
  get: (symbol, timeframe = '1d', strategy = null, limit = 500) =>
    api.get(`/indicators/${symbol}`, { params: { timeframe, strategy, limit } }),
};

// Strategy Settings API
export const strategySettingsAPI = {
  getAll: () => api.get('/strategy-settings'),
  get: (strategy) => api.get(`/strategy-settings/${strategy}`),
  save: (strategy, settings) => api.post(`/strategy-settings/${strategy}`, settings),
};

// Trades API
export const tradesAPI = {
  getAll: (symbol = null, limit = 50) =>
    api.get('/trades', { params: { symbol, limit } }),
};

export default api;
