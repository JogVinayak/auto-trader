# Manual Trading Feature - Implementation Guide

## Progress Summary

### ✅ Backend Implementation (COMPLETED)

1. **Models Updated**
   - Added `MANUAL` to `StrategyType` enum in [models.py](stock-auto-trader/backend/models.py:37)
   - Database enum updated successfully

2. **Fee Calculation Utility**
   - Created [trading_fees.py](stock-auto-trader/backend/utils/trading_fees.py)
   - Implements Zerodha fee structure:
     - Brokerage: ₹20 or 0.03% (whichever lower)
     - STT: 0.1% on sell side
     - Exchange charges: 0.00325%
     - GST: 18% on brokerage
     - SEBI charges: ₹10 per crore
     - Stamp duty: 0.015% buy / 0.003% sell

3. **API Endpoints Created**
   - `POST /trades/manual/buy` - Execute buy order
   - `POST /trades/manual/sell` - Execute sell order
   - `GET /trades/manual/positions` - Get open positions with P&L
   - `GET /trades/manual/history` - Get trade history with filters
   - `GET /trades/manual/calculate-fees` - Preview fees before trade

### ✅ Frontend Components (PARTIALLY COMPLETED)

1. **Created Components**
   - ✅ [ManualTradingCard.jsx](stock-auto-trader/frontend/src/components/ManualTradingCard.jsx)
     - Full-width collapsible card
     - Keyboard shortcuts (Cmd+B, Cmd+X)
     - Buy/Sell buttons
     - Summary display

   - ✅ [BuyModal.jsx](stock-auto-trader/frontend/src/components/BuyModal.jsx)
     - Quantity and price input
     - Fund allocation by percentage (25%, 50%, 75%, 100%)
     - Fee breakdown (Zerodha model)
     - Max quantity calculator
     - Confirmation dialog

   - ✅ [ManualTradingCard.css](stock-auto-trader/frontend/src/components/ManualTradingCard.css)
   - ✅ [TradeModal.css](stock-auto-trader/frontend/src/components/TradeModal.css)

2. **Remaining Components to Create**
   - ⏳ SellModal.jsx
   - ⏳ PositionsTable.jsx (with tabs, filters, summary)

## Next Steps to Complete

### Step 1: Create SellModal Component

Create `stock-auto-trader/frontend/src/components/SellModal.jsx`:

```javascript
// Similar to BuyModal but:
// - Shows current holding quantity
// - Validates against available shares
// - Shows realized P&L on sell
// - FIFO lot selection
```

### Step 2: Create PositionsTable Component

Create `stock-auto-trader/frontend/src/components/PositionsTable.jsx` with:

**Features:**
- ✅ Separate tabs: [Open Positions] | [Closed Trades]
- ✅ Filters: Date range, Trade type, Symbol
- ✅ Sort: Latest first, P&L high→low, P&L low→high
- ✅ Summary card: Today's P&L, Total P&L, Win rate
- ✅ Pagination: Load more (10 at a time)
- ✅ Real-time P&L updates

**Structure:**
```
┌─────────────────────────────────────────────────────┐
│  [Open Positions] | [History]                       │
├─────────────────────────────────────────────────────┤
│  Summary Card                                        │
│  Today: +$50  |  Total: +$500  |  Win Rate: 65%    │
├─────────────────────────────────────────────────────┤
│  Filters: [All ▼] [Last 7 Days ▼] Sort: [Latest ▼] │
├─────────────────────────────────────────────────────┤
│  Date   | Symbol | Type | Qty | Price | P&L        │
│  Jan 11 | AAPL   | BUY  | 10  | $250  | +$73.70   │
│  ...                                                 │
├─────────────────────────────────────────────────────┤
│              [Load 10 More]   Show: [10 ▼]         │
└─────────────────────────────────────────────────────┘
```

### Step 3: Create API Service

Create `stock-auto-trader/frontend/src/services/manualTrading.js`:

```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export const manualTradingAPI = {
  // Buy order
  buy: (symbol, quantity, price) =>
    axios.post(`${API_BASE}/trades/manual/buy`, { symbol, quantity, price }),

  // Sell order
  sell: (symbol, quantity, price) =>
    axios.post(`${API_BASE}/trades/manual/sell`, { symbol, quantity, price }),

  // Get positions
  getPositions: (symbol = null, limit = 10, offset = 0) =>
    axios.get(`${API_BASE}/trades/manual/positions`, {
      params: { symbol, limit, offset }
    }),

  // Get history
  getHistory: (params = {}) =>
    axios.get(`${API_BASE}/trades/manual/history`, { params }),

  // Calculate fees
  calculateFees: (symbol, quantity, price, tradeType, fundPercentage = null) =>
    axios.get(`${API_BASE}/trades/manual/calculate-fees`, {
      params: { symbol, quantity, price, trade_type: tradeType, fund_percentage: fundPercentage }
    })
};
```

### Step 4: Integrate with Dashboard

Update `stock-auto-trader/frontend/src/pages/Dashboard.jsx`:

```javascript
import ManualTradingCard from '../components/ManualTradingCard';

// In the render:
return (
  <div className="dashboard">
    <Sidebar ... />
    <main className="main-content">

      {/* ADD THIS - Manual Trading Card at the top */}
      <ManualTradingCard
        selectedStock={selectedStock}
        currentPrice={getCurrentPrice()}
        onRefresh={fetchStockData}
      />

      {/* Existing content below */}
      <div className="portfolio-stats">...</div>
      <div className="strategy-cards">...</div>
      ...
    </main>
  </div>
);
```

### Step 5: Add Buy/Sell Buttons to Stock Cards

Update stock card components to include quick Buy/Sell buttons:

```javascript
<div className="stock-card">
  <div className="stock-info">...</div>
  <div className="stock-actions">
    <button onClick={() => handleBuy(stock.symbol)}>Buy</button>
    <button onClick={() => handleSell(stock.symbol)}>Sell</button>
  </div>
</div>
```

## Testing Checklist

### Backend Tests
- [ ] Fee calculation matches Zerodha calculator
- [ ] Buy order creates trade and updates portfolio
- [ ] Buy order updates holdings correctly
- [ ] Sell order validates sufficient shares
- [ ] Sell order updates portfolio and holdings
- [ ] FIFO matching works correctly
- [ ] Positions endpoint returns correct P&L
- [ ] History endpoint filters work
- [ ] Fund percentage calculation is accurate

### Frontend Tests
- [ ] Keyboard shortcuts work (Cmd+B, Cmd+X)
- [ ] Buy modal shows correct fees
- [ ] Fund allocation percentages work
- [ ] Max quantity calculation is accurate
- [ ] Confirmation dialog prevents accidental trades
- [ ] Sell modal shows current holdings
- [ ] Positions table displays correctly
- [ ] Filters and sorting work
- [ ] Load more pagination works
- [ ] Card can collapse/expand
- [ ] Fullscreen mode works
- [ ] Real-time P&L updates

## API Endpoints Reference

### Execute Buy Order
```
POST /trades/manual/buy
Body: { symbol: string, quantity: number, price?: number }
Returns: { message, trade_id, fees, remaining_balance }
```

### Execute Sell Order
```
POST /trades/manual/sell
Body: { symbol: string, quantity: number, price?: number }
Returns: { message, trade_id, fees, new_balance }
```

### Get Open Positions
```
GET /trades/manual/positions?symbol=AAPL&limit=10&offset=0
Returns: { positions[], summary, pagination }
```

### Get Trade History
```
GET /trades/manual/history?symbol=AAPL&trade_type=BUY&limit=10
Returns: { trades[], pagination }
```

### Calculate Fees (Preview)
```
GET /trades/manual/calculate-fees?symbol=AAPL&quantity=10&price=250&trade_type=BUY&fund_percentage=50
Returns: { fees, max_quantity_info, can_execute }
```

## Database Schema

Trades are stored in existing `trades` table with:
- `strategy = 'MANUAL'`
- `trade_type` = 'BUY' or 'SELL'
- `total_value` includes all fees
- `notes` contains fee breakdown

Holdings track average buy price and quantity.

## File Structure

```
backend/
├── models.py (updated with MANUAL enum)
├── main.py (added manual trading endpoints)
└── utils/
    └── trading_fees.py (NEW - fee calculator)

frontend/src/
├── components/
│   ├── ManualTradingCard.jsx (NEW)
│   ├── ManualTradingCard.css (NEW)
│   ├── BuyModal.jsx (NEW)
│   ├── SellModal.jsx (TODO)
│   ├── PositionsTable.jsx (TODO)
│   └── TradeModal.css (NEW)
├── services/
│   └── manualTrading.js (TODO)
└── pages/
    └── Dashboard.jsx (needs integration)
```

## Next Action Items

1. Create SellModal.jsx
2. Create PositionsTable.jsx
3. Create manualTrading.js API service
4. Integrate ManualTradingCard into Dashboard
5. Add Buy/Sell buttons to stock cards
6. Test end-to-end flow
7. Add real-time price updates (WebSocket/polling)

## Notes

- All fees follow Zerodha's actual fee structure
- P&L is calculated in real-time based on current prices
- FIFO matching for sell orders
- Paper trading only (no real money)
- Keyboard shortcuts: Cmd+B (Buy), Cmd+X (Sell), Esc (Close)
